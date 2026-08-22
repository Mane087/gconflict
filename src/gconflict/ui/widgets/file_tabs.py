"""One tab per conflicted file, carrying how many conflicts remain."""

from collections.abc import Container, Sequence
from dataclasses import dataclass
from pathlib import Path

from rich.text import Text
from textual.widgets import Tab, Tabs

from gconflict.models.file_progress import FileProgress

PENDING = "*"
RESOLVED = "+"
UNTOUCHED = "o"
UNSUPPORTED = "!"


@dataclass(frozen=True)
class TabEntry:
    """A file's tab: its basename, its remaining conflicts, and its state."""

    name: str
    remaining: int
    glyph: str


def tab_entries(
    progress: Sequence[FileProgress], resolved_paths: Container[Path]
) -> list[TabEntry]:
    """Turn per-file progress into tab entries, in the order Git reported them."""
    entries: list[TabEntry] = []
    for item in progress:
        if not item.supported:
            entries.append(TabEntry(item.file.path.name, 0, UNSUPPORTED))
        elif item.file.path in resolved_paths:
            entries.append(TabEntry(item.file.path.name, 0, RESOLVED))
        else:
            entries.append(TabEntry(item.file.path.name, item.total, PENDING))
    return entries


class FileTabs(Tabs):
    """Show the conflicted files as tabs."""

    DEFAULT_CSS = """
    FileTabs {
        background: $surface-2;
        border-bottom: solid $line;
    }
    """

    _STYLES = {
        PENDING: "#e8a44c",
        RESOLVED: "#6fbf73",
        UNTOUCHED: "#4d5462",
        UNSUPPORTED: "#d9645f",
    }

    def __init__(self) -> None:
        super().__init__()
        self._entries: dict[str, TabEntry] = {}
        self._generation = 0

    @property
    def labels(self) -> list[str]:
        """Return the plain label of every tab, in order."""
        return [tab.label.plain for tab in self.query(Tab)]

    @property
    def tab_ids(self) -> list[str]:
        """Return the id of every tab, in order."""
        return [str(tab.id) for tab in self.query(Tab)]

    def set_files(self, entries: Sequence[TabEntry]) -> None:
        """Replace every tab with one per given entry."""
        # Tabs.clear() removes deferred, so ids must not collide across calls.
        self.clear()
        self._generation += 1
        self._entries = {}
        for position, entry in enumerate(entries):
            tab_id = f"file-{self._generation}-{position}"
            self._entries[tab_id] = entry
            self.add_tab(Tab(self._label(entry), id=tab_id))

    def entry_for(self, tab_id: str) -> TabEntry:
        """Return the entry behind an activated tab."""
        return self._entries[tab_id]

    def _label(self, entry: TabEntry) -> Text:
        """Render one tab label: glyph, name, and remaining count."""
        style = self._STYLES.get(entry.glyph, "#4d5462")
        label = Text()
        label.append(entry.glyph, style=style)
        label.append(f" {entry.name}", style="#d6dae3")
        if entry.remaining:
            label.append(f" {entry.remaining}", style=style)
        return label
