from unittest.mock import patch

from cliauth.providers.sentry import SentryProvider
from cliauth.runner import RunResult


class TestSentryProvider:
    def test_validate_config_ok(self):
        provider = SentryProvider({"auth_token": "sntryu_test"})
        assert provider.validate_config() == []

    def test_validate_config_missing(self):
        provider = SentryProvider({})
        assert "auth_token" in provider.validate_config()

    def test_setup_dry_run(self):
        provider = SentryProvider({"auth_token": "sntryu_test"})
        assert provider.setup(dry_run=True) is True

    def test_setup_writes_sentryclirc(self, tmp_path, monkeypatch):
        rc_path = tmp_path / ".sentryclirc"
        monkeypatch.setattr("cliauth.providers.sentry.SENTRYCLIRC_PATH", rc_path)

        provider = SentryProvider(
            {
                "auth_token": "sntryu_test123",
                "org": "myorg",
                "project": "myproject",
            }
        )
        assert provider.setup() is True
        assert rc_path.exists()

        content = rc_path.read_text()
        assert "sntryu_test123" in content
        assert "myorg" in content
        assert "myproject" in content

    @patch("cliauth.providers.sentry.run")
    def test_status_authenticated(self, mock_run):
        mock_run.return_value = RunResult(
            0, "Organization: myorg\nProject: myproject", ""
        )
        provider = SentryProvider({"auth_token": "test"})
        rows = provider.status()
        assert rows[0][1] is True

    @patch("cliauth.providers.sentry.run")
    def test_status_not_authenticated(self, mock_run):
        mock_run.return_value = RunResult(1, "", "not authenticated")
        provider = SentryProvider({"auth_token": ""})
        rows = provider.status()
        assert rows[0][1] is False
