from textual.app import ComposeResult

from gconflict.models.resolution import Resolution
from gconflict.ui.tokens import TokenApp
from gconflict.ui.widgets.conflict_rail import ConflictRail


class Harness(TokenApp):
    def compose(self) -> ComposeResult:
        yield ConflictRail()


async def test_rail_marks_active_resolved_and_pending() -> None:
    async with Harness().run_test() as pilot:
        rail = pilot.app.query_one(ConflictRail)
        rail.show(1, [Resolution.CURRENT, None, None, Resolution.INCOMING], "user.ex:112")
        await pilot.pause()
        assert rail.rendered_text == "Conflict 2 / 4  ●◉○●  user.ex:112   [←] [→] navegar conflictos"


async def test_rail_handles_a_single_conflict() -> None:
    async with Harness().run_test() as pilot:
        rail = pilot.app.query_one(ConflictRail)
        rail.show(0, [None], "runtime.exs:41")
        await pilot.pause()
        assert rail.rendered_text == "Conflict 1 / 1  ◉  runtime.exs:41   [←] [→] navegar conflictos"


async def test_clear_empties_the_rail() -> None:
    async with Harness().run_test() as pilot:
        rail = pilot.app.query_one(ConflictRail)
        rail.show(0, [None], "a.txt:1")
        rail.clear()
        await pilot.pause()
        assert rail.rendered_text == ""
