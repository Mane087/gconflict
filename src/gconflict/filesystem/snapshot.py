"""UTF-8 text snapshots with guarded, atomic replacement.

The final identity check and :func:`os.replace` cannot be made one indivisible
operation with portable filesystem APIs.  Consequently, a residual TOCTOU
window remains between those operations.  Symlink checks reduce accidental
misuse but do not remove that operating-system-level race.
"""

from __future__ import annotations

import codecs
import errno
import hashlib
import os
import stat
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Union

PathLike = Union[str, os.PathLike[str]]


class ConcurrentModificationError(RuntimeError):
    """Raised when a file no longer matches the snapshot being saved."""


@dataclass(frozen=True, slots=True)
class TextFileSnapshot:
    """Decoded text and filesystem details captured from one regular file."""

    path: Path
    text: str
    raw_hash: str
    has_bom: bool
    mode: int


def _open_regular_file(path: Path) -> int:
    """Open *path* for reading without intentionally following symlinks."""

    try:
        if stat.S_ISLNK(path.lstat().st_mode):
            raise ValueError(f"refusing to access symlink: {path}")
    except FileNotFoundError:
        raise

    flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW

    try:
        descriptor = os.open(path, flags)
    except OSError as error:
        if error.errno == errno.ELOOP:
            raise ValueError(f"refusing to access symlink: {path}") from error
        raise

    if not stat.S_ISREG(os.fstat(descriptor).st_mode):
        os.close(descriptor)
        raise ValueError(f"expected a regular file: {path}")

    return descriptor


def _read_raw_file(path: Path) -> tuple[bytes, int]:
    descriptor = _open_regular_file(path)
    try:
        file_stat = os.fstat(descriptor)
        with os.fdopen(descriptor, "rb", closefd=True) as file:
            raw = file.read()
        descriptor = -1
    finally:
        if descriptor >= 0:
            os.close(descriptor)

    return raw, stat.S_IMODE(file_stat.st_mode)


def load_text_file(path: PathLike) -> TextFileSnapshot:
    """Load a regular UTF-8 file without newline conversion.

    A leading UTF-8 BOM is represented by ``has_bom`` rather than included in
    ``text``. Invalid UTF-8, symlinks, and non-regular files are rejected.
    """

    resolved_path = Path(path)
    raw, mode = _read_raw_file(resolved_path)
    has_bom = raw.startswith(codecs.BOM_UTF8)
    payload = raw[len(codecs.BOM_UTF8) :] if has_bom else raw
    text = payload.decode("utf-8", errors="strict")

    return TextFileSnapshot(
        path=resolved_path,
        text=text,
        raw_hash=hashlib.sha256(raw).hexdigest(),
        has_bom=has_bom,
        mode=mode,
    )


def _fsync_file(file_descriptor: int) -> None:
    """Sync file contents, tolerating filesystems that do not support it."""

    try:
        os.fsync(file_descriptor)
    except OSError as error:
        unsupported = {errno.EINVAL, errno.EROFS}
        if hasattr(errno, "ENOTSUP"):
            unsupported.add(errno.ENOTSUP)
        if error.errno not in unsupported:
            raise


def _fsync_directory(directory: Path) -> None:
    flags = os.O_RDONLY
    if hasattr(os, "O_DIRECTORY"):
        flags |= os.O_DIRECTORY

    unsupported = {errno.EINVAL, errno.EROFS}
    if hasattr(errno, "ENOTSUP"):
        unsupported.add(errno.ENOTSUP)

    try:
        descriptor = os.open(directory, flags)
    except OSError as error:
        if error.errno in unsupported:
            return
        raise

    try:
        _fsync_file(descriptor)
    finally:
        os.close(descriptor)


def save_text_file(snapshot: TextFileSnapshot, text: str) -> TextFileSnapshot:
    """Atomically save ``text`` if the source still matches ``snapshot``.

    The replacement is prepared in the source directory, retains the original
    BOM and mode, and is removed after every failure that occurs before a
    successful replacement. No Git command or staging operation is performed.

    A residual TOCTOU window exists between the final raw-byte comparison and
    ``os.replace`` because portable APIs cannot combine them atomically.
    """

    if not isinstance(text, str):
        raise TypeError("text must be a str")

    path = snapshot.path
    encoded = text.encode("utf-8")
    if snapshot.has_bom:
        encoded = codecs.BOM_UTF8 + encoded

    temporary_path: Path | None = None
    replaced = False
    try:
        descriptor, temporary_name = tempfile.mkstemp(
            prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
        )
        temporary_path = Path(temporary_name)

        try:
            with os.fdopen(descriptor, "wb", closefd=True) as temporary_file:
                temporary_file.write(encoded)
                temporary_file.flush()
                os.fchmod(temporary_file.fileno(), snapshot.mode)
                _fsync_file(temporary_file.fileno())
        except BaseException:
            try:
                os.close(descriptor)
            except OSError:
                pass
            raise

        current_raw, _current_mode = _read_raw_file(path)
        if hashlib.sha256(current_raw).hexdigest() != snapshot.raw_hash:
            raise ConcurrentModificationError(
                f"file changed after snapshot was loaded: {path}"
            )

        os.replace(temporary_path, path)
        replaced = True
        _fsync_directory(path.parent)
    finally:
        if temporary_path is not None and not replaced:
            try:
                temporary_path.unlink()
            except FileNotFoundError:
                pass

    return load_text_file(path)
