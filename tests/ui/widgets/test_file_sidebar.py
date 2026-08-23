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


async def test_sidebar_maps_a_list_item_back_to_its_entry() -> None:
    async with Harness().run_test() as pilot:
        sidebar = pilot.app.query_one(FileSidebar)
        entries = [
            SidebarEntry(Path("a.txt"), "*", "1 sin resolver"),
            SidebarEntry(Path("nested/b.txt"), "*", "2 sin resolver"),
        ]
        sidebar.set_entries(entries, selected=0)
        await pilot.pause()
        assert sidebar.entry_for(sidebar.item_ids[1]) == entries[1]


async def test_sidebar_returns_none_for_a_stale_list_item() -> None:
    async with Harness().run_test() as pilot:
        sidebar = pilot.app.query_one(FileSidebar)
        sidebar.set_entries(
            [SidebarEntry(Path("a.txt"), "*", "1"), SidebarEntry(Path("b.txt"), "*", "1")],
            selected=0,
        )
        await pilot.pause()
        stale = sidebar.item_ids[1]
        # ListView.clear() removes deferred, so the old items outlive the call.
        sidebar.set_entries([SidebarEntry(Path("a.txt"), "*", "1")], selected=0)
        assert sidebar.entry_for(stale) is None


async def test_sidebar_does_not_rebuild_when_the_entries_are_unchanged() -> None:
    async with Harness().run_test() as pilot:
        sidebar = pilot.app.query_one(FileSidebar)
        entries = [SidebarEntry(Path("a.txt"), "*", "1 sin resolver")]
        sidebar.set_entries(entries, selected=0)
        await pilot.pause()
        first = list(sidebar.item_ids)
        sidebar.set_entries(list(entries), selected=0)
        await pilot.pause()
        assert sidebar.item_ids == first
