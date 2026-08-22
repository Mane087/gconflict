from dataclasses import dataclass


@dataclass
class Conflict:
    index: int
    current: list[str]
    incoming: list[str]
    base: list[str] | None
    start_line: int
    end_line: int
