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
        assert panes.current_header == "◆ CURRENT  |  rebased base"
        assert panes.incoming_header == "◇ INCOMING  |  commit being applied"


async def test_choosing_current_marks_only_that_pane() -> None:
    async with Harness().run_test() as pilot:
        panes = pilot.app.query_one(ConflictPanes)
        panes.show(make_conflict(), Resolution.CURRENT, "ours", "theirs")
        await pilot.pause()
        assert panes.current_header == "◆ CURRENT  |  ours   ELEGIDO "
        assert panes.incoming_header == "◇ INCOMING  |  theirs"


async def test_choosing_both_marks_the_two_panes() -> None:
    async with Harness().run_test() as pilot:
        panes = pilot.app.query_one(ConflictPanes)
        panes.show(make_conflict(), Resolution.BOTH_INCOMING_FIRST, "ours", "theirs")
        await pilot.pause()
        assert panes.current_header == "◆ CURRENT  |  ours   ELEGIDO "
        assert panes.incoming_header == "◇ INCOMING  |  theirs   ELEGIDO "


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


async def test_panes_show_the_surrounding_file_context_dimmed() -> None:
    async with Harness().run_test() as pilot:
        panes = pilot.app.query_one(ConflictPanes)
        panes.show(
            make_conflict(),
            None,
            "ours",
            "theirs",
            before=["  def status(user):\n"],
            after=["  end\n"],
        )
        await pilot.pause()
        # start_line=111 and end_line=116 are the marker lines themselves, so
        # the context keeps its real file numbering around them.
        assert panes.current_text == (
            "110   def status(user):\n"
            "112     user.status\n"
            "113     |> normalize()\n"
            "117   end"
        )
        assert panes.incoming_text == (
            "110   def status(user):\n"
            "112     user.account.status\n"
            "117   end"
        )
