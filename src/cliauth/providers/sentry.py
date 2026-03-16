import configparser
from pathlib import Path
from typing import Any

from cliauth import output
from cliauth.providers.base import AuthProvider
from cliauth.runner import run

SENTRYCLIRC_PATH = Path.home() / ".sentryclirc"


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

    def setup(self, dry_run: bool = False) -> bool:
        if dry_run:
            output.info(f"[{self.name}] Would write auth config to {SENTRYCLIRC_PATH}")
            return True

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
