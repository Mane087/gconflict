"""Helpers for reading unmerged entries from the Git index."""

from dataclasses import dataclass
from enum import IntEnum
from pathlib import Path

from .client import GitClient
from gconflict.models.conflicted_file import ConflictedFile, ConflictType


class GitStage(IntEnum):
    """Stage of an unmerged index entry."""

    BASE = 1
    OURS = 2
    THEIRS = 3


@dataclass(frozen=True)
class UnmergedEntry:
    """An unmerged entry reported by Git."""

    mode: str
    object_id: str
    stage: GitStage
    path: Path


class GitIndex:
    """Read index information through an injected Git client."""

    def __init__(self, client: GitClient | None = None) -> None:
        self.client = client or GitClient()

    def unmerged_entries(self, cwd: str | Path | None = None) -> list[UnmergedEntry]:
        """Return unmerged index entries in Git's output order."""
        result = self.client.run(["ls-files", "-u"], cwd=cwd)
        entries: list[UnmergedEntry] = []
        for line in result.stdout.splitlines():
            metadata, separator, path = line.partition("\t")
            fields = metadata.split()
            if not separator or len(fields) != 3 or not path:
                raise ValueError(f"Malformed Git index record: {line!r}")
            mode, object_id, stage_value = fields
            try:
                stage = GitStage(int(stage_value))
            except (ValueError, TypeError):
                raise ValueError(f"Malformed Git index record: {line!r}") from None
            entries.append(UnmergedEntry(mode, object_id, stage, Path(path)))
        return entries

    def conflicted_file_descriptors(
        self, cwd: str | Path | None = None
    ) -> list[ConflictedFile]:
        """Classify conflicted paths from their unmerged index stages."""
        stages_by_path: dict[Path, set[GitStage]] = {}
        for entry in self.unmerged_entries(cwd):
            stages_by_path.setdefault(entry.path, set()).add(entry.stage)

        root = Path.cwd() if cwd is None else Path(cwd)
        return [
            ConflictedFile(path, self._classify(path, stages, root))
            for path, stages in stages_by_path.items()
        ]

    @staticmethod
    def _classify(path: Path, stages: set[GitStage], root: Path) -> ConflictType:
        if stages == {GitStage.OURS, GitStage.THEIRS}:
            return ConflictType.ADD_ADD
        if stages in (
            {GitStage.BASE, GitStage.OURS},
            {GitStage.BASE, GitStage.THEIRS},
        ):
            return ConflictType.MODIFY_DELETE
        if stages == {GitStage.BASE, GitStage.OURS, GitStage.THEIRS}:
            try:
                text = (root / path).read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                return ConflictType.OTHER
            if GitIndex._has_standard_markers(text):
                return ConflictType.CONTENT
        return ConflictType.OTHER

    @staticmethod
    def _has_standard_markers(text: str) -> bool:
        marker = 0
        for line in text.splitlines():
            if marker == 0 and line.startswith("<<<<<<< "):
                marker = 1
            elif marker == 1 and line == "=======":
                marker = 2
            elif marker == 2 and line.startswith(">>>>>>> "):
                return True
        return False
