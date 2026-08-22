"""Git integration for gconflict."""

from .client import GitClient, GitResult
from .index import GitIndex, GitStage, UnmergedEntry
from .operation import GitOperation
from .repository import GitRepository

__all__ = [
    "GitClient",
    "GitIndex",
    "GitOperation",
    "GitRepository",
    "GitResult",
    "GitStage",
    "UnmergedEntry",
]
