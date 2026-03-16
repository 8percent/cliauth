from unittest.mock import patch

from cliauth.providers.aws import AWSProvider
from cliauth.runner import RunResult


class TestAWSProvider:
    def test_validate_config_ok(self):
        provider = AWSProvider({"sso_profiles": ["dev"]})
        assert provider.validate_config() == []

    def test_validate_config_empty_profiles(self):
        provider = AWSProvider({"sso_profiles": []})
        assert "sso_profiles" in provider.validate_config()

    def test_validate_config_missing(self):
        provider = AWSProvider({})
        assert "sso_profiles" in provider.validate_config()

    def test_setup_dry_run(self):
        provider = AWSProvider({"sso_profiles": ["dev", "prd"]})
        assert provider.setup(dry_run=True) is True

    @patch("cliauth.providers.aws.run")
    def test_setup_success(self, mock_run):
        mock_run.return_value = RunResult(0, "", "")
        provider = AWSProvider({"sso_profiles": ["dev", "prd"]})
        assert provider.setup() is True
        assert mock_run.call_count == 2

    @patch("cliauth.providers.aws.run")
    def test_setup_partial_failure(self, mock_run):
        mock_run.side_effect = [
            RunResult(0, "", ""),
            RunResult(1, "", "error"),
        ]
        provider = AWSProvider({"sso_profiles": ["dev", "prd"]})
        assert provider.setup() is False

    @patch("cliauth.providers.aws.run")
    def test_status_all_ok(self, mock_run):
        mock_run.return_value = RunResult(0, '{"Account": "123"}', "")
        provider = AWSProvider({"sso_profiles": ["dev", "prd"]})
        rows = provider.status()
        assert len(rows) == 2
        assert all(ok for _, ok, _ in rows)

    @patch("cliauth.providers.aws.run")
    def test_status_expired(self, mock_run):
        mock_run.return_value = RunResult(1, "", "Error: SSO session expired")
        provider = AWSProvider({"sso_profiles": ["dev"]})
        rows = provider.status()
        assert rows[0][1] is False
