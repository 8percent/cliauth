import os
import tomllib
from pathlib import Path
from typing import Any

import tomli_w

DEFAULT_CONFIG_DIR = Path.home() / ".config" / "cliauth"
DEFAULT_CONFIG_PATH = DEFAULT_CONFIG_DIR / "config.toml"

CONFIG_TEMPLATE: dict[str, Any] = {
    "gh": {
        "token": "",
    },
    "aws": {
        "sso_profiles": [],
    },
    "sentry": {
        "auth_token": "",
        "org": "",
        "project": "",
    },
    "acli": {
        "site": "",
        "email": "",
        "api_token": "",
    },
}

CONFIG_COMMENTS = """# cliauth configuration file
# https://github.com/8percent/cliauth
#
# Fill in your tokens and settings below.
# Run `cliauth setup` to authenticate all configured CLIs.
# Run `cliauth status` to check authentication status.
#
# Security: Keep this file private.
#   chmod 600 ~/.config/cliauth/config.toml

"""


def get_config_path() -> Path:
    env_path = os.environ.get("CLIAUTH_CONFIG")
    if env_path:
        return Path(env_path)
    return DEFAULT_CONFIG_PATH


def load_config(config_path: Path | None = None) -> dict[str, Any]:
    path = config_path or get_config_path()
    if not path.exists():
        raise FileNotFoundError(
            f"Config file not found: {path}\nRun `cliauth config init` to create one."
        )
    with open(path, "rb") as f:
        return tomllib.load(f)


def init_config(config_path: Path | None = None, force: bool = False) -> Path:
    path = config_path or get_config_path()
    if path.exists() and not force:
        raise FileExistsError(
            f"Config file already exists: {path}\nUse --force to overwrite."
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    toml_content = tomli_w.dumps(CONFIG_TEMPLATE)
    with open(path, "w") as f:
        f.write(CONFIG_COMMENTS)
        f.write(toml_content)
    path.chmod(0o600)
    return path


def mask_token(token: str) -> str:
    if len(token) <= 8:
        return "***"
    return f"{token[:4]}...{token[-4:]}"


def get_masked_config(config: dict[str, Any]) -> dict[str, Any]:
    masked = {}
    secret_keys = {"token", "auth_token", "api_token"}
    for section, values in config.items():
        if not isinstance(values, dict):
            masked[section] = values
            continue
        masked[section] = {}
        for key, value in values.items():
            if key in secret_keys and isinstance(value, str) and value:
                masked[section][key] = mask_token(value)
            else:
                masked[section][key] = value
    return masked
