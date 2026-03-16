from unittest.mock import patch

from cliauth.providers.gh import GitHubProvider
from cliauth.runner import RunResult


class TestGitHubProvider:
    def test_validate_config_ok(self):
        provider = GitHubProvider({"token": "ghp_test123"})
        assert provider.validate_config() == []

    def test_validate_config_missing_token(self):
        provider = GitHubProvider({})
        assert "token" in provider.validate_config()

    def test_validate_config_empty_token(self):
        provider = GitHubProvider({"token": ""})
        assert "token" in provider.validate_config()

    def test_setup_dry_run(self):
        provider = GitHubProvider({"token": "ghp_test123"})
        assert provider.setup(dry_run=True) is True

    @patch("cliauth.providers.gh.run")
    def test_setup_success(self, mock_run):
        mock_run.return_value = RunResult(0, "", "")
        provider = GitHubProvider({"token": "ghp_test123"})
        assert provider.setup() is True
        mock_run.assert_called_once_with(
            ["gh", "auth", "login", "--with-token"],
            input_text="ghp_test123",
        )

    @patch("cliauth.providers.gh.run")
    def test_setup_failure(self, mock_run):
        mock_run.return_value = RunResult(1, "", "error: invalid token")
        provider = GitHubProvider({"token": "bad_token"})
        assert provider.setup() is False

    @patch("cliauth.providers.gh.run")
    def test_status_authenticated(self, mock_run):
        mock_run.return_value = RunResult(0, "Logged in to github.com as Kirade", "")
        provider = GitHubProvider({"token": "ghp_test123"})
        rows = provider.status()
        assert len(rows) == 1
        assert rows[0][0] == "gh"
        assert rows[0][1] is True

    @patch("cliauth.providers.gh.run")
    def test_status_not_authenticated(self, mock_run):
        mock_run.return_value = RunResult(1, "", "not logged in")
        provider = GitHubProvider({"token": ""})
        rows = provider.status()
        assert rows[0][1] is False
