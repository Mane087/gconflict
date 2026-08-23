from textual.app import ComposeResult

from gconflict.ui.tokens import TokenApp

from gconflict.ui.widgets.status_line import StatusKind, StatusLine


class Harness(TokenApp):
    def compose(self) -> ComposeResult:
        yield StatusLine()


async def test_status_line_starts_empty() -> None:
    async with Harness().run_test() as pilot:
        line = pilot.app.query_one(StatusLine)
        assert line.rendered_text == ""


async def test_blocked_status_shows_glyph_title_and_detail() -> None:
    async with Harness().run_test() as pilot:
        line = pilot.app.query_one(StatusLine)
        line.show(
            StatusKind.BLOCKED,
            "No puedes guardar todavia",
            "el conflicto 4 de 4 sigue sin eleccion",
        )
        await pilot.pause()
        assert line.rendered_text == (
            "⚠ No puedes guardar todavia\n  el conflicto 4 de 4 sigue sin eleccion"
        )
        assert line.has_class("-blocked")


async def test_success_status_replaces_the_previous_one() -> None:
    async with Harness().run_test() as pilot:
        line = pilot.app.query_one(StatusLine)
        line.show(StatusKind.BLOCKED, "Bloqueado")
        line.show(StatusKind.SUCCESS, "Guardado - user.ex", "4 conflictos resueltos")
        await pilot.pause()
        assert line.rendered_text == "✓ Guardado - user.ex\n  4 conflictos resueltos"
        assert line.has_class("-success")
        assert not line.has_class("-blocked")


async def test_clear_removes_text_and_variant() -> None:
    async with Harness().run_test() as pilot:
        line = pilot.app.query_one(StatusLine)
        line.show(StatusKind.WARNING, "Ojo")
        line.clear()
        await pilot.pause()
        assert line.rendered_text == ""
        assert not line.has_class("-warning")
