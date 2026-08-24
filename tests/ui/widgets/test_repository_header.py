from pathlib import Path

from textual.app import ComposeResult

from gconflict.git.operation import GitOperation
from gconflict.models.repository_context import RepositoryContext
from gconflict.ui.tokens import TokenApp
from gconflict.ui.widgets.repository_header import RepositoryHeader


class Harness(TokenApp):
    def compose(self) -> ComposeResult:
        yield RepositoryHeader()


def context(
    operation: GitOperation, branch: str | None, incoming: str | None = "main"
) -> RepositoryContext:
    return RepositoryContext(
        root=Path("/work/lynxweb"),
        name="lynxweb",
        branch=branch,
        incoming_ref=incoming,
        operation=operation,
        current_label="ours",
        incoming_label="theirs",
    )


async def test_header_splits_identity_from_the_operation() -> None:
    async with Harness().run_test() as pilot:
        header = pilot.app.query_one(RepositoryHeader)
        header.set_context(context(GitOperation.MERGE, "feature/user-status"))
        await pilot.pause()
        assert header.left_text == "\u2387  gconflict  /  lynxweb"
        assert header.right_text == " MERGE    feature/user-status  \u2190  main"


async def test_header_names_a_detached_head() -> None:
    async with Harness().run_test() as pilot:
        header = pilot.app.query_one(RepositoryHeader)
        header.set_context(context(GitOperation.REBASE, None))
        await pilot.pause()
        assert header.right_text == " REBASE    detached HEAD  \u2190  main"


async def test_header_omits_the_arrow_without_an_incoming_reference() -> None:
    async with Harness().run_test() as pilot:
        header = pilot.app.query_one(RepositoryHeader)
        header.set_context(context(GitOperation.NONE, "feature/x", None))
        await pilot.pause()
        assert header.right_text == " NONE    feature/x"


async def test_header_reserves_a_row_above_the_text() -> None:
    async with Harness().run_test() as pilot:
        header = pilot.app.query_one(RepositoryHeader)
        header.set_context(context(GitOperation.MERGE, "feature/x"))
        await pilot.pause()
        # One padding row, one content row, one border row.
        assert header.region.height == 3
        assert header.query_one("#header-left").content_size.height == 1
