"""Repository state the interface needs to label the two sides of a conflict."""

from dataclasses import dataclass
from pathlib import Path

from gconflict.git.operation import GitOperation


def side_labels(
    operation: GitOperation, branch: str | None, incoming: str | None
) -> tuple[str, str]:
    """Describe the CURRENT and INCOMING sides for the operation in progress."""
    ours = f"ours - {branch}" if branch else "ours - detached HEAD"

    if operation is GitOperation.REBASE:
        # During a rebase "ours" is the base being replayed onto, not the user's branch.
        return "rebased base", "commit being applied"

    if operation is GitOperation.CHERRY_PICK:
        theirs = f"picked commit - {incoming}" if incoming else "picked commit"
    elif operation is GitOperation.REVERT:
        theirs = f"reverted commit - {incoming}" if incoming else "reverted commit"
    else:
        theirs = f"theirs - {incoming}" if incoming else "theirs"

    return ours, theirs


@dataclass(frozen=True)
class RepositoryContext:
    """Everything the header and the conflict panes need about the repository."""

    root: Path
    name: str
    branch: str | None
    operation: GitOperation
    current_label: str
    incoming_label: str
