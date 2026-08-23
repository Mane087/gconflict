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
    ConflictPanes .pane-hint { height: 1; color: $text-4; }
    """

    def __init__(self) -> None:
        super().__init__()
        self._headers = {"current": "", "incoming": ""}
        self._bodies = {"current": "", "incoming": ""}
        self._hints = {"current": "", "incoming": ""}

    def compose(self) -> ComposeResult:
        with Vertical(id="pane-current"):
            yield Static("", id="header-current")
            yield Static("", id="body-current")
            yield Static("", id="hint-current", classes="pane-hint")
        with Vertical(id="pane-incoming"):
            yield Static("", id="header-incoming")
            yield Static("", id="body-incoming")
            yield Static("", id="hint-incoming", classes="pane-hint")

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

    @property
    def current_hint(self) -> str:
        """Return the plain text of the CURRENT footer hint."""
        return self._hints["current"]

    @property
    def incoming_hint(self) -> str:
        """Return the plain text of the INCOMING footer hint."""
        return self._hints["incoming"]

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
            key="c",
            hint="quedarte con CURRENT",
            accent="#e8a44c",
            gutter="#8a6b34",
            body="#f0d3a4",
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
            key="i",
            hint="quedarte con INCOMING",
            accent="#4ca8e8",
            gutter="#35708f",
            body="#a8d6f5",
        )

    def clear(self) -> None:
        """Empty both panes and drop their selection marks."""
        for side in ("current", "incoming"):
            self._headers[side] = ""
            self._bodies[side] = ""
            self._hints[side] = ""
            self.query_one(f"#header-{side}", Static).update("")
            self.query_one(f"#body-{side}", Static).update("")
            self.query_one(f"#hint-{side}", Static).update("")
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
        key: str,
        hint: str,
        accent: str,
        gutter: str,
        body: str,
    ) -> None:
        """Render one pane's header, body with context, and footer hint."""
        header = Text()
        header.append(glyph, style=accent)
        header.append(f" {title}", style=accent)
        header.append(f"  {label}", style="#79808f")
        if selected:
            header.append(f"  {CHOSEN}", style=accent)

        content = Text()
        for offset, line in enumerate(before):
            self._append_line(content, before_start + offset, line, "#343b48", "#454c5b")
        for offset, line in enumerate(lines):
            self._append_line(content, body_start + offset, line, gutter, body)
        for offset, line in enumerate(after):
            self._append_line(content, after_start + offset, line, "#343b48", "#454c5b")

        footer = Text()
        footer.append(f"[{key}]", style=accent)
        footer.append(f" {hint}", style="#4d5462")

        self._headers[side] = header.plain
        self._bodies[side] = content.plain
        self._hints[side] = footer.plain
        self.query_one(f"#header-{side}", Static).update(header)
        self.query_one(f"#body-{side}", Static).update(content)
        self.query_one(f"#hint-{side}", Static).update(footer)
        pane = self.query_one(f"#pane-{side}")
        pane.set_class(selected, "-selected")

    @staticmethod
    def _append_line(
        content: Text, number: int, line: str, gutter: str, body: str
    ) -> None:
        """Append one numbered code line."""
        if content.plain:
            content.append("\n")
        content.append(str(number).rjust(3), style=gutter)
        content.append(" ", style=gutter)
        content.append(line.rstrip("\r\n"), style=body)
