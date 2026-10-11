import os
import stat
import subprocess
from pathlib import Path

import pytest

from cliauth.providers import aws as aws_module
from cliauth.providers.aws import AWSProvider, aws_candidates, find_aws_v2
from cliauth.runner import RunResult

AWS = "/fake/aws"


class FakeRun:
    """Answer configure/login/sts calls, recording every call."""

    def __init__(
        self, sessions: dict[str, str], login_rc: int = 0, login_timeout: bool = False
    ):
        self.sessions = sessions
        self.login_rc = login_rc
        self.login_timeout = login_timeout
        self.calls: list[list[str]] = []

    def __call__(self, args: list[str], **kwargs: object) -> RunResult:
        self.calls.append(list(args))
        if args[1:3] == ["configure", "get"]:
            session = self.sessions.get(args[-1])
            return RunResult(0, session, "") if session else RunResult(1, "", "")
        if args[1:3] == ["sso", "login"]:
            if self.login_timeout:
                raise subprocess.TimeoutExpired(args, kwargs.get("timeout"))
            return RunResult(self.login_rc, "", "login error" if self.login_rc else "")
        if args[1:3] == ["sts", "get-caller-identity"]:
            return RunResult(0, '{"Account": "123"}', "")
        raise AssertionError(f"unexpected call: {args}")

    @property
    def logins(self) -> list[list[str]]:
        return [call for call in self.calls if call[1:3] == ["sso", "login"]]


@pytest.fixture(autouse=True)
def v2_present(monkeypatch: pytest.MonkeyPatch):
    find_aws_v2.cache_clear()
    monkeypatch.setattr(aws_module, "find_aws_v2", lambda: AWS)
    yield
    find_aws_v2.cache_clear()


def make_aws(
    directory: Path, name: str, version_line: str, executable: bool = True
) -> str:
    path = directory / name
    path.write_text(f'#!/bin/sh\necho "{version_line}"\n')
    if executable:
        path.chmod(path.stat().st_mode | stat.S_IEXEC)
    return str(path)


class TestAWSProvider:
    def test_validate_config_ok(self):
        assert AWSProvider({"sso_profiles": ["dev"]}).validate_config() == []

    def test_validate_config_empty_profiles(self):
        assert "sso_profiles" in AWSProvider({"sso_profiles": []}).validate_config()

    def test_validate_config_missing(self):
        assert "sso_profiles" in AWSProvider({}).validate_config()

    def test_is_installed_requires_v2(self, monkeypatch: pytest.MonkeyPatch):
        assert AWSProvider({"sso_profiles": ["dev"]}).is_installed() is True
        monkeypatch.setattr(aws_module, "find_aws_v2", lambda: None)
        assert AWSProvider({"sso_profiles": ["dev"]}).is_installed() is False

    def test_missing_binary_message_names_v2_and_search_scope(self):
        assert AWSProvider({}).missing_binary_message() == (
            "AWS CLI v2 not found (checked PATH and common install paths)"
        )

    def test_setup_dry_run_lists_one_login_per_session(self, monkeypatch, capsys):
        fake = FakeRun({"dev": "SHARED", "prd": "SHARED"})
        monkeypatch.setattr(aws_module, "run", fake)
        assert AWSProvider({"sso_profiles": ["dev", "prd"]}).setup(dry_run=True) is True
        out = capsys.readouterr().out
        assert out.count("Would run:") == 1
        assert f"Would run: {AWS} sso login --sso-session SHARED" in out
        assert fake.logins == []

    def test_setup_dry_run_shell_quotes_the_command(self, monkeypatch, capsys):
        monkeypatch.setattr(aws_module, "find_aws_v2", lambda: "/fake dir/aws")
        monkeypatch.setattr(aws_module, "run", FakeRun({"dev": "SHARED"}))
        assert AWSProvider({"sso_profiles": ["dev"]}).setup(dry_run=True) is True
        assert (
            "Would run: '/fake dir/aws' sso login --sso-session SHARED"
            in capsys.readouterr().out
        )

    def test_setup_logs_in_once_per_session(self, monkeypatch):
        fake = FakeRun({"dev": "SHARED", "prd": "SHARED"})
        monkeypatch.setattr(aws_module, "run", fake)
        assert AWSProvider({"sso_profiles": ["dev", "prd"]}).setup() is True
        assert fake.logins == [[AWS, "sso", "login", "--sso-session", "SHARED"]]

    def test_setup_keeps_profile_order_for_distinct_sessions(self, monkeypatch):
        fake = FakeRun({"prd": "PRD", "dev": "DEV"})
        monkeypatch.setattr(aws_module, "run", fake)
        assert AWSProvider({"sso_profiles": ["prd", "dev"]}).setup() is True
        assert [call[-1] for call in fake.logins] == ["PRD", "DEV"]

    def test_setup_falls_back_to_profile_without_session(self, monkeypatch):
        fake = FakeRun({"dev": "DEV"})
        monkeypatch.setattr(aws_module, "run", fake)
        assert AWSProvider({"sso_profiles": ["dev", "legacy"]}).setup() is True
        assert fake.logins == [
            [AWS, "sso", "login", "--sso-session", "DEV"],
            [AWS, "sso", "login", "--profile", "legacy"],
        ]

    def test_setup_reports_login_failure(self, monkeypatch):
        fake = FakeRun({"dev": "DEV"}, login_rc=1)
        monkeypatch.setattr(aws_module, "run", fake)
        assert AWSProvider({"sso_profiles": ["dev"]}).setup() is False

    def test_setup_reports_login_timeout_without_raising(self, monkeypatch, capsys):
        fake = FakeRun({"dev": "DEV"}, login_timeout=True)
        monkeypatch.setattr(aws_module, "run", fake)
        assert AWSProvider({"sso_profiles": ["dev"]}).setup() is False
        assert (
            "session DEV timed out waiting for browser approval (300s)"
            in capsys.readouterr().out
        )

    def test_setup_without_v2_fails_before_running_anything(self, monkeypatch, capsys):
        fake = FakeRun({})
        monkeypatch.setattr(aws_module, "run", fake)
        monkeypatch.setattr(aws_module, "find_aws_v2", lambda: None)
        assert AWSProvider({"sso_profiles": ["dev"]}).setup() is False
        assert fake.calls == []
        assert "AWS CLI v2 not found" in capsys.readouterr().out

    def test_status_all_ok_uses_v2_path(self, monkeypatch):
        fake = FakeRun({})
        monkeypatch.setattr(aws_module, "run", fake)
        rows = AWSProvider({"sso_profiles": ["dev", "prd"]}).status()
        assert len(rows) == 2 and all(ok for _, ok, _ in rows)
        assert all(call[0] == AWS for call in fake.calls)

    def test_status_expired(self, monkeypatch):
        monkeypatch.setattr(
            aws_module,
            "run",
            lambda args, **kwargs: RunResult(1, "", "Error: SSO session expired"),
        )
        rows = AWSProvider({"sso_profiles": ["dev"]}).status()
        assert rows[0][1] is False
        assert "expired" in rows[0][2]


