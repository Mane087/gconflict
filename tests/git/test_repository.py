from pathlib import Path
import subprocess
from unittest.mock import Mock, call

import pytest

from gconflict.git.repository import GitRepository
from gconflict.git.operation import GitOperation
from gconflict.models.conflicted_file import ConflictedFile, ConflictType


def test_root_from_root_and_subdirectory(tmp_path: Path) -> None:
    subprocess.run(["git", "init", str(tmp_path)], check=True, capture_output=True)
    nested = tmp_path / "nested"
    nested.mkdir()

    repository = GitRepository()

    assert repository.root(tmp_path) == tmp_path
    assert repository.root(nested) == tmp_path


def test_root_rejects_non_repository(tmp_path: Path) -> None:
    with pytest.raises(RuntimeError):
        GitRepository().root(tmp_path)


def test_conflicted_files_delegates_to_client_and_preserves_cwd(tmp_path: Path) -> None:
    client = Mock()
    client.run.return_value = subprocess.CompletedProcess([], 0, stdout="file.txt\n")

    assert GitRepository(client).conflicted_files(tmp_path) == [Path("file.txt")]
    client.run.assert_called_once_with(
        ["diff", "--name-only", "--diff-filter=U"], cwd=tmp_path
    )


def test_conflicted_files_preserves_order_and_ignores_empty_lines() -> None:
    client = Mock()
    client.run.return_value = subprocess.CompletedProcess(
        [], 0, stdout="first.txt\nsecond/file.txt\n\n"
    )

    assert GitRepository(client).conflicted_files() == [
        Path("first.txt"),
        Path("second/file.txt"),
    ]


def test_conflicted_files_returns_empty_for_empty_output() -> None:
    client = Mock()
    client.run.return_value = subprocess.CompletedProcess([], 0, stdout="")

    assert GitRepository(client).conflicted_files() == []


def test_conflicted_files_propagates_client_errors() -> None:
    client = Mock()
    error = RuntimeError("git failed")
    client.run.side_effect = error

    with pytest.raises(RuntimeError) as raised:
        GitRepository(client).conflicted_files()

    assert raised.value is error


def test_conflicted_file_descriptors_uses_repository_root(tmp_path: Path) -> None:
    repository = GitRepository(Mock())
    repository.root = Mock(return_value=tmp_path)
    expected = [ConflictedFile(Path("file.txt"), ConflictType.ADD_ADD)]
    repository.index.conflicted_file_descriptors = Mock(return_value=expected)

    assert repository.conflicted_file_descriptors("nested") == expected
    repository.root.assert_called_once_with("nested")
    repository.index.conflicted_file_descriptors.assert_called_once_with(tmp_path)


def test_stage_uses_repository_root_and_relative_path(tmp_path: Path) -> None:
    client = Mock()
    root = tmp_path / "repository"
    client.run.side_effect = [
        subprocess.CompletedProcess([], 0, stdout=f"{root}\n"),
        subprocess.CompletedProcess([], 0, stdout=""),
    ]

    GitRepository(client).stage(Path("nested/file.txt"), cwd=tmp_path)

    assert client.run.call_args_list == [
        call(["rev-parse", "--show-toplevel"], cwd=tmp_path),
        call(["add", "--", "nested/file.txt"], cwd=root),
    ]


@pytest.mark.parametrize("path", [Path("/outside.txt"), Path("../outside.txt")])
def test_stage_rejects_unconfined_path_before_git_add(
    tmp_path: Path, path: Path
) -> None:
    client = Mock()
    client.run.return_value = subprocess.CompletedProcess(
        [], 0, stdout=f"{tmp_path}\n"
    )

    with pytest.raises(ValueError, match="relative|escapes"):
        GitRepository(client).stage(path, cwd=tmp_path)

    client.run.assert_called_once_with(
        ["rev-parse", "--show-toplevel"], cwd=tmp_path
    )


def test_stage_rejects_symlink_escape_before_git_add(tmp_path: Path) -> None:
    outside = tmp_path.parent / "outside-repository"
    outside.mkdir()
    (tmp_path / "linked").symlink_to(outside, target_is_directory=True)
    client = Mock()
    client.run.return_value = subprocess.CompletedProcess(
        [], 0, stdout=f"{tmp_path}\n"
    )

    with pytest.raises(ValueError, match="resolves outside"):
        GitRepository(client).stage(Path("linked/file.txt"), cwd=tmp_path)

    client.run.assert_called_once_with(
        ["rev-parse", "--show-toplevel"], cwd=tmp_path
    )


