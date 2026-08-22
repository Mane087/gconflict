from pathlib import Path

from textual.app import ComposeResult

from gconflict.models.conflicted_file import ConflictedFile, ConflictType
from gconflict.models.file_progress import FileProgress
from gconflict.ui.tokens import TokenApp
from gconflict.ui.widgets.file_tabs import FileTabs, TabEntry, tab_entries


class Harness(TokenApp):
    def compose(self) -> ComposeResult:
        yield FileTabs()


def test_tab_entries_mark_pending_resolved_and_unsupported() -> None:
    progress = [
        FileProgress(ConflictedFile(Path("lib/user.ex"), ConflictType.CONTENT), 2),
        FileProgress(ConflictedFile(Path("lib/index.ex"), ConflictType.CONTENT), 1),
        FileProgress(ConflictedFile(Path("priv/logo.png"), ConflictType.ADD_ADD), 0),
    ]

    assert tab_entries(progress, {Path("lib/index.ex")}) == [
        TabEntry("user.ex", 2, "*"),
        TabEntry("index.ex", 0, "+"),
        TabEntry("logo.png", 0, "!"),
    ]


async def test_file_tabs_render_glyph_name_and_count() -> None:
    async with Harness().run_test() as pilot:
        tabs = pilot.app.query_one(FileTabs)
        tabs.set_files(
            [TabEntry("user.ex", 2, "*"), TabEntry("index.ex", 0, "+")]
        )
        await pilot.pause()
        assert tabs.labels == ["* user.ex 2", "+ index.ex"]


async def test_file_tabs_map_an_activated_tab_back_to_its_entry() -> None:
    async with Harness().run_test() as pilot:
        tabs = pilot.app.query_one(FileTabs)
        entries = [TabEntry("user.ex", 2, "*"), TabEntry("index.ex", 0, "+")]
        tabs.set_files(entries)
        await pilot.pause()
        assert tabs.entry_for(tabs.tab_ids[1]) == entries[1]


async def test_setting_files_twice_replaces_the_previous_tabs() -> None:
    async with Harness().run_test() as pilot:
        tabs = pilot.app.query_one(FileTabs)
        tabs.set_files([TabEntry("user.ex", 2, "*")])
        await pilot.pause()
        tabs.set_files([TabEntry("runtime.exs", 1, "o")])
        await pilot.pause()
        assert tabs.labels == ["o runtime.exs 1"]
