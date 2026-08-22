"""Git operations currently in progress."""

from enum import Enum


class GitOperation(Enum):
    """Operation represented by Git's in-progress state markers."""

    NONE = "none"
    REBASE = "rebase"
    CHERRY_PICK = "cherry-pick"
    REVERT = "revert"
    MERGE = "merge"
