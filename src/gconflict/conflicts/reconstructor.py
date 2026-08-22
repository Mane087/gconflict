from collections.abc import Sequence

from gconflict.models.conflict import Conflict


def reconstruct_text(
    text: str,
    conflicts: Sequence[Conflict],
    resolutions: Sequence[Sequence[str]],
) -> str:
    """Replace conflict marker ranges with their resolved lines."""
    if len(conflicts) != len(resolutions):
        raise ValueError("conflicts and resolutions must have the same length")

    lines = text.splitlines(keepends=True)
    previous_end = 0
    replacements: list[tuple[int, int, str]] = []
    for conflict, resolution in zip(conflicts, resolutions):
        start, end = conflict.start_line, conflict.end_line
        if start < 1 or end < start or end > len(lines):
            raise ValueError("conflict range is outside the text")
        if start <= previous_end:
            raise ValueError("conflict ranges must be ordered and non-overlapping")
        previous_end = end
        replacements.append((start - 1, end, "".join(resolution)))

    result: list[str] = []
    previous_end = 0
    for start, end, replacement in replacements:
        result.extend(lines[previous_end:start])
        result.append(replacement)
        previous_end = end
    result.extend(lines[previous_end:])
    return "".join(result)
