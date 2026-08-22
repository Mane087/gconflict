from pathlib import Path

from textual.app import ComposeResult

from gconflict.ui.tokens import TokenApp
from gconflict.ui.widgets.file_sidebar import FileSidebar, SidebarEntry


class Harness(TokenApp):
    def compose(self) -> ComposeResult:
        yield FileSidebar()


async def test_sidebar_lists_directory_name_and_note() -> None:
    async with Harness().run_test() as pilot:
        sidebar = pilot.app.query_one(FileSidebar)
        sidebar.set_entries(
            [
                SidebarEntry(Path("lib/lynxweb/accounts/user.ex"), "*", "2 sin resolver"),
                SidebarEntry(Path("config/runtime.exs"), "o", "1 sin resolver"),
            ],
            selected=0,
        )
        await pilot.pause()
        assert sidebar.rows == [
            "* user.ex\n  lib/lynxweb/accounts/\n  2 sin resolver",
            "o runtime.exs\n  config/\n  1 sin resolver",
        ]


async def test_sidebar_marks_a_file_at_the_repository_root() -> None:
    async with Harness().run_test() as pilot:
        sidebar = pilot.app.query_one(FileSidebar)
        sidebar.set_entries([SidebarEntry(Path("README.md"), "*", "1 sin resolver")], selected=0)
        await pilot.pause()
        assert sidebar.rows == ["* README.md\n  ./\n  1 sin resolver"]


async def test_sidebar_renders_the_progress_block() -> None:
    async with Harness().run_test() as pilot:
        sidebar = pilot.app.query_one(FileSidebar)
        sidebar.set_progress(
            conflicts_resolved=3, conflicts_total=8, files_resolved=1, files_total=4
        )
        await pilot.pause()
        assert sidebar.progress_text == "PROGRESO 3 / 8\narchivos 1 / 4"


async def test_sidebar_survives_an_empty_file_list() -> None:
    async with Harness().run_test() as pilot:
        sidebar = pilot.app.query_one(FileSidebar)
        sidebar.set_entries([], selected=None)
        await pilot.pause()
        assert sidebar.rows == []
