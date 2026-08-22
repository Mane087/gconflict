"""Safe filesystem snapshots used by gconflict."""

from .snapshot import (
    ConcurrentModificationError,
    TextFileSnapshot,
    load_text_file,
    save_text_file,
)

__all__ = [
    "ConcurrentModificationError",
    "TextFileSnapshot",
    "load_text_file",
    "save_text_file",
]
