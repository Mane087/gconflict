"""Where the user is inside the selected file's conflicts."""

from collections.abc import Sequence

from rich.text import Text
from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.widgets import Static

from gconflict.models.resolution import Resolution
from gconflict.ui import glyphs

HINT = "[←] [→] navegar conflictos"


class ConflictRail(Horizontal):
    """Show the active conflict, the state of every conflict, and the location."""

    DEFAULT_CSS = """
    ConflictRail {
        height: 1;
        padding: 0 2;
        background: $surface-1;
    }
    ConflictRail > #rail-left {
        width: 1fr;
    }
    ConflictRail > #rail-right {
        width: auto;
        color: $text-4;
    }
    """

    def __init__(self) -> None:
        super().__init__()
        self._left = ""
        self._right = ""

    def compose(self) -> ComposeResult:
        yield Static("", id="rail-left")
        yield Static("", id="rail-right")

    @property
    def rendered_text(self) -> str:
        """Return the plain text currently displayed, left then right."""
        if not self._left:
            return ""
        return f"{self._left}   {self._right}"

    def show(
        self,
        active: int,
        resolutions: Sequence[Resolution | None],
        location: str,
    ) -> None:
        """Render the counter, one dot per conflict, and the file location."""
        total = len(resolutions)
        text = Text()
        text.append(f"Conflict {active + 1} / {total}", style="#d6dae3")
        text.append("  ")
        for position, resolution in enumerate(resolutions):
            if position == active:
                text.append(glyphs.RAIL_ACTIVE, style="#e8a44c")
            elif resolution is not None:
                text.append(glyphs.RAIL_RESOLVED, style="#6fbf73")
            else:
                text.append(glyphs.RAIL_PENDING, style="#4d5462")
        text.append(f"  {location}", style="#79808f")

        self._left = text.plain
        self._right = HINT
        self.query_one("#rail-left", Static).update(text)
        self.query_one("#rail-right", Static).update(Text(HINT, style="#4d5462"))

    def clear(self) -> None:
        """Empty the rail."""
        self._left = ""
        self._right = ""
        self.query_one("#rail-left", Static).update("")
        self.query_one("#rail-right", Static).update("")
