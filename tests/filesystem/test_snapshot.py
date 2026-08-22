import codecs
import errno
import hashlib
import os
import stat

import pytest

from gconflict.filesystem import snapshot as snapshot_module
from gconflict.filesystem.snapshot import (
    ConcurrentModificationError,
    load_text_file,
    save_text_file,
)


@pytest.mark.parametrize(
    ("raw", "expected_text", "has_bom"),
    [
        ("alpha\r\nbeta\n".encode(), "alpha\r\nbeta\n", False),
        (codecs.BOM_UTF8 + "á\rúltima".encode(), "á\rúltima", True),
    ],
)
def test_load_preserves_encoding_newlines_hash_and_mode(
    tmp_path, raw, expected_text, has_bom
):
    path = tmp_path / "sample.txt"
    path.write_bytes(raw)
    path.chmod(0o754)

    snapshot = load_text_file(path)

    assert snapshot.path == path
    assert snapshot.text == expected_text
    assert snapshot.has_bom is has_bom
    assert snapshot.raw_hash == hashlib.sha256(raw).hexdigest()
    assert snapshot.mode == 0o754


def test_load_rejects_invalid_utf8(tmp_path):
    path = tmp_path / "invalid.txt"
    path.write_bytes(b"valid\xffinvalid")

    with pytest.raises(UnicodeDecodeError):
        load_text_file(path)


def test_load_rejects_symlink(tmp_path):
    target = tmp_path / "target.txt"
    target.write_text("target", encoding="utf-8")
    link = tmp_path / "link.txt"
    link.symlink_to(target)

    with pytest.raises(ValueError, match="symlink"):
        load_text_file(link)


def test_save_preserves_bom_exact_newlines_and_mode(tmp_path):
    path = tmp_path / "sample.txt"
    path.write_bytes(codecs.BOM_UTF8 + b"old\r\ntext\n")
    path.chmod(0o751)
    snapshot = load_text_file(path)

    saved = save_text_file(snapshot, "new\r\ntext\n")

    expected = codecs.BOM_UTF8 + b"new\r\ntext\n"
    assert path.read_bytes() == expected
    assert stat.S_IMODE(path.stat().st_mode) == 0o751
    assert saved.text == "new\r\ntext\n"
    assert saved.raw_hash == hashlib.sha256(expected).hexdigest()


def test_save_applies_mode_before_final_file_fsync(tmp_path, monkeypatch):
    path = tmp_path / "sample.txt"
    path.write_bytes(b"old")
    snapshot = load_text_file(path)
    events = []
    original_fchmod = os.fchmod
    original_fsync = os.fsync

    def recording_fchmod(descriptor, mode):
        events.append(("fchmod", descriptor))
        return original_fchmod(descriptor, mode)

    def recording_fsync(descriptor):
        events.append(("fsync", descriptor))
        return original_fsync(descriptor)

    monkeypatch.setattr(os, "fchmod", recording_fchmod)
    monkeypatch.setattr(os, "fsync", recording_fsync)

    save_text_file(snapshot, "new")

    assert [event for event, _descriptor in events[:2]] == ["fchmod", "fsync"]
    assert events[0][1] == events[1][1]


def test_save_rejects_concurrent_modification_without_overwriting(tmp_path):
    path = tmp_path / "sample.txt"
    path.write_bytes(b"original")
    snapshot = load_text_file(path)
    path.write_bytes(b"concurrent")

    with pytest.raises(ConcurrentModificationError):
        save_text_file(snapshot, "replacement")

    assert path.read_bytes() == b"concurrent"
    assert list(tmp_path.glob(".sample.txt.*.tmp")) == []


def test_save_cleans_temp_and_leaves_original_on_pre_replace_failure(
    tmp_path, monkeypatch
):
    path = tmp_path / "sample.txt"
    path.write_bytes(b"original")
    path.chmod(0o744)
    snapshot = load_text_file(path)

    def fail_replace(source, destination):
        assert os.fspath(destination) == os.fspath(path)
        raise OSError("injected replacement failure")

    monkeypatch.setattr(os, "replace", fail_replace)

    with pytest.raises(OSError, match="injected replacement failure"):
        save_text_file(snapshot, "replacement")

    assert path.read_bytes() == b"original"
    assert stat.S_IMODE(path.stat().st_mode) == 0o744
    assert list(tmp_path.glob(".sample.txt.*.tmp")) == []


@pytest.mark.parametrize(
    ("error_number", "should_raise"),
    [(errno.EINVAL, False), (errno.EIO, True)],
)
def test_directory_sync_selectively_handles_open_errors(
    tmp_path, monkeypatch, error_number, should_raise
):
    def fail_open(_path, _flags):
        raise OSError(error_number, os.strerror(error_number))

    monkeypatch.setattr(os, "open", fail_open)

    if should_raise:
        with pytest.raises(OSError) as raised:
            snapshot_module._fsync_directory(tmp_path)
        assert raised.value.errno == error_number
    else:
        snapshot_module._fsync_directory(tmp_path)


@pytest.mark.parametrize(
    ("error_number", "should_raise"),
    [(errno.EINVAL, False), (errno.EIO, True)],
)
def test_directory_sync_selectively_handles_fsync_errors(
    tmp_path, monkeypatch, error_number, should_raise
):
    flags = os.O_RDONLY
    if hasattr(os, "O_DIRECTORY"):
        flags |= os.O_DIRECTORY
    descriptor = os.open(tmp_path, flags)

    monkeypatch.setattr(os, "open", lambda _path, _flags: descriptor)

    def fail_fsync(_descriptor):
        raise OSError(error_number, os.strerror(error_number))

    monkeypatch.setattr(os, "fsync", fail_fsync)

    if should_raise:
        with pytest.raises(OSError) as raised:
            snapshot_module._fsync_directory(tmp_path)
        assert raised.value.errno == error_number
    else:
        snapshot_module._fsync_directory(tmp_path)
