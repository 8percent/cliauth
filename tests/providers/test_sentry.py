import urllib.error
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

    @patch.object(SentryProvider, "_verify_token", return_value=(True, "ok"))
    def test_setup_writes_sentryclirc(self, _mock_verify, tmp_path, monkeypatch):
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

    @patch.object(SentryProvider, "_verify_token", return_value=(True, "ok"))
    def test_setup_backs_up_existing_config(self, _mock_verify, tmp_path, monkeypatch):
        rc_path = tmp_path / ".sentryclirc"
        rc_path.write_text("[auth]\ntoken = old_valid_token\n")
        monkeypatch.setattr("cliauth.providers.sentry.SENTRYCLIRC_PATH", rc_path)

        provider = SentryProvider({"auth_token": "sntryu_new", "org": "myorg"})
        assert provider.setup() is True

        backup = tmp_path / ".sentryclirc.bak"
        assert backup.exists()
        assert "old_valid_token" in backup.read_text()

    @patch.object(
        SentryProvider, "_verify_token", return_value=(False, "token rejected")
    )
    def test_setup_aborts_on_invalid_token(self, _mock_verify, tmp_path, monkeypatch):
        rc_path = tmp_path / ".sentryclirc"
        original = "[auth]\ntoken = old_valid_token\n"
        rc_path.write_text(original)
        monkeypatch.setattr("cliauth.providers.sentry.SENTRYCLIRC_PATH", rc_path)

        provider = SentryProvider({"auth_token": "sntryu_bad", "org": "myorg"})
        assert provider.setup() is False
        # An invalid token must leave the existing config untouched.
        assert rc_path.read_text() == original
        assert not (tmp_path / ".sentryclirc.bak").exists()

    @patch.object(
        SentryProvider, "_verify_token", return_value=(None, "could not reach API")
    )
    def test_setup_proceeds_when_unverifiable(
        self, _mock_verify, tmp_path, monkeypatch
    ):
        rc_path = tmp_path / ".sentryclirc"
        monkeypatch.setattr("cliauth.providers.sentry.SENTRYCLIRC_PATH", rc_path)

        provider = SentryProvider({"auth_token": "sntryu_x", "org": "myorg"})
        assert provider.setup() is True
        assert rc_path.exists()

    @patch.object(SentryProvider, "_verify_token", return_value=(True, "ok"))
    @patch("cliauth.providers.sentry.output.warning")
    def test_setup_warns_when_project_missing(
        self, mock_warning, _mock_verify, tmp_path, monkeypatch
    ):
        rc_path = tmp_path / ".sentryclirc"
        monkeypatch.setattr("cliauth.providers.sentry.SENTRYCLIRC_PATH", rc_path)

        provider = SentryProvider({"auth_token": "sntryu_x", "org": "myorg"})
        assert provider.setup() is True
        assert any(
            "project" in str(call).lower() for call in mock_warning.call_args_list
        )

    @patch("cliauth.providers.sentry.urllib.request.urlopen")
    def test_verify_token_valid(self, _mock_urlopen):
        provider = SentryProvider({"auth_token": "sntryu_good"})
        verified, _ = provider._verify_token()
        assert verified is True

    @patch("cliauth.providers.sentry.urllib.request.urlopen")
    def test_verify_token_invalid(self, mock_urlopen):
        mock_urlopen.side_effect = urllib.error.HTTPError(
            "https://sentry.io/api/0/", 401, "Unauthorized", {}, None
        )
        provider = SentryProvider({"auth_token": "sntryu_bad"})
        verified, _ = provider._verify_token()
        assert verified is False

    @patch("cliauth.providers.sentry.urllib.request.urlopen")
    def test_verify_token_network_error(self, mock_urlopen):
        mock_urlopen.side_effect = urllib.error.URLError("network down")
        provider = SentryProvider({"auth_token": "sntryu_x"})
        verified, _ = provider._verify_token()
        assert verified is None

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
