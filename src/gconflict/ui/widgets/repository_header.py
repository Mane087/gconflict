"""Repository name, operation in progress, and the branches being combined."""

from rich.text import Text
from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.widgets import Static

from gconflict.models.repository_context import RepositoryContext

# A terminal paints character cells, so the design's vector branch mark is drawn
# with the Unicode branch glyph rather than assets/git.png.
BRANCH_MARK = "⎇"
INCOMING_ARROW = "←"


class RepositoryHeader(Horizontal):
    """Name where the user is, and what Git is in the middle of."""

    DEFAULT_CSS = """
    RepositoryHeader {
        /* One row of breathing room above the text, then the content row, then
           the bottom border: three rows in total. */
        height: 3;
        padding: 1 2 0 2;
        background: $surface-2;
        border-bottom: solid $line;
    }
    RepositoryHeader > #header-left {
        width: 1fr;
        text-wrap: nowrap;
    }
    RepositoryHeader > #header-right {
        width: auto;
        text-align: right;
        text-wrap: nowrap;
    }
    """

    def __init__(self) -> None:
        super().__init__()
        self._left = ""
        self._right = ""

    def compose(self) -> ComposeResult:
        yield Static("", id="header-left")
        yield Static("", id="header-right")

    @property
    def rendered_text(self) -> str:
        """Return the plain text currently displayed, left group then right."""
        if not self._left:
            return ""
        return f"{self._left}   {self._right}"

    @property
    def left_text(self) -> str:
        """Return the plain text of the identity group."""
        return self._left

    @property
    def right_text(self) -> str:
        """Return the plain text of the operation group."""
        return self._right

    def set_context(self, context: RepositoryContext) -> None:
        """Replace the header with the given repository state."""
        left = Text()
        left.append(f"{BRANCH_MARK}  ", style="#e8a44c")
        left.append("gconflict", style="bold #e8e9ee")
        left.append("  /  ", style="#4d5462")
        left.append(context.name, style="#a4abba")

        right = Text()
        right.append(
            f" {context.operation.value.upper()} ", style="bold #e8a44c on #241c10"
        )
        right.append("   ")
        right.append(context.branch or "detached HEAD", style="#79808f")
        if context.incoming_ref:
            right.append(f"  {INCOMING_ARROW}  ", style="#4d5462")
            right.append(context.incoming_ref, style="#79808f")

        self._left = left.plain
        self._right = right.plain
        self.query_one("#header-left", Static).update(left)
        self.query_one("#header-right", Static).update(right)
