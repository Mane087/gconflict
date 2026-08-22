from textual.app import ComposeResult

from gconflict.models.conflict import Conflict
from gconflict.models.resolution import Resolution
from gconflict.ui.tokens import TokenApp
from gconflict.ui.widgets.conflict_panes import ConflictPanes


class Harness(TokenApp):
    def compose(self) -> ComposeResult:
        yield ConflictPanes()


def make_conflict() -> Conflict:
    return Conflict(
        index=0,
        current=["    user.status\n", "    |> normalize()\n"],
        incoming=["    user.account.status\n"],
        base=None,
        start_line=111,
        end_line=116,
    )


async def test_panes_number_lines_from_the_conflict_start() -> None:
    async with Harness().run_test() as pilot:
        panes = pilot.app.query_one(ConflictPanes)
        panes.show(make_conflict(), None, "ours - feature/x", "theirs - main")
        await pilot.pause()
        assert panes.current_text == (
            "112     user.status\n113     |> normalize()"
        )
        assert panes.incoming_text == "112     user.account.status"


async def test_panes_headers_carry_the_operation_labels() -> None:
    async with Harness().run_test() as pilot:
        panes = pilot.app.query_one(ConflictPanes)
        panes.show(make_conflict(), None, "rebased base", "commit being applied")
        await pilot.pause()
        assert panes.current_header == "* CURRENT  rebased base"
        assert panes.incoming_header == "o INCOMING  commit being applied"


async def test_choosing_current_marks_only_that_pane() -> None:
    async with Harness().run_test() as pilot:
        panes = pilot.app.query_one(ConflictPanes)
        panes.show(make_conflict(), Resolution.CURRENT, "ours", "theirs")
        await pilot.pause()
        assert panes.current_header == "* CURRENT  ours  SELECTED"
        assert panes.incoming_header == "o INCOMING  theirs"


async def test_choosing_both_marks_the_two_panes() -> None:
    async with Harness().run_test() as pilot:
        panes = pilot.app.query_one(ConflictPanes)
        panes.show(make_conflict(), Resolution.BOTH_INCOMING_FIRST, "ours", "theirs")
        await pilot.pause()
        assert panes.current_header == "* CURRENT  ours  SELECTED"
        assert panes.incoming_header == "o INCOMING  theirs  SELECTED"


async def test_clear_empties_both_panes() -> None:
    async with Harness().run_test() as pilot:
        panes = pilot.app.query_one(ConflictPanes)
        panes.show(make_conflict(), None, "ours", "theirs")
        panes.clear()
        await pilot.pause()
        assert panes.current_text == ""
        assert panes.incoming_text == ""
        assert panes.current_header == ""
        assert panes.incoming_header == ""
