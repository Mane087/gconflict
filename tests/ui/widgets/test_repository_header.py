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


async def test_header_shows_repository_operation_and_branch() -> None:
    async with Harness().run_test() as pilot:
        header = pilot.app.query_one(RepositoryHeader)
        header.set_context(context(GitOperation.MERGE, "feature/user-status"))
        await pilot.pause()
        assert header.rendered_text == "gconflict / lynxweb   MERGE   feature/user-status <- main"


async def test_header_names_a_detached_head() -> None:
    async with Harness().run_test() as pilot:
        header = pilot.app.query_one(RepositoryHeader)
        header.set_context(context(GitOperation.REBASE, None))
        await pilot.pause()
        assert header.rendered_text == "gconflict / lynxweb   REBASE   detached HEAD <- main"


async def test_header_omits_the_arrow_without_an_incoming_reference() -> None:
    async with Harness().run_test() as pilot:
        header = pilot.app.query_one(RepositoryHeader)
        header.set_context(context(GitOperation.NONE, "feature/x", None))
        await pilot.pause()
        assert header.rendered_text == "gconflict / lynxweb   NONE   feature/x"
