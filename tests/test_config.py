import pytest

from cliauth.config import (
    get_masked_config,
    init_config,
    load_config,
    mask_token,
)


class TestLoadConfig:
    def test_load_valid_config(self, tmp_config):
        config = load_config(tmp_config)
        assert config["gh"]["token"] == "ghp_test1234567890abcdef"
        assert config["aws"]["sso_profiles"] == ["dev-profile", "prd-profile"]
        assert config["sentry"]["auth_token"] == "sntryu_test1234567890abcdef"
        assert config["acli"]["site"] == "test.atlassian.net"

    def test_load_missing_file(self, tmp_path):
        missing = tmp_path / "nonexistent.toml"
        with pytest.raises(FileNotFoundError, match="Config file not found"):
            load_config(missing)


class TestInitConfig:
    def test_init_creates_file(self, tmp_path):
        path = tmp_path / "new_config.toml"
        result = init_config(path)
        assert result == path
        assert path.exists()

        config = load_config(path)
        assert "gh" in config
        assert "aws" in config
        assert "sentry" in config
        assert "acli" in config

    def test_init_refuses_overwrite(self, tmp_config):
        with pytest.raises(FileExistsError, match="already exists"):
            init_config(tmp_config)

    def test_init_force_overwrite(self, tmp_config):
        result = init_config(tmp_config, force=True)
        assert result == tmp_config

    def test_init_sets_permissions(self, tmp_path):
        path = tmp_path / "secure.toml"
        init_config(path)
        assert oct(path.stat().st_mode & 0o777) == "0o600"


class TestMaskToken:
    def test_mask_long_token(self):
        assert mask_token("ghp_v1CBPhj2wnuEBJ2YDdU09") == "ghp_...dU09"

    def test_mask_short_token(self):
        assert mask_token("abc") == "***"

    def test_mask_empty_token(self):
        assert mask_token("") == "***"


class TestGetMaskedConfig:
    def test_masks_secret_keys(self):
        config = {
            "gh": {"token": "ghp_v1CBPhj2wnuEBJ2YDdU09"},
            "sentry": {"auth_token": "sntryu_1234567890abcdef", "org": "myorg"},
            "acli": {"api_token": "atlassian_token_here", "site": "test.net"},
        }
        masked = get_masked_config(config)
        assert masked["gh"]["token"] == "ghp_...dU09"
        assert masked["sentry"]["auth_token"] == "sntr...cdef"
        assert masked["sentry"]["org"] == "myorg"
        assert masked["acli"]["api_token"] == "atla...here"
        assert masked["acli"]["site"] == "test.net"
