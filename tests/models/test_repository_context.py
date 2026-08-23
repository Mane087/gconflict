from pathlib import Path

import pytest

from gconflict.git.operation import GitOperation
from gconflict.models.repository_context import RepositoryContext, side_labels


@pytest.mark.parametrize(
    ("operation", "branch", "incoming", "expected"),
    [
        (GitOperation.MERGE, "feature/x", "main", ("ours - feature/x", "theirs - main")),
        (GitOperation.MERGE, None, "main", ("ours - detached HEAD", "theirs - main")),
        (GitOperation.MERGE, "feature/x", None, ("ours - feature/x", "theirs")),
        (
            GitOperation.REBASE,
            "feature/x",
            "feature/x",
            ("rebased base", "commit being applied"),
        ),
        (
            GitOperation.CHERRY_PICK,
            "feature/x",
            "main",
            ("ours - feature/x", "picked commit - main"),
        ),
        (
            GitOperation.REVERT,
            "feature/x",
            "main",
            ("ours - feature/x", "reverted commit - main"),
        ),
        (GitOperation.NONE, "feature/x", None, ("ours - feature/x", "theirs")),
    ],
)
def test_side_labels_depend_on_the_operation(
    operation: GitOperation, branch: str | None, incoming: str | None, expected: tuple[str, str]
) -> None:
    assert side_labels(operation, branch, incoming) == expected


def test_context_names_itself_after_the_repository_root() -> None:
    context = RepositoryContext(
        root=Path("/work/lynxweb"),
        name="lynxweb",
        branch="feature/x",
        incoming_ref="main",
        operation=GitOperation.MERGE,
        current_label="ours - feature/x",
        incoming_label="theirs - main",
    )

    assert context.name == "lynxweb"
    assert context.operation is GitOperation.MERGE
