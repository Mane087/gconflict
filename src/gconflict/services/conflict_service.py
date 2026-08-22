"""Coordinate loading and resolving conflicted files."""

from collections.abc import Sequence
from pathlib import Path

from gconflict.conflicts.parser import parse_conflicts
from gconflict.conflicts.reconstructor import reconstruct_text
from gconflict.conflicts.resolver import resolve_conflict
from gconflict.filesystem.snapshot import (
    PathLike,
    TextFileSnapshot,
    load_text_file,
    save_text_file,
)
from gconflict.git.repository import GitRepository, _confined_relative_path
from gconflict.models.conflict import Conflict
from gconflict.models.conflicted_file import ConflictedFile
from gconflict.models.repository_context import RepositoryContext, side_labels
from gconflict.models.resolution import Resolution


class ConflictService:
    """Coordinate Git conflict discovery and file conflict resolution."""

    def __init__(self, repository: GitRepository | None = None) -> None:
        self.repository = repository or GitRepository()

    def root(self, cwd: str | Path | None = None) -> Path:
        """Delegate repository-root discovery to Git."""
        return self.repository.root(cwd)

    def context(self, cwd: str | Path | None = None) -> RepositoryContext:
        """Gather the repository state the interface labels its two sides with."""
        root = self.repository.root(cwd)
        branch = self.repository.current_branch(root)
        incoming = self.repository.incoming_ref(root)
        operation = self.repository.operation(root)
        current_label, incoming_label = side_labels(operation, branch, incoming)
        return RepositoryContext(
            root=root,
            name=root.name,
            branch=branch,
            operation=operation,
            current_label=current_label,
            incoming_label=incoming_label,
        )

    def conflicted_files(self, cwd: str | Path | None = None) -> list[Path]:
        """Delegate unresolved-file discovery to the repository."""
        return self.repository.conflicted_files(cwd)

    def conflicted_file_descriptors(
        self, cwd: str | Path | None = None
    ) -> list[ConflictedFile]:
        """Delegate classified conflict discovery to the repository."""
        return self.repository.conflicted_file_descriptors(cwd)

    def mark_resolved(
        self, path: PathLike, cwd: str | Path | None = None
    ) -> None:
        """Stage a conflict-free file and verify Git no longer reports it unresolved."""
        root = self.repository.root(cwd)
        relative_path = _confined_relative_path(root, path)
        current_path = root / relative_path
        snapshot = load_text_file(current_path)

        if parse_conflicts(snapshot.text):
            raise ValueError(
                f"Cannot mark {relative_path} resolved: conflict markers remain."
            )

        if relative_path not in self.repository.conflicted_files(root):
            raise ValueError(
                f"Cannot mark {relative_path} resolved: Git does not report it as conflicted."
            )

        self.repository.stage(relative_path, cwd=root)

        if relative_path in self.repository.conflicted_files(root):
            raise RuntimeError(
                f"Failed to mark {relative_path} resolved: Git still reports it as "
                "conflicted after staging; the index may have been partially modified."
            )

    def load_conflicts(self, path: PathLike) -> tuple[TextFileSnapshot, list[Conflict]]:
        """Load a text snapshot and parse its conflicts."""
        snapshot = load_text_file(path)
        return snapshot, parse_conflicts(snapshot.text)

    def resolve_file(
        self,
        snapshot: TextFileSnapshot,
        conflicts: Sequence[Conflict],
        resolutions: Sequence[Resolution],
        manual: Sequence[list[str] | None] | None = None,
    ) -> TextFileSnapshot:
        """Resolve, reconstruct, and save a previously loaded snapshot."""
        if len(conflicts) != len(resolutions):
            raise ValueError("conflicts and resolutions must have the same length")
        if manual is not None and len(manual) != len(conflicts):
            raise ValueError("conflicts and manual content must have the same length")

        resolved: list[list[str]] = []
        for expected_index, (conflict, resolution) in enumerate(
            zip(conflicts, resolutions)
        ):
            if conflict.index != expected_index:
                raise ValueError("conflict indices must be ordered and contiguous")
            manual_content = None if manual is None else manual[expected_index]
            resolved.append(resolve_conflict(conflict, resolution, manual_content))

        text = reconstruct_text(snapshot.text, conflicts, resolved)
        return save_text_file(snapshot, text)
