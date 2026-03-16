from typing import Any

from cliauth import output
from cliauth.providers.base import AuthProvider
from cliauth.runner import run


class GitHubProvider(AuthProvider):
    name = "gh"
    display_name = "GitHub CLI"
    required_binary = "gh"

    def __init__(self, config: dict[str, Any]):
        super().__init__(config)
        self.token = self.config.get("token", "")

    def validate_config(self) -> list[str]:
        missing = []
        if not self.token:
            missing.append("token")
        return missing

    def setup(self, dry_run: bool = False) -> bool:
        if dry_run:
            output.info(f"[{self.name}] Would run: gh auth login --with-token")
            return True

        result = run(
            ["gh", "auth", "login", "--with-token"],
            input_text=self.token,
        )
        if result.success:
            output.success(f"[{self.name}] Authenticated successfully")
        else:
            output.error(f"[{self.name}] Auth failed: {result.stderr}")
        return result.success

    def status(self) -> list[tuple[str, bool, str]]:
        result = run(["gh", "auth", "status"])
        combined = result.stdout + result.stderr
        if result.success:
            detail = "Authenticated"
            for line in combined.splitlines():
                if "Logged in to" in line:
                    detail = line.strip()
                    break
            return [(self.name, True, detail)]
        return [(self.name, False, combined or "Not authenticated")]
