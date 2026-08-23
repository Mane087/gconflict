"""The two sides of one conflict, shown next to each other."""

from collections.abc import Sequence

from rich.text import Text
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Static

from gconflict.models.conflict import Conflict
from gconflict.models.resolution import Resolution
from gconflict.ui import glyphs

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

CHOSEN = "ELEGIDO"


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
    ConflictPanes .pane-header { height: 1; padding: 0 2; }
    ConflictPanes .pane-body { padding: 1 2; text-wrap: nowrap; }
    """

    def __init__(self) -> None:
        super().__init__()
        self._headers = {"current": "", "incoming": ""}
        self._bodies = {"current": "", "incoming": ""}

    def compose(self) -> ComposeResult:
        with Vertical(id="pane-current"):
            yield Static("", id="header-current", classes="pane-header")
            yield Static("", id="body-current", classes="pane-body")
        with Vertical(id="pane-incoming"):
            yield Static("", id="header-incoming", classes="pane-header")
            yield Static("", id="body-incoming", classes="pane-body")

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
        before: Sequence[str] = (),
        after: Sequence[str] = (),
    ) -> None:
        """Render one conflict, its surrounding context, and what is chosen.

        ``before`` and ``after`` are the untouched file lines around the marker
        range; they are shown dimmed so the reader keeps the file's context.
        """
        # Raw file numbering: the marker lines themselves are start_line and
        # end_line, so the body starts one line after the opening marker and the
        # trailing context starts one line after the closing one.
        before_start = conflict.start_line - len(before)
        body_start = conflict.start_line + 1
        after_start = conflict.end_line + 1
        self._render_side(
            "current",
            glyph=glyphs.CURRENT,
            title="CURRENT",
            label=current_label,
            selected=resolution in _INCLUDES_CURRENT,
            lines=conflict.current,
            before=before,
            after=after,
            before_start=before_start,
            body_start=body_start,
            after_start=after_start,
            accent="#e8a44c",
            gutter="#8a6b34",
            body="#f0d3a4",
            header_bg="#1e1810",
            line_bg="#241c10",
        )
        self._render_side(
            "incoming",
            glyph=glyphs.INCOMING,
            title="INCOMING",
            label=incoming_label,
            selected=resolution in _INCLUDES_INCOMING,
            lines=conflict.incoming,
            before=before,
            after=after,
            before_start=before_start,
            body_start=body_start,
            after_start=after_start,
            accent="#4ca8e8",
            gutter="#35708f",
            body="#a8d6f5",
            header_bg="#141821",
            line_bg="#10202c",
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
        before: Sequence[str],
        after: Sequence[str],
        before_start: int,
        body_start: int,
        after_start: int,
        accent: str,
        gutter: str,
        body: str,
        header_bg: str,
        line_bg: str,
    ) -> None:
        """Render one pane's tinted header and its body with file context."""
        header = Text()
        header.append(f"{glyph} ", style=f"{accent} on {header_bg}")
        header.append(title, style=f"bold {accent} on {header_bg}")
        header.append(f"  {label}", style=f"#79808f on {header_bg}")
        if selected:
            header.append("  ")
            header.append(f" {CHOSEN} ", style=f"bold #1a1408 on {accent}")

        content = Text()
        for offset, line in enumerate(before):
            self._append_line(content, before_start + offset, line, "#343b48", "#454c5b")
        for offset, line in enumerate(lines):
            self._append_line(
                content, body_start + offset, line, gutter, body, background=line_bg
            )
        for offset, line in enumerate(after):
            self._append_line(content, after_start + offset, line, "#343b48", "#454c5b")

        self._headers[side] = header.plain
        self._bodies[side] = content.plain
        self.query_one(f"#header-{side}", Static).update(header)
        self.query_one(f"#body-{side}", Static).update(content)
        pane = self.query_one(f"#pane-{side}")
        pane.set_class(selected, "-selected")

    @staticmethod
    def _append_line(
        content: Text,
        number: int,
        line: str,
        gutter: str,
        body: str,
        background: str = "",
    ) -> None:
        """Append one numbered code line, tinted when it belongs to the conflict."""
        if content.plain:
            content.append("\n")
        suffix = f" on {background}" if background else ""
        content.append(str(number).rjust(3), style=f"{gutter}{suffix}")
        content.append(" ", style=f"{gutter}{suffix}")
        content.append(line.rstrip("\r\n"), style=f"{body}{suffix}")
