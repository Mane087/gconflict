"""The conflicted-file list and the global progress block."""

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from rich.text import Text
from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widgets import Label, ListItem, ListView, Static

_GLYPH_STYLES = {"*": "#e8a44c", "+": "#6fbf73", "o": "#4d5462", "!": "#d9645f"}


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

    def compose(self) -> ComposeResult:
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

    def set_entries(
        self, entries: Sequence[SidebarEntry], selected: int | None
    ) -> None:
        """Replace the file list and move the highlight."""
        listing = self.query_one(ListView)
        listing.clear()
        self._rows = []
        for entry in entries:
            text = self._row(entry)
            self._rows.append(text.plain)
            listing.append(ListItem(Label(text)))
        listing.index = selected

    def set_progress(
        self,
        conflicts_resolved: int,
        conflicts_total: int,
        files_resolved: int,
        files_total: int,
    ) -> None:
        """Replace the progress block."""
        text = Text()
        text.append("PROGRESO ", style="#4d5462")
        text.append(f"{conflicts_resolved} / {conflicts_total}", style="#a4abba")
        text.append("\narchivos ", style="#4d5462")
        text.append(f"{files_resolved} / {files_total}", style="#a4abba")
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
