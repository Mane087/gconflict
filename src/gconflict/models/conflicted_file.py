"""Descriptors for files with unresolved Git conflicts."""

from dataclasses import dataclass
from enum import Enum
from pathlib import Path


class ConflictType(Enum):
    """Kinds of unresolved conflicts supported by Git's index stages."""

    ADD_ADD = "add_add"
    MODIFY_DELETE = "modify_delete"
    CONTENT = "content"
    OTHER = "other"


@dataclass(frozen=True)
class ConflictedFile:
    """A conflicted repository path and its classified conflict type."""

    path: Path
    conflict_type: ConflictType
