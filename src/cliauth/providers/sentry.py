import configparser
import shutil
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from cliauth import output
from cliauth.providers.base import AuthProvider
from cliauth.runner import run

SENTRYCLIRC_PATH = Path.home() / ".sentryclirc"
SENTRY_API_URL = "https://sentry.io/api/0/"


class SentryProvider(AuthProvider):
    name = "sentry"
    display_name = "Sentry CLI"
    required_binary = "sentry-cli"

    def __init__(self, config: dict[str, Any]):
        super().__init__(config)
        self.auth_token = self.config.get("auth_token", "")
        self.org = self.config.get("org", "")
        self.project = self.config.get("project", "")

    def validate_config(self) -> list[str]:
        missing = []
        if not self.auth_token:
            missing.append("auth_token")
        return missing

    def _verify_token(self) -> tuple[bool | None, str]:
        """Check the auth token against the Sentry API.

        Returns (verified, message) where verified is True when the token
        is confirmed valid, False when confirmed invalid, and None when it
        could not be verified (e.g. a network failure).
        """
        request = urllib.request.Request(
            SENTRY_API_URL,
            headers={"Authorization": f"Bearer {self.auth_token}"},
        )
        try:
            with urllib.request.urlopen(request, timeout=10):
                return True, "token verified against Sentry API"
        except urllib.error.HTTPError as e:
            if e.code in (401, 403):
                return False, f"token rejected by Sentry API (HTTP {e.code})"
            return None, f"could not verify token (Sentry API HTTP {e.code})"
        except urllib.error.URLError as e:
            return None, f"could not reach Sentry API ({e.reason})"

    def setup(self, dry_run: bool = False) -> bool:
        if dry_run:
            output.info(
                f"[{self.name}] Would verify the auth token, back up any "
                f"existing {SENTRYCLIRC_PATH}, then write auth config"
            )
            return True

        # Verify the token before touching ~/.sentryclirc. An invalid token
        # in the cliauth config must not be allowed to clobber a working
        # ~/.sentryclirc that may still hold a valid token.
        verified, message = self._verify_token()
        if verified is False:
            output.error(
                f"[{self.name}] Aborting: {message}. "
                f"{SENTRYCLIRC_PATH} left unchanged — update auth_token in "
                f"your cliauth config and retry."
            )
            return False
        if verified is None:
            output.warning(f"[{self.name}] {message}; proceeding anyway")

        if not self.project:
            output.warning(
                f"[{self.name}] No project configured — sentry-cli commands "
                f"that need a project (issues, events, source maps) will "
                f"require an explicit --project."
            )

        # Back up any existing config so a bad write stays recoverable.
        if SENTRYCLIRC_PATH.exists():
            backup_path = SENTRYCLIRC_PATH.with_name(SENTRYCLIRC_PATH.name + ".bak")
            shutil.copy2(SENTRYCLIRC_PATH, backup_path)
            output.info(f"[{self.name}] Backed up existing config to {backup_path}")

        config = configparser.ConfigParser()
        if SENTRYCLIRC_PATH.exists():
            config.read(SENTRYCLIRC_PATH)

        if not config.has_section("auth"):
            config.add_section("auth")
        config.set("auth", "token", self.auth_token)

        if self.org or self.project:
            if not config.has_section("defaults"):
                config.add_section("defaults")
            if self.org:
                config.set("defaults", "org", self.org)
            if self.project:
                config.set("defaults", "project", self.project)

        with open(SENTRYCLIRC_PATH, "w") as f:
            config.write(f)

        output.success(f"[{self.name}] Config written to {SENTRYCLIRC_PATH}")
        return True

    def status(self) -> list[tuple[str, bool, str]]:
        result = run(["sentry-cli", "info"])
        if result.success:
            detail = "Authenticated"
            for line in result.stdout.splitlines():
                if "Organization:" in line or "org:" in line.lower():
                    detail = line.strip()
                    break
            return [(self.name, True, detail)]
        return [(self.name, False, result.stderr or "Not authenticated")]
