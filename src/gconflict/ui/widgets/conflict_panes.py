"""The two sides of one conflict, shown next to each other."""

from collections.abc import Sequence

from rich.text import Text
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Static

from gconflict.models.conflict import Conflict
from gconflict.models.resolution import Resolution

_INCLUDES_CURRENT = {
    Resolution.CURRENT,
    Resolution.BOTH_CURRENT_FIRST,
    Resolution.BOTH_INCOMING_FIRST,
}
_INCLUDES_INCOMING = {
    Resolution.INCOMING,
    Resolution.BOTH_CURRENT_FIRST,
    Resolution.BOTH_INCOMING_FIRST,
}


class ConflictPanes(Horizontal):
    """Render CURRENT and INCOMING side by side, marking what is chosen."""

    DEFAULT_CSS = """
    ConflictPanes {
        height: 1fr;
    }
    ConflictPanes > Vertical {
        width: 1fr;
        background: $surface-2;
        border: solid $line;
    }
    ConflictPanes > #pane-current.-selected { border: solid $current; }
    ConflictPanes > #pane-incoming.-selected { border: solid $incoming; }
    """

    def __init__(self) -> None:
        super().__init__()
        self._headers = {"current": "", "incoming": ""}
        self._bodies = {"current": "", "incoming": ""}

    def compose(self) -> ComposeResult:
        with Vertical(id="pane-current"):
            yield Static("", id="header-current")
            yield Static("", id="body-current")
        with Vertical(id="pane-incoming"):
            yield Static("", id="header-incoming")
            yield Static("", id="body-incoming")

    @property
    def current_header(self) -> str:
        """Return the plain text of the CURRENT header."""
        return self._headers["current"]

    @property
    def incoming_header(self) -> str:
        """Return the plain text of the INCOMING header."""
        return self._headers["incoming"]

    @property
    def current_text(self) -> str:
        """Return the plain text of the CURRENT body."""
        return self._bodies["current"]

    @property
    def incoming_text(self) -> str:
        """Return the plain text of the INCOMING body."""
        return self._bodies["incoming"]

    def show(
        self,
        conflict: Conflict,
        resolution: Resolution | None,
        current_label: str,
        incoming_label: str,
    ) -> None:
        """Render one conflict and mark the sides the resolution keeps."""
        # The marker line itself is start_line, so content starts one line later.
        first_line = conflict.start_line + 1
        self._render_side(
            "current",
            glyph="*",
            title="CURRENT",
            label=current_label,
            selected=resolution in _INCLUDES_CURRENT,
            lines=conflict.current,
            first_line=first_line,
            accent="#e8a44c",
            gutter="#8a6b34",
            body="#f0d3a4",
        )
        self._render_side(
            "incoming",
            glyph="o",
            title="INCOMING",
            label=incoming_label,
            selected=resolution in _INCLUDES_INCOMING,
            lines=conflict.incoming,
            first_line=first_line,
            accent="#4ca8e8",
            gutter="#35708f",
            body="#a8d6f5",
        )

    def clear(self) -> None:
        """Empty both panes and drop their selection marks."""
        for side in ("current", "incoming"):
            self._headers[side] = ""
            self._bodies[side] = ""
            self.query_one(f"#header-{side}", Static).update("")
            self.query_one(f"#body-{side}", Static).update("")
            self.query_one(f"#pane-{side}").remove_class("-selected")

    def _render_side(
        self,
        side: str,
        *,
        glyph: str,
        title: str,
        label: str,
        selected: bool,
        lines: Sequence[str],
        first_line: int,
        accent: str,
        gutter: str,
        body: str,
    ) -> None:
        """Render one pane's header and body."""
        header = Text()
        header.append(glyph, style=accent)
        header.append(f" {title}", style=accent)
        header.append(f"  {label}", style="#79808f")
        if selected:
            header.append("  SELECTED", style=accent)

        content = Text()
        for offset, line in enumerate(lines):
            if offset:
                content.append("\n")
            content.append(str(first_line + offset).rjust(3), style=gutter)
            content.append(" ", style=gutter)
            content.append(line.rstrip("\r\n"), style=body)

        self._headers[side] = header.plain
        self._bodies[side] = content.plain
        self.query_one(f"#header-{side}", Static).update(header)
        self.query_one(f"#body-{side}", Static).update(content)
        pane = self.query_one(f"#pane-{side}")
        pane.set_class(selected, "-selected")
