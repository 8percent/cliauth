from unittest.mock import patch

from cliauth.providers.acli import AtlassianProvider
from cliauth.runner import RunResult


class TestAtlassianProvider:
    def _make_config(self, **overrides):
        config = {
            "site": "test.atlassian.net",
            "email": "user@test.com",
            "api_token": "token123",
        }
        config.update(overrides)
        return config

    def test_validate_config_ok(self):
        provider = AtlassianProvider(self._make_config())
        assert provider.validate_config() == []

    def test_validate_config_missing_all(self):
        provider = AtlassianProvider({})
        missing = provider.validate_config()
        assert "site" in missing
        assert "email" in missing
        assert "api_token" in missing

    def test_validate_config_partial(self):
        provider = AtlassianProvider({"site": "test.net"})
        missing = provider.validate_config()
        assert "site" not in missing
        assert "email" in missing
        assert "api_token" in missing

    def test_setup_dry_run(self):
        provider = AtlassianProvider(self._make_config())
        assert provider.setup(dry_run=True) is True

    @patch("cliauth.providers.acli.run")
    def test_setup_success(self, mock_run):
        mock_run.return_value = RunResult(0, "", "")
        provider = AtlassianProvider(self._make_config())
        assert provider.setup() is True
        mock_run.assert_called_once_with(
            [
                "acli",
                "jira",
                "auth",
                "login",
                "--site",
                "test.atlassian.net",
                "--email",
                "user@test.com",
                "--token",
            ],
            input_text="token123",
        )

    @patch("cliauth.providers.acli.run")
    def test_setup_failure(self, mock_run):
        mock_run.return_value = RunResult(1, "", "auth error")
        provider = AtlassianProvider(self._make_config())
        assert provider.setup() is False

    @patch("cliauth.providers.acli.run")
    def test_status_authenticated(self, mock_run):
        mock_run.return_value = RunResult(0, "Authenticated", "")
        provider = AtlassianProvider(self._make_config())
        rows = provider.status()
        assert rows[0][1] is True

    @patch("cliauth.providers.acli.run")
    def test_status_not_authenticated(self, mock_run):
        mock_run.return_value = RunResult(1, "", "not logged in")
        provider = AtlassianProvider(self._make_config())
        rows = provider.status()
        assert rows[0][1] is False
