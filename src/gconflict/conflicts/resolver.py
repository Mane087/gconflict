from gconflict.models.conflict import Conflict
from gconflict.models.resolution import Resolution


def resolve_conflict(
    conflict: Conflict, resolution: Resolution, manual: list[str] | None = None
) -> list[str]:
    if resolution is Resolution.CURRENT:
        return list(conflict.current)
    if resolution is Resolution.INCOMING:
        return list(conflict.incoming)
    if resolution is Resolution.BOTH_CURRENT_FIRST:
        return [*conflict.current, *conflict.incoming]
    if resolution is Resolution.BOTH_INCOMING_FIRST:
        return [*conflict.incoming, *conflict.current]
    if resolution is Resolution.MANUAL:
        if manual is None:
            raise ValueError("manual content is required")
        return list(manual)
    raise ValueError(f"unsupported resolution: {resolution!r}")
