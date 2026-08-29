"""The two sides of one conflict, shown next to each other."""

from collections.abc import Sequence

from rich.text import Text
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical, VerticalScroll
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
        border: round $line;
    }
    ConflictPanes > #pane-current.-selected { border: round $current; }
    ConflictPanes > #pane-incoming.-selected { border: round $incoming; }
    ConflictPanes .pane-header {
        height: 2;
        padding: 0 2;
        background: $surface-2;
        border-bottom: solid $line;
    }
    ConflictPanes > #pane-current.-selected .pane-header {
        color: $current;
        border-bottom: solid $current;
    }
    ConflictPanes > #pane-incoming.-selected .pane-header {
        color: $incoming;
        border-bottom: solid $incoming;
    }
    ConflictPanes .pane-scroll {
        height: 1fr;
        background: $surface-2;
    }
    ConflictPanes .pane-body {
        height: auto;
        padding: 1 2;
        text-wrap: nowrap;
        background: $surface-2;
    }
    """

    def __init__(self) -> None:
        super().__init__()
        self._headers = {"current": "", "incoming": ""}
        self._bodies = {"current": "", "incoming": ""}
        self._shown_conflict: tuple[int, int] | None = None

    def compose(self) -> ComposeResult:
        for side in ("current", "incoming"):
            with Vertical(id=f"pane-{side}"):
                yield Static("", id=f"header-{side}", classes="pane-header")
                # The body needs a scrollable container around it: a bare Static
                # reports is_scrollable == False, so Textual ignores the wheel.
                with self._scroll_container(side):
                    yield Static("", id=f"body-{side}", classes="pane-body")

    @staticmethod
    def _scroll_container(side: str) -> VerticalScroll:
        """Build the scrollable wrapper for one pane body."""
        container = VerticalScroll(id=f"scroll-{side}", classes="pane-scroll")
        # Scrolling with the wheel does not need focus, and keeping these out of
        # the focus chain leaves the app-level key bindings untouched.
        container.can_focus = False
        return container

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
        # Numbering follows the file as it would look if this side were chosen:
        # the markers disappear, so the body takes over the opening marker's line
        # and the trailing context continues right after it. Each side therefore
        # numbers its own trailing context, and the panes agree with RESULT.
        before_start = conflict.start_line - len(before)
        body_start = conflict.start_line
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
            accent="#e8a44c",
            gutter="#8a6b34",
            body="#f0d3a4",
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
            accent="#4ca8e8",
            gutter="#35708f",
            body="#a8d6f5",
            line_bg="#10202c",
        )
        # Keep the offset while the same conflict is re-rendered (choosing a
        # resolution redraws it), and start from the top on a different one.
        key = (conflict.index, conflict.start_line)
        if key != self._shown_conflict:
            self._shown_conflict = key
            self._reset_scroll()

    def _reset_scroll(self) -> None:
        """Send both pane bodies back to their first line."""
        for side in ("current", "incoming"):
            self.query_one(f"#scroll-{side}", VerticalScroll).scroll_to(
                y=0, animate=False
            )

    def clear(self) -> None:
        """Empty both panes and drop their selection marks."""
        self._shown_conflict = None
        self._reset_scroll()
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
        accent: str,
        gutter: str,
        body: str,
        line_bg: str,
    ) -> None:
        """Render one pane's tinted header and its body with file context."""
        header = Text()
        header.append(f"{glyph} ", style=accent)
        header.append(title, style=f"bold {accent}")
        header.append(f"  |  {label}", style="#79808f")
        if selected:
            header.append("  ")
            header.append(f" {CHOSEN} ", style=f"bold #1a1408 on {accent}")

        after_start = body_start + len(lines)

        content = Text()
        logical_content = Text()
        body_widget = self.query_one(f"#body-{side}", Static)
        body_width = body_widget.content_region.width
        for offset, line in enumerate(before):
            self._append_line(content, before_start + offset, line, "#343b48", "#454c5b")
            self._append_line(logical_content, before_start + offset, line, "#343b48", "#454c5b")
        for offset, line in enumerate(lines):
            self._append_line(
                content,
                body_start + offset,
                line,
                gutter,
                body,
                background=line_bg,
                width=body_width,
            )
            self._append_line(
                logical_content,
                body_start + offset,
                line,
                gutter,
                body,
            )
        for offset, line in enumerate(after):
            self._append_line(content, after_start + offset, line, "#343b48", "#454c5b")
            self._append_line(logical_content, after_start + offset, line, "#343b48", "#454c5b")

        self._headers[side] = header.plain
        self._bodies[side] = logical_content.plain
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
        width: int = 0,
    ) -> None:
        """Append one numbered code line, tinted when it belongs to the conflict."""
        if content.plain:
            content.append("\n")
        suffix = f" on {background}" if background else ""
        numbered_line = Text()
        numbered_line.append(str(number).rjust(3), style=f"{gutter}{suffix}")
        numbered_line.append(" ", style=f"{gutter}{suffix}")
        line_without_ending = line.removesuffix("\n").removesuffix("\r")
        numbered_line.append(line_without_ending, style=f"{body}{suffix}")
        if background and width > numbered_line.cell_len:
            numbered_line.append(
                " " * (width - numbered_line.cell_len),
                style=f"{body}{suffix}",
            )
        content.append_text(numbered_line)
