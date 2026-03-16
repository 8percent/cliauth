from typing import Any

from cliauth import output
from cliauth.providers.base import AuthProvider
from cliauth.runner import run


class AtlassianProvider(AuthProvider):
    name = "acli"
    display_name = "Atlassian CLI (Jira)"
    required_binary = "acli"

    def __init__(self, config: dict[str, Any]):
        super().__init__(config)
        self.site = self.config.get("site", "")
        self.email = self.config.get("email", "")
        self.api_token = self.config.get("api_token", "")

    def validate_config(self) -> list[str]:
        missing = []
        if not self.site:
            missing.append("site")
        if not self.email:
            missing.append("email")
        if not self.api_token:
            missing.append("api_token")
        return missing

    def setup(self, dry_run: bool = False) -> bool:
        if dry_run:
            output.info(
                f"[{self.name}] Would run: "
                f"acli jira auth login --site {self.site} "
                f"--email {self.email} --token"
            )
            return True

        result = run(
            [
                "acli",
                "jira",
                "auth",
                "login",
                "--site",
                self.site,
                "--email",
                self.email,
                "--token",
            ],
            input_text=self.api_token,
        )
        if result.success:
            output.success(f"[{self.name}] Authenticated to {self.site}")
        else:
            output.error(f"[{self.name}] Auth failed: {result.stderr}")
        return result.success

    def status(self) -> list[tuple[str, bool, str]]:
        result = run(["acli", "jira", "auth", "status"])
        if result.success:
            detail = f"Authenticated to {self.site}" if self.site else "Authenticated"
            return [(self.name, True, detail)]
        return [(self.name, False, result.stderr or "Not authenticated")]