@pytest.mark.parametrize("path_name", ["rebase-merge", "rebase-apply"])
@pytest.mark.parametrize("absolute", [False, True])
def test_operation_detects_rebase_path(
    tmp_path: Path, path_name: str, absolute: bool
) -> None:
    client = Mock()
    marker = tmp_path / path_name
    marker.mkdir()
    valid_path = str(marker) if absolute else path_name
    client.run.side_effect = [
        subprocess.CompletedProcess(
            [], 0 if path_name == "rebase-merge" else 1,
            stdout=(valid_path if path_name == "rebase-merge" else ""),
        ),
        subprocess.CompletedProcess(
            [], 0 if path_name == "rebase-apply" else 1,
            stdout=(valid_path if path_name == "rebase-apply" else ""),
        ),
    ]

    assert GitRepository(client).operation(tmp_path) is GitOperation.REBASE
    assert client.run.call_args_list[0].kwargs == {"cwd": tmp_path, "check": False}


@pytest.mark.parametrize(
    ("marker", "operation"),
    [
        ("CHERRY_PICK_HEAD", GitOperation.CHERRY_PICK),
        ("REVERT_HEAD", GitOperation.REVERT),
        ("MERGE_HEAD", GitOperation.MERGE),
    ],
)
def test_operation_detects_marker(tmp_path: Path, marker: str, operation: GitOperation) -> None:
    client = Mock()
    markers = ["CHERRY_PICK_HEAD", "REVERT_HEAD", "MERGE_HEAD"]
    marker_index = markers.index(marker)
    client.run.side_effect = [
        subprocess.CompletedProcess([], 1, stdout="") for _ in range(2 + marker_index)
    ] + [subprocess.CompletedProcess([], 0, stdout="head\n")]

    assert GitRepository(client).operation(tmp_path) is operation
    assert client.run.call_args_list[-1] == call(
        ["rev-parse", "-q", "--verify", marker], cwd=tmp_path, check=False
    )


def test_operation_returns_none_and_preserves_cwd() -> None:
    client = Mock()
    client.run.return_value = subprocess.CompletedProcess([], 1, stdout="")

    assert GitRepository(client).operation("work") is GitOperation.NONE
    assert client.run.call_args_list[-1] == call(
        ["rev-parse", "-q", "--verify", "MERGE_HEAD"], cwd="work", check=False
    )


@pytest.mark.parametrize(
    ("active_marker", "expected"),
    [
        ("REBASE", GitOperation.REBASE),
        ("CHERRY_PICK_HEAD", GitOperation.CHERRY_PICK),
        ("REVERT_HEAD", GitOperation.REVERT),
    ],
)
def test_operation_precedence_is_rebase_then_cherry_pick_then_revert_then_merge(
    tmp_path: Path, active_marker: str, expected: GitOperation
) -> None:
    client = Mock()
    client.run.side_effect = [
        subprocess.CompletedProcess([], 0, stdout=str(tmp_path / "rebase-merge"))
        if active_marker == "REBASE"
        else subprocess.CompletedProcess([], 1, stdout=""),
        subprocess.CompletedProcess([], 1, stdout="")
        if active_marker != "REBASE"
        else subprocess.CompletedProcess([], 1, stdout=""),
        *[
            subprocess.CompletedProcess(
                [],
                0
                if active_marker == "REBASE"
                or active_marker == "CHERRY_PICK_HEAD"
                or (active_marker == "REVERT_HEAD" and marker != "CHERRY_PICK_HEAD")
                else 1,
                stdout="head\n",
            )
            for marker in ("CHERRY_PICK_HEAD", "REVERT_HEAD", "MERGE_HEAD")
        ],
    ]

    (tmp_path / "rebase-merge").mkdir()
    assert GitRepository(client).operation(tmp_path) is expected


def test_stage_adds_a_real_file_to_a_real_index(tmp_path: Path) -> None:
    subprocess.run(["git", "init", str(tmp_path)], check=True, capture_output=True)
    nested = tmp_path / "nested"
    nested.mkdir()
    (nested / "file.txt").write_text("content\n", encoding="utf-8")

    GitRepository().stage(Path("nested/file.txt"), cwd=tmp_path)

    staged = subprocess.run(
        ["git", "diff", "--cached", "--name-only"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=True,
    )
    assert staged.stdout.splitlines() == ["nested/file.txt"]
