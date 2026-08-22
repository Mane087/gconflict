from pathlib import Path

import pytest

from gconflict.git.client import GitClient


def test_run_passes_arguments_captures_output_and_cwd(monkeypatch, tmp_path: Path) -> None:
    calls = {}

    class Completed:
        stdout = "out"
        stderr = "err"
        returncode = 0

    def fake_run(*args, **kwargs):
        calls.update(args=args, kwargs=kwargs)
        return Completed()

    monkeypatch.setattr("gconflict.git.client.subprocess.run", fake_run)

    result = GitClient().run(["status", "--short"], cwd=tmp_path)

    assert calls["args"] == (["git", "status", "--short"],)
    assert calls["kwargs"] == {
        "cwd": tmp_path,
        "capture_output": True,
        "text": True,
        "check": False,
    }
    assert result.stdout == "out"
    assert result.stderr == "err"
    assert result.returncode == 0


def test_run_check_false_returns_failed_result(monkeypatch) -> None:
    class Completed:
        stdout = ""
        stderr = "failure"
        returncode = 1

    monkeypatch.setattr("gconflict.git.client.subprocess.run", lambda *a, **k: Completed())

    assert GitClient().run(["status"], check=False).returncode == 1


def test_run_check_true_raises(monkeypatch) -> None:
    class Completed:
        stdout = ""
        stderr = "failure"
        returncode = 1

    monkeypatch.setattr("gconflict.git.client.subprocess.run", lambda *a, **k: Completed())

    with pytest.raises(RuntimeError, match="failure"):
        GitClient().run(["status"])
