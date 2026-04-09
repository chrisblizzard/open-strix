import subprocess
from pathlib import Path

import pytest

from open_strix.app import _git_sync


def test_git_sync_no_git_dir(tmp_path: Path) -> None:
    assert _git_sync(tmp_path) == "skip: not a git repo"


def test_git_sync_clean_repo(tmp_path: Path) -> None:
    subprocess.run(["git", "init"], cwd=tmp_path, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "test@test.com"],
        cwd=tmp_path, capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "test"],
        cwd=tmp_path, capture_output=True,
    )
    subprocess.run(
        ["git", "commit", "--allow-empty", "-m", "init"],
        cwd=tmp_path, capture_output=True,
    )
    assert _git_sync(tmp_path) == "clean: no changes"


def test_git_sync_commits_dirty_repo(tmp_path: Path) -> None:
    subprocess.run(["git", "init"], cwd=tmp_path, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "test@test.com"],
        cwd=tmp_path, capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "test"],
        cwd=tmp_path, capture_output=True,
    )
    subprocess.run(
        ["git", "commit", "--allow-empty", "-m", "init"],
        cwd=tmp_path, capture_output=True,
    )
    (tmp_path / "test.txt").write_text("hello")
    result = _git_sync(tmp_path)
    # No remote configured, so push fails — but commit should succeed
    assert "git push failed:" in result


def test_git_sync_timeout_raises(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A hanging subprocess raises TimeoutExpired instead of blocking forever."""
    (tmp_path / ".git").mkdir()

    original_run = subprocess.run

    def slow_run(cmd, **kwargs):
        if cmd[0] == "git":
            raise subprocess.TimeoutExpired(cmd, kwargs.get("timeout", 30))
        return original_run(cmd, **kwargs)

    monkeypatch.setattr(subprocess, "run", slow_run)
    with pytest.raises(subprocess.TimeoutExpired):
        _git_sync(tmp_path)
