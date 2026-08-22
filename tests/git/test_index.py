from pathlib import Path

import pytest

from gconflict.git import GitIndex, GitStage
from gconflict.git.client import GitResult
from gconflict.models.conflicted_file import ConflictType


class StubClient:
    def __init__(self, stdout: str) -> None:
        self.stdout = stdout
        self.calls = []

    def run(self, args, *, cwd=None, check=True):
        self.calls.append((args, cwd, check))
        return GitResult(self.stdout, "", 0)


def test_unmerged_entries_delegates_with_cwd_and_parses_stages_in_order():
    client = StubClient(
        "100644 base 1\tfile.txt\n100644 ours 2\tfile.txt\n100644 theirs 3\tfile.txt\n"
    )
    entries = GitIndex(client).unmerged_entries("repo")

    assert client.calls == [(["ls-files", "-u"], "repo", True)]
    assert [entry.stage for entry in entries] == [GitStage.BASE, GitStage.OURS, GitStage.THEIRS]


def test_unmerged_entries_allows_missing_stages_and_spaces_in_paths():
    client = StubClient("100644 ours 2\tdirectory/file with spaces.txt\n")

    entries = GitIndex(client).unmerged_entries()

    assert entries[0].path == Path("directory/file with spaces.txt")


def test_unmerged_entries_empty_output():
    assert GitIndex(StubClient("")).unmerged_entries() == []


@pytest.mark.parametrize("line", ["malformed", "100644 hash 4\tfile", "100644 hash 1 file"])
def test_unmerged_entries_rejects_malformed_records(line):
    with pytest.raises(ValueError):
        GitIndex(StubClient(line)).unmerged_entries()


@pytest.mark.parametrize(
    ("stages", "expected"),
    [
        ((2, 3), ConflictType.ADD_ADD),
        ((1, 2), ConflictType.MODIFY_DELETE),
        ((1, 3), ConflictType.MODIFY_DELETE),
    ],
)
def test_conflicted_file_descriptors_classifies_stage_combinations(
    tmp_path: Path, stages: tuple[int, ...], expected: ConflictType
) -> None:
    output = "".join(f"100644 hash {stage}\tfile.txt\n" for stage in stages)

    descriptors = GitIndex(StubClient(output)).conflicted_file_descriptors(tmp_path)

    assert descriptors[0].path == Path("file.txt")
    assert descriptors[0].conflict_type is expected


def test_three_stage_conflict_requires_utf8_file_with_standard_markers(
    tmp_path: Path,
) -> None:
    output = "".join(f"100644 hash {stage}\tfile.txt\n" for stage in (1, 2, 3))
    index = GitIndex(StubClient(output))
    path = tmp_path / "file.txt"
    path.write_text("<<<<<<< HEAD\nours\n=======\ntheirs\n>>>>>>> branch\n", encoding="utf-8")
    assert index.conflicted_file_descriptors(tmp_path)[0].conflict_type is ConflictType.CONTENT

    path.write_text("ordinary text\n", encoding="utf-8")
    assert index.conflicted_file_descriptors(tmp_path)[0].conflict_type is ConflictType.OTHER

    path.write_bytes(b"\xff")
    assert index.conflicted_file_descriptors(tmp_path)[0].conflict_type is ConflictType.OTHER
