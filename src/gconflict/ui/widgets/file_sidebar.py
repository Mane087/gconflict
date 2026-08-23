"""The conflicted-file list and the global progress block."""

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from rich.text import Text
from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widgets import Label, ListItem, ListView, Static

from gconflict.ui import glyphs

_GLYPH_STYLES = {
    glyphs.PENDING: "#e8a44c",
    glyphs.RESOLVED: "#6fbf73",
    glyphs.UNTOUCHED: "#4d5462",
    glyphs.UNSUPPORTED: "#d9645f",
}


@dataclass(frozen=True)
class SidebarEntry:
    """One row of the file list."""

    path: Path
    glyph: str
    note: str


class FileSidebar(Vertical):
    """List the conflicted files and summarise overall progress."""

    DEFAULT_CSS = """
    FileSidebar {
        width: 32;
        background: $surface-1;
        border-right: solid $line;
    }
    FileSidebar > #sidebar-title {
        height: 1;
        padding: 0 1;
        color: $text-4;
        text-style: bold;
    }
    FileSidebar > ListView {
        height: 1fr;
        background: $surface-1;
    }
    FileSidebar > #sidebar-progress {
        height: auto;
        padding: 1;
        border-top: solid $line;
    }
    """

    def __init__(self) -> None:
        super().__init__()
        self._rows: list[str] = []
        self._progress_text = ""
        self._entries: dict[str, SidebarEntry] = {}
        self._shown: list[SidebarEntry] = []
        self._generation = 0

    def compose(self) -> ComposeResult:
        yield Static("CONFLICTED FILES", id="sidebar-title")
        yield ListView()
        yield Static("", id="sidebar-progress")

    @property
    def rows(self) -> list[str]:
        """Return the plain text of every file row, in order."""
        return list(self._rows)

    @property
    def progress_text(self) -> str:
        """Return the plain text of the progress block."""
        return self._progress_text

    @property
    def item_ids(self) -> list[str]:
        """Return the id of every row currently owned by this sidebar."""
        return [f"row-{self._generation}-{position}" for position in range(len(self._shown))]

    def entry_for(self, item_id: str | None) -> SidebarEntry | None:
        """Return the entry behind a row, or None if the row is stale."""
        if item_id is None:
            return None
        return self._entries.get(item_id)

    def set_entries(
        self, entries: Sequence[SidebarEntry], selected: int | None
    ) -> None:
        """Replace the file list and move the highlight."""
        listing = self.query_one(ListView)
        if list(entries) == self._shown:
            # Rebuilding on every refresh would churn the list and reset the highlight.
            listing.index = selected
            return

        # ListView.clear() removes deferred, so ids must not collide across calls
        # and stale rows must stop resolving to an entry.
        listing.clear()
        self._generation += 1
        self._entries = {}
        self._shown = list(entries)
        self._rows = []
        for position, entry in enumerate(entries):
            text = self._row(entry)
            self._rows.append(text.plain)
            item_id = f"row-{self._generation}-{position}"
            self._entries[item_id] = entry
            listing.append(ListItem(Label(text), id=item_id))
        listing.index = selected

    def set_progress(
        self,
        conflicts_resolved: int,
        conflicts_total: int,
        files_resolved: int,
        files_total: int,
        staged: int = 0,
    ) -> None:
        """Replace the progress block."""
        text = Text()
        text.append("PROGRESO ", style="#4d5462")
        text.append(f"{conflicts_resolved} / {conflicts_total}", style="#a4abba")
        text.append("\narchivos ", style="#4d5462")
        text.append(f"{files_resolved} / {files_total}", style="#a4abba")
        text.append("\nstaged   ", style="#4d5462")
        text.append(str(staged), style="#6fbf73" if staged else "#4d5462")
        self._progress_text = text.plain
        self.query_one("#sidebar-progress", Static).update(text)

    @staticmethod
    def _row(entry: SidebarEntry) -> Text:
        """Render one file row: glyph, basename, directory, note."""
        directory = entry.path.parent
        shown = "./" if directory == Path(".") else f"{directory}/"
        style = _GLYPH_STYLES.get(entry.glyph, "#4d5462")

        text = Text()
        text.append(entry.glyph, style=style)
        text.append(f" {entry.path.name}", style="#d6dae3")
        text.append(f"\n  {shown}", style="#4d5462")
        text.append(f"\n  {entry.note}", style=style)
        return text
