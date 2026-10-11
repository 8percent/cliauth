from pathlib import Path

import pytest
from typer.testing import CliRunner

from cliauth.cli import app
from cliauth.providers import aws as aws_module
from cliauth.providers.gh import GitHubProvider

runner = CliRunner()


def test_setup_skip_names_aws_v2_search_scope(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
):
    config = tmp_path / "config.toml"
    config.write_text('[aws]\nsso_profiles = ["dev"]\n')
    monkeypatch.setattr(aws_module, "find_aws_v2", lambda: None)

    result = runner.invoke(app, ["setup", "aws", "--config", str(config)])

    assert result.exit_code == 1
    assert (
        "Skipping: AWS CLI v2 not found (checked PATH and common install paths)"
        in result.output
    )


def test_missing_binary_message_defaults_to_path_lookup():
    assert GitHubProvider({}).missing_binary_message() == "gh not found on PATH"
