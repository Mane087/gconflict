import pytest

from gconflict.conflicts.parser import parse_conflicts


def test_parses_and_preserves_multiple_conflicts() -> None:
    text = "before\r\n<<<<<<< ours\r\n a\t\r\n=======\r\n\r\nb\r\n>>>>>>> theirs\r\n<<<<<<< ours\n=======\n>>>>>>> theirs"
    conflicts = parse_conflicts(text)

    assert conflicts[0].index == 0
    assert conflicts[0].current == [" a\t\r\n"]
    assert conflicts[0].incoming == ["\r\n", "b\r\n"]
    assert conflicts[0].start_line == 2
    assert conflicts[0].end_line == 7
    assert conflicts[1].index == 1
    assert conflicts[1].current == conflicts[1].incoming == []


def test_no_markers_returns_empty() -> None:
    assert parse_conflicts("plain text\n") == []


@pytest.mark.parametrize(
    "text",
    [
        "<<<<<<< ours\na\n>>>>>>> theirs\n",
        "<<<<<<< ours\n=======\na\n",
        "=======\na\n>>>>>>> theirs\n",
        "<<<<<<< ours\n=======\n<<<<<<< nested\n>>>>>>> theirs\n",
        "<<<<<<< ours\n||||||| base\n=======\n>>>>>>> theirs\n",
    ],
)
def test_rejects_invalid_markers(text: str) -> None:
    with pytest.raises(ValueError):
        parse_conflicts(text)
