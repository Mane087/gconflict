from textual.app import ComposeResult

from gconflict.ui.tokens import TokenApp
from gconflict.ui.widgets.action_bar import Action, ActionBar


class Harness(TokenApp):
    def compose(self) -> ComposeResult:
        yield ActionBar()


async def test_action_bar_groups_actions_by_scope() -> None:
    async with Harness().run_test() as pilot:
        bar = pilot.app.query_one(ActionBar)
        bar.set_actions(
            [
                Action("c", "Current", "CONFLICT", active=True),
                Action("i", "Incoming", "CONFLICT"),
                Action("s", "Save", "FILE", enabled=False, reason="faltan 1 de 4 conflictos"),
                Action("q", "Salir", "REPO"),
            ]
        )
        await pilot.pause()
        assert bar.rendered_text == (
            "CONFLICT   c  Current    i  Incoming \n"
            "FILE       s  Save  faltan 1 de 4 conflictos\n"
            "REPO       q  Salir "
        )


async def test_action_bar_omits_a_scope_with_no_actions() -> None:
    async with Harness().run_test() as pilot:
        bar = pilot.app.query_one(ActionBar)
        bar.set_actions([Action("q", "Salir", "REPO")])
        await pilot.pause()
        assert bar.rendered_text == "REPO       q  Salir "


async def test_action_bar_preserves_the_given_order_inside_a_scope() -> None:
    async with Harness().run_test() as pilot:
        bar = pilot.app.query_one(ActionBar)
        bar.set_actions(
            [
                Action("b", "Both C-I", "CONFLICT"),
                Action("c", "Current", "CONFLICT"),
            ]
        )
        await pilot.pause()
        assert bar.rendered_text == "CONFLICT   b  Both C-I    c  Current "


async def test_action_bar_rejects_an_unknown_scope() -> None:
    async with Harness().run_test() as pilot:
        bar = pilot.app.query_one(ActionBar)
        try:
            bar.set_actions([Action("x", "Nope", "BRANCH")])
        except ValueError as error:
            assert "BRANCH" in str(error)
        else:
            raise AssertionError("set_actions accepted an unknown scope")
