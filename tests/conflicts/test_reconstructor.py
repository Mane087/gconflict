import pytest

from gconflict.conflicts import reconstruct_text
from gconflict.models.conflict import Conflict


def conflict(start: int, end: int) -> Conflict:
    return Conflict(0, [], [], None, start, end)


def test_preserves_text_outside_conflict():
    text = "before\n<<<<<<<\nold\n=======\nnew\n>>>>>>>\nafter\n"
    assert reconstruct_text(text, [conflict(2, 6)], [["resolved\n"]]) == "before\nresolved\nafter\n"


def test_reconstructs_multiple_blocks():
    text = "a\n<<<<<<<\nx\n=======\ny\n>>>>>>>\nb\n<<<<<<<\np\n=======\nq\n>>>>>>>\nc"
    assert reconstruct_text(text, [conflict(2, 6), conflict(8, 12)], [["one\n"], ["two\n"]]) == "a\none\nb\ntwo\nc"


def test_supports_empty_replacement_and_mixed_newlines():
    text = "a\r\n<<<<<<<\r\nold\r\n=======\nnew\n>>>>>>>\r\nz"
    assert reconstruct_text(text, [conflict(2, 6)], [[]]) == "a\r\nz"


def test_supports_eof_without_final_newline():
    text = "a\n<<<<<<<\nold\n=======\nnew\n>>>>>>>"
    assert reconstruct_text(text, [conflict(2, 6)], [["done"]]) == "a\ndone"


@pytest.mark.parametrize("start, end", [(0, 1), (2, 8), (3, 2)])
def test_rejects_invalid_ranges(start, end):
    text = "a\nb\nc\n"
    with pytest.raises(ValueError):
        reconstruct_text(text, [conflict(start, end)], [[]])


def test_rejects_overlapping_ranges():
    text = "a\nb\nc\nd\n"
    with pytest.raises(ValueError):
        reconstruct_text(text, [conflict(1, 2), conflict(2, 3)], [[], []])