class TestFindAwsV2:
    def test_prefers_first_v2_candidate(self, monkeypatch, tmp_path: Path):
        v1 = make_aws(tmp_path, "aws1", "aws-cli/1.44.81 Python/3.10")
        v2 = make_aws(tmp_path, "aws2", "aws-cli/2.28.14 Python/3.13")
        monkeypatch.setattr(aws_module, "aws_candidates", lambda: [v1, v2])
        monkeypatch.setattr(aws_module, "find_aws_v2", find_aws_v2.__wrapped__)
        assert aws_module.find_aws_v2() == v2

    def test_picks_first_of_several_v2_candidates(self, monkeypatch, tmp_path: Path):
        first = make_aws(tmp_path, "aws-first", "aws-cli/2.28.14 Python/3.13")
        second = make_aws(tmp_path, "aws-second", "aws-cli/2.30.0 Python/3.13")
        monkeypatch.setattr(aws_module, "aws_candidates", lambda: [first, second])
        monkeypatch.setattr(aws_module, "find_aws_v2", find_aws_v2.__wrapped__)
        assert aws_module.find_aws_v2() == first

    def test_none_when_only_v1(self, monkeypatch, tmp_path: Path):
        v1 = make_aws(tmp_path, "aws1", "aws-cli/1.44.81 Python/3.10")
        monkeypatch.setattr(
            aws_module, "aws_candidates", lambda: [v1, str(tmp_path / "missing")]
        )
        monkeypatch.setattr(aws_module, "find_aws_v2", find_aws_v2.__wrapped__)
        assert aws_module.find_aws_v2() is None

    def test_skips_non_executable_and_broken_candidates(
        self, monkeypatch, tmp_path: Path
    ):
        plain = make_aws(tmp_path, "plain", "aws-cli/2.0.0", executable=False)
        broken = tmp_path / "broken"
        broken.write_text("#!/nonexistent/interpreter\n")
        broken.chmod(broken.stat().st_mode | stat.S_IEXEC)
        v2 = make_aws(tmp_path, "aws2", "aws-cli/2.28.14 Python/3.13")
        monkeypatch.setattr(
            aws_module, "aws_candidates", lambda: [plain, str(broken), v2]
        )
        monkeypatch.setattr(aws_module, "find_aws_v2", find_aws_v2.__wrapped__)
        assert aws_module.find_aws_v2() == v2

    def test_candidates_put_path_entries_before_fallbacks(self, monkeypatch):
        monkeypatch.setenv("PATH", os.pathsep.join(["/a", "", "/b"]))
        candidates = aws_candidates()
        assert candidates[:2] == ["/a/aws", "/b/aws"]
        assert candidates[2:] == list(aws_module.AWS_V2_FALLBACKS)

    def test_candidates_are_deduplicated_keeping_first_position(self, monkeypatch):
        fallback_dir = os.path.dirname(aws_module.AWS_V2_FALLBACKS[0])
        monkeypatch.setenv("PATH", os.pathsep.join(["/a", fallback_dir, "/a"]))
        assert aws_candidates() == ["/a/aws", *aws_module.AWS_V2_FALLBACKS]
