import pytest

from gconflict.conflicts.resolver import resolve_conflict
from gconflict.models.conflict import Conflict
from gconflict.models.resolution import Resolution


def conflict(current=None, incoming=None):
    return Conflict(1, current or [], incoming or [], None, 1, 2)


def test_resolves_all_modes_without_deduplication():
    value = conflict(["same", "current"], ["same", "incoming"])

    assert resolve_conflict(value, Resolution.CURRENT) == ["same", "current"]
    assert resolve_conflict(value, Resolution.INCOMING) == ["same", "incoming"]
    assert resolve_conflict(value, Resolution.BOTH_CURRENT_FIRST) == [
        "same", "current", "same", "incoming"
    ]
    assert resolve_conflict(value, Resolution.BOTH_INCOMING_FIRST) == [
        "same", "incoming", "same", "current"
    ]


def test_preserves_empty_sides_and_manual_content():
    value = conflict([], ["incoming"])
    manual = ["literal", "", "content"]

    assert resolve_conflict(value, Resolution.BOTH_CURRENT_FIRST) == ["incoming"]
    assert resolve_conflict(value, Resolution.MANUAL, manual) == manual


def test_does_not_mutate_inputs():
    current, incoming, manual = ["current"], ["incoming"], ["manual"]
    value = conflict(current, incoming)

    resolve_conflict(value, Resolution.BOTH_CURRENT_FIRST)
    resolve_conflict(value, Resolution.MANUAL, manual)

    assert value.current == current
    assert value.incoming == incoming
    assert manual == ["manual"]


def test_manual_requires_content():
    with pytest.raises(ValueError):
        resolve_conflict(conflict(), Resolution.MANUAL)
