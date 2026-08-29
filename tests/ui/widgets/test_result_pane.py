from textual.app import ComposeResult
from textual.containers import VerticalScroll

from gconflict.ui.tokens import TokenApp
from gconflict.ui.widgets.result_pane import ResultPane


class Harness(TokenApp):
    def compose(self) -> ComposeResult:
        yield ResultPane()


async def test_result_pane_numbers_lines_and_warns_it_is_unsaved() -> None:
    async with Harness().run_test() as pilot:
        pane = pilot.app.query_one(ResultPane)
        pane.show("def status do\n  user.status\nend\n", saved=False, first_line=111)
        await pilot.pause()
        assert pane.header_text == "RESULT  lo que se escribira en el archivo    sin guardar "
        assert pane.body_text == "111 def status do\n112   user.status\n113 end"


async def test_result_pane_reports_a_saved_file() -> None:
    async with Harness().run_test() as pilot:
        pane = pilot.app.query_one(ResultPane)
        pane.show("a\n", saved=True)
        await pilot.pause()
        assert pane.header_text == "RESULT  lo que se escribira en el archivo    guardado "


async def test_result_pane_keeps_all_lines_for_scrolling() -> None:
    async with Harness().run_test() as pilot:
        pane = pilot.app.query_one(ResultPane)
        pane.show("".join(f"line {n}\n" for n in range(1, 11)), saved=False, max_lines=3)
        await pilot.pause()
        body = pane.query_one("#result-body", VerticalScroll)
        assert pane.styles.max_height.value == 12
        assert body.max_scroll_y > 0
        body.focus()
        assert pane.app.focused is body
        body.scroll_y = 1
        assert body.scroll_y == 1
        assert pane.body_text == "\n".join(f"{n} line {n}" for n in range(1, 11))
        assert "... 7 lineas mas" not in pane.body_text


async def test_result_pane_handles_an_empty_result() -> None:
    async with Harness().run_test() as pilot:
        pane = pilot.app.query_one(ResultPane)
        pane.show("", saved=False)
        await pilot.pause()
        assert pane.body_text == "(archivo vacio)"


async def test_clear_empties_the_pane() -> None:
    async with Harness().run_test() as pilot:
        pane = pilot.app.query_one(ResultPane)
        pane.show("a\n", saved=False)
        pane.clear()
        await pilot.pause()
        assert pane.header_text == ""
        assert pane.body_text == ""


async def test_clear_with_unsaved_reason_keeps_the_result_status() -> None:
    async with Harness().run_test() as pilot:
        pane = pilot.app.query_one(ResultPane)
        pane.show("a\n", saved=True)
        pane.clear("sin guardar")
        await pilot.pause()
        assert pane.header_text == "RESULT  lo que se escribira en el archivo    sin guardar "
        assert pane.body_text == ""
