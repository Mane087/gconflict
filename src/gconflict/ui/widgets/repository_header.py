"""Repository name, operation in progress, and checked-out branch."""

from rich.text import Text
from textual.widgets import Static

from gconflict.models.repository_context import RepositoryContext


class RepositoryHeader(Static):
    """Name where the user is and what Git is in the middle of."""

    DEFAULT_CSS = """
    RepositoryHeader {
        height: 1;
        padding: 0 1;
        background: $surface-2;
        border-bottom: solid $line;
    }
    """

    def __init__(self) -> None:
        super().__init__("")
        self._rendered_text = ""

    @property
    def rendered_text(self) -> str:
        """Return the plain text currently displayed."""
        return self._rendered_text

    def set_context(self, context: RepositoryContext) -> None:
        """Replace the header with the given repository state."""
        text = Text()
        text.append("gconflict", style="bold #e8e9ee")
        text.append(" / ", style="#4d5462")
        text.append(context.name, style="#a4abba")
        text.append("   ")
        text.append(context.operation.value.upper(), style="#e8a44c")
        text.append("   ")
        text.append(context.branch or "detached HEAD", style="#79808f")

        self._rendered_text = text.plain
        self.update(text)
