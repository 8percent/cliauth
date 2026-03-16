import pytest


@pytest.fixture
def tmp_config(tmp_path):
    config_file = tmp_path / "config.toml"
    config_file.write_text(
        """
[gh]
token = "ghp_test1234567890abcdef"

[aws]
sso_profiles = ["dev-profile", "prd-profile"]

[sentry]
auth_token = "sntryu_test1234567890abcdef"
org = "test-org"
project = "test-project"

[acli]
site = "test.atlassian.net"
email = "test@example.com"
api_token = "atlassian_test_token_1234"
"""
    )
    return config_file


@pytest.fixture
def empty_config(tmp_path):
    config_file = tmp_path / "config.toml"
    config_file.write_text(
        """
[gh]
token = ""

[aws]
sso_profiles = []

[sentry]
auth_token = ""
org = ""
project = ""

[acli]
site = ""
email = ""
api_token = ""
"""
    )
    return config_file


@pytest.fixture(autouse=True)
def _no_default_config(monkeypatch, tmp_path):
    """Prevent tests from reading/writing the real config file."""
    fake_path = tmp_path / "no_config" / "config.toml"
    monkeypatch.setattr("cliauth.config.DEFAULT_CONFIG_PATH", fake_path)
    monkeypatch.setattr("cliauth.config.DEFAULT_CONFIG_DIR", fake_path.parent)
