from pathlib import Path
from unittest.mock import Mock, call

import pytest

from gconflict.filesystem.snapshot import ConcurrentModificationError
from gconflict.models.resolution import Resolution
from gconflict.git.operation import GitOperation
from gconflict.models.conflicted_file import ConflictedFile, ConflictType
from gconflict.services.conflict_service import ConflictService


def test_resolve_file_uses_incoming_and_preserves_exterior_text(tmp_path: Path) -> None:
    path = tmp_path / "conflicted.txt"
    path.write_text(
        "before\n<<<<<<< HEAD\ncurrent\n=======\nincoming\n>>>>>>> branch\nafter\n",
        encoding="utf-8",
    )
    service = ConflictService(repository=Mock())
    snapshot, conflicts = service.load_conflicts(path)

    refreshed = service.resolve_file(snapshot, conflicts, [Resolution.INCOMING])

    assert refreshed.text == "before\nincoming\nafter\n"
    assert path.read_text(encoding="utf-8") == "before\nincoming\nafter\n"


def test_resolve_file_requires_manual_content(tmp_path: Path) -> None:
    path = tmp_path / "conflicted.txt"
    path.write_text(
        "<<<<<<< HEAD\ncurrent\n=======\nincoming\n>>>>>>> branch\n",
        encoding="utf-8",
    )
    service = ConflictService(repository=Mock())
    snapshot, conflicts = service.load_conflicts(path)

    with pytest.raises(ValueError, match="manual content is required"):
        service.resolve_file(snapshot, conflicts, [Resolution.MANUAL])


def test_resolve_file_propagates_concurrent_modification(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "conflicted.txt"
    path.write_text(
        "<<<<<<< HEAD\ncurrent\n=======\nincoming\n>>>>>>> branch\n",
        encoding="utf-8",
    )
    service = ConflictService(repository=Mock())
    snapshot, conflicts = service.load_conflicts(path)

    def raise_concurrent_modification(*_args: object) -> None:
        raise ConcurrentModificationError("changed")

    monkeypatch.setattr(
        "gconflict.services.conflict_service.save_text_file",
        raise_concurrent_modification,
    )

    with pytest.raises(ConcurrentModificationError, match="changed"):
        service.resolve_file(snapshot, conflicts, [Resolution.CURRENT])


def test_conflicted_files_delegates_without_staging(tmp_path: Path) -> None:
    repository = Mock()
    repository.conflicted_files.return_value = [Path("one.txt")]
    service = ConflictService(repository=repository)

    assert service.conflicted_files(tmp_path) == [Path("one.txt")]
    repository.conflicted_files.assert_called_once_with(tmp_path)
    repository.stage.assert_not_called()


def test_conflicted_file_descriptors_delegates_without_staging(tmp_path: Path) -> None:
    repository = Mock()
    descriptors = [ConflictedFile(Path("one.txt"), ConflictType.CONTENT)]
    repository.conflicted_file_descriptors.return_value = descriptors

    assert ConflictService(repository).conflicted_file_descriptors(tmp_path) == descriptors
    repository.conflicted_file_descriptors.assert_called_once_with(tmp_path)
    repository.stage.assert_not_called()


def test_mark_resolved_rejects_remaining_conflict_markers(tmp_path: Path) -> None:
    path = tmp_path / "conflicted.txt"
    path.write_text(
        "<<<<<<< HEAD\ncurrent\n=======\nincoming\n>>>>>>> branch\n",
        encoding="utf-8",
    )
    repository = Mock()
    repository.root.return_value = tmp_path

    with pytest.raises(ValueError, match="conflict markers remain"):
        ConflictService(repository).mark_resolved(Path("conflicted.txt"), cwd=tmp_path)

    repository.conflicted_files.assert_not_called()
    repository.stage.assert_not_called()


def test_mark_resolved_requires_git_conflicted_path(tmp_path: Path) -> None:
    path = tmp_path / "resolved.txt"
    path.write_text("resolved\n", encoding="utf-8")
    repository = Mock()
    repository.root.return_value = tmp_path
    repository.conflicted_files.return_value = []

    with pytest.raises(ValueError, match="Git does not report it as conflicted"):
        ConflictService(repository).mark_resolved(Path("resolved.txt"), cwd=tmp_path)

    repository.stage.assert_not_called()


def test_mark_resolved_stages_relative_path_and_postchecks(tmp_path: Path) -> None:
    path = tmp_path / "nested/resolved.txt"
    path.parent.mkdir()
    path.write_text("resolved\n", encoding="utf-8")
    repository = Mock()
    repository.root.return_value = tmp_path
    repository.conflicted_files.side_effect = [
        [Path("nested/resolved.txt")],
        [],
    ]

    ConflictService(repository).mark_resolved(Path("nested/resolved.txt"), cwd=tmp_path)

    repository.root.assert_called_once_with(tmp_path)
    repository.stage.assert_called_once_with(Path("nested/resolved.txt"), cwd=tmp_path)
    assert repository.conflicted_files.call_args_list == [
        call(tmp_path),
        call(tmp_path),
    ]


def test_mark_resolved_postcheck_reports_partial_mutation(tmp_path: Path) -> None:
    path = tmp_path / "resolved.txt"
    path.write_text("resolved\n", encoding="utf-8")
    repository = Mock()
    repository.root.return_value = tmp_path
    repository.conflicted_files.return_value = [Path("resolved.txt")]

    with pytest.raises(RuntimeError, match="index may have been partially modified"):
        ConflictService(repository).mark_resolved(Path("resolved.txt"), cwd=tmp_path)

    repository.stage.assert_called_once_with(Path("resolved.txt"), cwd=tmp_path)


@pytest.mark.parametrize("path", [Path("/outside.txt"), Path("../outside.txt")])
def test_mark_resolved_rejects_unconfined_path_before_loading(
    tmp_path: Path, path: Path
) -> None:
    repository = Mock()
    repository.root.return_value = tmp_path

    with pytest.raises(ValueError, match="relative|escapes"):
        ConflictService(repository).mark_resolved(path, cwd=tmp_path)

    repository.conflicted_files.assert_not_called()
    repository.stage.assert_not_called()


def test_mark_resolved_rejects_symlink_escape_before_loading(tmp_path: Path) -> None:
    outside = tmp_path.parent / "outside-service"
    outside.mkdir()
    (tmp_path / "linked").symlink_to(outside, target_is_directory=True)
    repository = Mock()
    repository.root.return_value = tmp_path

    with pytest.raises(ValueError, match="resolves outside"):
        ConflictService(repository).mark_resolved(
            Path("linked/resolved.txt"), cwd=tmp_path
        )

    repository.conflicted_files.assert_not_called()
    repository.stage.assert_not_called()


def test_context_composes_repository_state_into_labels() -> None:
    repository = Mock()
    repository.root.return_value = Path("/work/lynxweb")
    repository.current_branch.return_value = "feature/user-status"
    repository.incoming_ref.return_value = "main"
    repository.operation.return_value = GitOperation.MERGE

    context = ConflictService(repository).context("/work/lynxweb/lib")

    assert context.root == Path("/work/lynxweb")
    assert context.name == "lynxweb"
    assert context.branch == "feature/user-status"
    assert context.operation is GitOperation.MERGE
    assert context.current_label == "ours - feature/user-status"
    assert context.incoming_label == "theirs - main"
    repository.root.assert_called_once_with("/work/lynxweb/lib")
