import os
import shlex
import subprocess
from functools import lru_cache
from typing import Any

from cliauth import output
from cliauth.providers.base import AuthProvider
from cliauth.runner import run

# A project venv may put aws v1 first on PATH, so well-known v2 locations are
# checked too.
AWS_V2_FALLBACKS = (
    "/opt/homebrew/bin/aws",
    "/usr/local/bin/aws",
    "/usr/local/aws-cli/aws",
)
SSO_LOGIN_TIMEOUT_SECONDS = 300


def aws_candidates() -> list[str]:
    from_path = [
        os.path.join(directory, "aws")
        for directory in os.environ.get("PATH", "").split(os.pathsep)
        if directory
    ]
    return list(dict.fromkeys(from_path + list(AWS_V2_FALLBACKS)))


@lru_cache(maxsize=1)
def find_aws_v2() -> str | None:
    """Return the first executable whose --version reports aws-cli/2, or None."""
    for candidate in aws_candidates():
        if not (os.path.isfile(candidate) and os.access(candidate, os.X_OK)):
            continue
        try:
            result = run([candidate, "--version"], timeout=10)
        except (OSError, subprocess.TimeoutExpired):
            continue
        if f"{result.stdout}{result.stderr}".startswith("aws-cli/2."):
            return candidate
    return None


class AWSProvider(AuthProvider):
    name = "aws"
    display_name = "AWS CLI"
    required_binary = "aws (v2)"

    def __init__(self, config: dict[str, Any]):
        super().__init__(config)
        self.sso_profiles: list[str] = self.config.get("sso_profiles", [])

    def validate_config(self) -> list[str]:
        missing = []
        if not self.sso_profiles:
            missing.append("sso_profiles")
        return missing

    def is_installed(self) -> bool:
        return find_aws_v2() is not None

    def missing_binary_message(self) -> str:
        return "AWS CLI v2 not found (checked PATH and common install paths)"

    def _sso_session(self, aws: str, profile: str) -> str | None:
        result = run([aws, "configure", "get", "sso_session", "--profile", profile])
        if result.success and result.stdout:
            return result.stdout
        return None

    def _login_targets(self, aws: str) -> list[tuple[str, list[str]]]:
        """One login per sso-session in profile order.

        Profiles without a session fall back to a per-profile login.
        """
        targets: list[tuple[str, list[str]]] = []
        seen_sessions: set[str] = set()
        for profile in self.sso_profiles:
            session = self._sso_session(aws, profile)
            if session is None:
                targets.append(
                    (f"profile {profile}", [aws, "sso", "login", "--profile", profile])
                )
            elif session not in seen_sessions:
                seen_sessions.add(session)
                targets.append(
                    (
                        f"session {session}",
                        [aws, "sso", "login", "--sso-session", session],
                    )
                )
        return targets

    def setup(self, dry_run: bool = False) -> bool:
        aws = find_aws_v2()
        if aws is None:
            output.error(f"[{self.name}] AWS CLI v2 not found (brew install awscli)")
            return False
        all_ok = True
        for label, command in self._login_targets(aws):
            if dry_run:
                output.info(f"[{self.name}] Would run: {shlex.join(command)}")
                continue
            output.info(f"[{self.name}] Logging in to {label} ...")
            try:
                result = run(command, timeout=SSO_LOGIN_TIMEOUT_SECONDS)
            except subprocess.TimeoutExpired:
                output.error(
                    f"[{self.name}] {label} timed out waiting for browser approval "
                    f"({SSO_LOGIN_TIMEOUT_SECONDS}s)"
                )
                all_ok = False
                continue
            if result.success:
                output.success(f"[{self.name}] {label} authenticated")
            else:
                output.error(f"[{self.name}] {label} failed: {result.stderr}")
                all_ok = False
        return all_ok

    def status(self) -> list[tuple[str, bool, str]]:
        aws = find_aws_v2() or "aws"
        rows: list[tuple[str, bool, str]] = []
        for profile in self.sso_profiles:
            result = run([aws, "sts", "get-caller-identity", "--profile", profile])
            label = f"{self.name}/{profile}"
            if result.success:
                rows.append((label, True, f"Profile active: {profile}"))
            else:
                detail = "SSO session expired or not configured"
                if result.stderr:
                    for line in result.stderr.splitlines():
                        if "expired" in line.lower() or "error" in line.lower():
                            detail = line.strip()
                            break
                rows.append((label, False, detail))
        return rows
