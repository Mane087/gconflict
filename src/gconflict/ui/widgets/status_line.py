"""One-line explanation of what just happened and what unblocks it."""

from enum import Enum

from rich.text import Text
from textual.widgets import Static

from gconflict.ui import glyphs


class StatusKind(Enum):
    """Severity of a status message."""

    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    BLOCKED = "blocked"


_GLYPHS = {
    StatusKind.INFO: glyphs.STATUS_INFO,
    StatusKind.SUCCESS: glyphs.STATUS_SUCCESS,
    StatusKind.WARNING: glyphs.STATUS_WARNING,
    StatusKind.BLOCKED: glyphs.STATUS_BLOCKED,
}

_STYLES = {
    StatusKind.INFO: "#4ca8e8",
    StatusKind.SUCCESS: "#6fbf73",
    StatusKind.WARNING: "#e8a44c",
    StatusKind.BLOCKED: "#d9645f",
}

_VARIANTS = tuple(f"-{kind.value}" for kind in StatusKind)


class StatusLine(Static):
    """Report an outcome with its reason and its remedy."""

    DEFAULT_CSS = """
    StatusLine {
        height: auto;
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

    def show(self, kind: StatusKind, title: str, detail: str = "") -> None:
        """Replace the message with one of the given severity."""
        self.remove_class(*_VARIANTS)
        self.add_class(f"-{kind.value}")

        text = Text()
        text.append(_GLYPHS[kind], style=_STYLES[kind])
        text.append(f" {title}", style=_STYLES[kind])
        if detail:
            text.append(f"\n  {detail}", style="#79808f")

        self._rendered_text = text.plain
        self.update(text)

    def clear(self) -> None:
        """Remove the message and its severity."""
        self.remove_class(*_VARIANTS)
        self._rendered_text = ""
        self.update("")
