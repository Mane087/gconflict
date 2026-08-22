"""Where the user is inside the selected file's conflicts."""

from collections.abc import Sequence

from rich.text import Text
from textual.widgets import Static

from gconflict.models.resolution import Resolution


class ConflictRail(Static):
    """Show the active conflict, the state of every conflict, and the location."""

    DEFAULT_CSS = """
    ConflictRail {
        height: 1;
        padding: 0 1;
        background: $surface-1;
    }
    """

    def __init__(self) -> None:
        super().__init__("")
        self._rendered_text = ""

    @property
    def rendered_text(self) -> str:
        """Return the plain text currently displayed."""
        return self._rendered_text

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
                text.append("O", style="#e8a44c")
            elif resolution is not None:
                text.append("*", style="#6fbf73")
            else:
                text.append(".", style="#4d5462")
        text.append(f"  {location}", style="#79808f")

        self._rendered_text = text.plain
        self.update(text)

    def clear(self) -> None:
        """Empty the rail."""
        self._rendered_text = ""
        self.update("")
