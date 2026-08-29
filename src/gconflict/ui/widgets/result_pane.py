"""Preview of the text that Save would write to the file."""

from rich.text import Text
from textual.app import ComposeResult
from textual.containers import Vertical, VerticalScroll
from textual.widgets import Static

class ResultPane(Vertical):
    """Show the reconstructed file before anything touches disk."""

    DEFAULT_CSS = """
    ResultPane {
        height: auto;
        max-height: 12;
        background: $surface-2;
        border: solid $line;
    }
    ResultPane > #result-header {
        height: 1;
        padding: 0 2;
        background: $surface-2;
    }
    ResultPane > #result-body {
        height: 1fr;
        background: $surface-2;
    }
    ResultPane > #result-body > #result-content {
        padding: 1 2;
        text-wrap: nowrap;
        background: $surface-2;
    }
    """

    def __init__(self) -> None:
        super().__init__()
        self._header_text = ""
        self._body_text = ""

    def compose(self) -> ComposeResult:
        yield Static("", id="result-header")
        yield VerticalScroll(Static("", id="result-content"), id="result-body")

    @property
    def header_text(self) -> str:
        """Return the plain text of the header."""
        return self._header_text

    @property
    def body_text(self) -> str:
        """Return the plain text of the preview body."""
        return self._body_text

    def show(
        self, text: str, *, saved: bool, first_line: int = 1, max_lines: int = 8
    ) -> None:
        """Render the preview, saying whether it has been written yet."""
        header = Text()
        header.append("RESULT", style="bold #6fbf73")
        header.append("  lo que se escribira en el archivo", style="#4d5462")
        header.append("   ")
        header.append(
            " guardado " if saved else " sin guardar ",
            style="bold #1a1408 on #6fbf73" if saved else "bold #1a0d0d on #d9645f",
        )

        lines = text.splitlines()
        body = Text()
        if not lines:
            body.append("(archivo vacio)", style="#4d5462")
        else:
            for offset, line in enumerate(lines):
                if offset:
                    body.append("\n")
                body.append(str(first_line + offset), style="#4d5462")
                body.append(f" {line}", style="#d6dae3")

        self._header_text = header.plain
        self._body_text = body.plain
        self.query_one("#result-header", Static).update(header)
        self.query_one("#result-content", Static).update(body)

    def clear(self, reason: str = "") -> None:
        """Clear the preview, optionally keeping a status reason in the header."""
        self._body_text = ""
        if not reason:
            self._header_text = ""
            self.query_one("#result-header", Static).update("")
            self.query_one("#result-content", Static).update("")
            return

        header = Text()
        header.append("RESULT", style="bold #6fbf73")
        header.append("  lo que se escribira en el archivo", style="#4d5462")
        header.append("   ")
        header.append(" sin guardar ", style="bold #1a0d0d on #d9645f")
        self._header_text = header.plain
        self.query_one("#result-header", Static).update(header)
        self.query_one("#result-content", Static).update("")
