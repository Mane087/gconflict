from pathlib import Path

from textual.app import ComposeResult
from textual.widgets import Static

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
                SidebarEntry(Path("lib/lynxweb/accounts/user.ex"), "●", "2 sin resolver"),
                SidebarEntry(Path("config/runtime.exs"), "○", "1 sin resolver"),
            ],
            selected=0,
        )
        await pilot.pause()
        assert sidebar.rows == [
            "● user.ex\n  lib/lynxweb/accounts/\n  2 sin resolver",
            "○ runtime.exs\n  config/\n  1 sin resolver",
        ]


async def test_sidebar_marks_a_file_at_the_repository_root() -> None:
    async with Harness().run_test() as pilot:
        sidebar = pilot.app.query_one(FileSidebar)
        sidebar.set_entries([SidebarEntry(Path("README.md"), "●", "1 sin resolver")], selected=0)
        await pilot.pause()
        assert sidebar.rows == ["● README.md\n  ./\n  1 sin resolver"]


async def test_progress_keeps_the_label_and_the_bar_in_separate_widgets() -> None:
    async with Harness().run_test() as pilot:
        sidebar = pilot.app.query_one(FileSidebar)
        sidebar.set_progress(
            resolved=3,
            total=8,
            segments=["resolved"] * 3 + ["active"] + ["pending"] * 4,
        )
        await pilot.pause()
        title = sidebar.query_one("#progress-title", Static)
        count = sidebar.query_one("#progress-count", Static)
        bar = sidebar.query_one("#progress-bar", Static)
        # Three widgets, each one row: the counter can never be split off.
        assert title.content_size.height == 1
        assert count.content_size.height == 1
        assert bar.content_size.height == 1
        assert sidebar.progress_counter == "3 / 8"


async def test_progress_blocks_stay_narrow() -> None:
    async with Harness().run_test() as pilot:
        sidebar = pilot.app.query_one(FileSidebar)
        sidebar.set_progress(resolved=0, total=2, segments=["active", "pending"])
        await pilot.pause()
        bar = sidebar.progress_bar
        # Two conflicts must not become two slabs half a sidebar wide.
        assert bar == "███ ███"


async def test_progress_never_wraps_whatever_the_width() -> None:
    async with Harness().run_test(size=(20, 12)) as pilot:
        sidebar = pilot.app.query_one(FileSidebar)
        sidebar.set_progress(resolved=0, total=40, segments=["pending"] * 40)
        await pilot.pause()
        bar_widget = sidebar.query_one("#progress-bar", Static)
        assert " " not in sidebar.progress_bar
        # One row, whatever the count: the bar clips instead of wrapping.
        assert bar_widget.content_size.height == 1


async def test_progress_with_no_conflicts_renders_an_empty_bar() -> None:
    async with Harness().run_test() as pilot:
        sidebar = pilot.app.query_one(FileSidebar)
        sidebar.set_progress(resolved=0, total=0)
        await pilot.pause()
        assert sidebar.progress_bar == ""


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
            SidebarEntry(Path("a.txt"), "●", "1 sin resolver"),
            SidebarEntry(Path("nested/b.txt"), "●", "2 sin resolver"),
        ]
        sidebar.set_entries(entries, selected=0)
        await pilot.pause()
        assert sidebar.entry_for(sidebar.item_ids[1]) == entries[1]


async def test_sidebar_returns_none_for_a_stale_list_item() -> None:
    async with Harness().run_test() as pilot:
        sidebar = pilot.app.query_one(FileSidebar)
        sidebar.set_entries(
            [SidebarEntry(Path("a.txt"), "●", "1"), SidebarEntry(Path("b.txt"), "●", "1")],
            selected=0,
        )
        await pilot.pause()
        stale = sidebar.item_ids[1]
        # ListView.clear() removes deferred, so the old items outlive the call.
        sidebar.set_entries([SidebarEntry(Path("a.txt"), "●", "1")], selected=0)
        assert sidebar.entry_for(stale) is None


async def test_sidebar_does_not_rebuild_when_the_entries_are_unchanged() -> None:
    async with Harness().run_test() as pilot:
        sidebar = pilot.app.query_one(FileSidebar)
        entries = [SidebarEntry(Path("a.txt"), "●", "1 sin resolver")]
        sidebar.set_entries(entries, selected=0)
        await pilot.pause()
        first = list(sidebar.item_ids)
        sidebar.set_entries(list(entries), selected=0)
        await pilot.pause()
        assert sidebar.item_ids == first
