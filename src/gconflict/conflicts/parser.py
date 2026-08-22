import re

from gconflict.models.conflict import Conflict


_START = re.compile(r"^<<<<<<<")
_SEPARATOR = re.compile(r"^=======")
_END = re.compile(r"^>>>>>>>")
_DIFF3 = re.compile(r"^\|\|\|\|\|\|\|")


def parse_conflicts(text: str) -> list[Conflict]:
    """Parse standard two-way conflict markers using 1-based line numbers."""
    lines = text.splitlines(keepends=True)
    conflicts: list[Conflict] = []
    current_start: int | None = None
    separator: int | None = None
    current: list[str] = []

    for number, line in enumerate(lines, 1):
        content = line.rstrip("\r\n")
        if _DIFF3.match(content):
            raise ValueError("diff3/zdiff3 conflict markers are unsupported")

        if current_start is None:
            if _SEPARATOR.match(content) or _END.match(content):
                raise ValueError("orphan conflict marker")
            if _START.match(content):
                current_start = number
                current = []
            continue

        if separator is None:
            if _START.match(content):
                raise ValueError("nested conflict marker")
            if _END.match(content):
                raise ValueError("conflict is missing separator")
            if _SEPARATOR.match(content):
                separator = number
            else:
                current.append(line)
            continue

        if _START.match(content) or _SEPARATOR.match(content):
            raise ValueError("invalid conflict marker ordering")
        if _END.match(content):
            incoming = lines[separator:number - 1]
            conflicts.append(
                Conflict(
                    index=len(conflicts),
                    current=current,
                    incoming=incoming,
                    base=None,
                    start_line=current_start,
                    end_line=number,
                )
            )
            current_start = None
            separator = None
            current = []
        else:
            # Keep the original line terminator and all whitespace.
            continue

    if current_start is not None:
        if separator is None:
            raise ValueError("conflict is missing separator")
        raise ValueError("conflict is missing closing marker")
    return conflicts
