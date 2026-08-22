"""How many conflicts a conflicted file holds."""

from dataclasses import dataclass

from gconflict.models.conflicted_file import ConflictedFile, ConflictType


@dataclass(frozen=True)
class FileProgress:
    """A conflicted file and the number of content conflicts inside it."""

    file: ConflictedFile
    total: int

    @property
    def supported(self) -> bool:
        """Report whether gconflict can resolve this file at all."""
        return self.file.conflict_type is ConflictType.CONTENT
