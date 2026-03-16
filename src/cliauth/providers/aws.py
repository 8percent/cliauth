from typing import Any

from cliauth import output
from cliauth.providers.base import AuthProvider
from cliauth.runner import run


class AWSProvider(AuthProvider):
    name = "aws"
    display_name = "AWS CLI"
    required_binary = "aws"

    def __init__(self, config: dict[str, Any]):
        super().__init__(config)
        self.sso_profiles: list[str] = self.config.get("sso_profiles", [])

    def validate_config(self) -> list[str]:
        missing = []
        if not self.sso_profiles:
            missing.append("sso_profiles")
        return missing

    def setup(self, dry_run: bool = False) -> bool:
        all_ok = True
        for profile in self.sso_profiles:
            if dry_run:
                output.info(
                    f"[{self.name}] Would run: aws sso login --profile {profile}"
                )
                continue

            output.info(f"[{self.name}] Logging in to profile: {profile} ...")
            result = run(
                ["aws", "sso", "login", "--profile", profile],
                timeout=300,
            )
            if result.success:
                output.success(f"[{self.name}] {profile} authenticated")
            else:
                output.error(f"[{self.name}] {profile} failed: {result.stderr}")
                all_ok = False
        return all_ok

    def status(self) -> list[tuple[str, bool, str]]:
        rows: list[tuple[str, bool, str]] = []
        for profile in self.sso_profiles:
            result = run(
                ["aws", "sts", "get-caller-identity", "--profile", profile],
            )
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
