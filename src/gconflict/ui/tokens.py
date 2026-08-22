"""The single source of the design tokens every widget styles itself with.

Textual parses a widget's ``DEFAULT_CSS`` with only the variables the running
app publishes through ``get_css_variables``, so the tokens cannot live in
``app.tcss`` alone: a widget mounted by any other app would fail to parse.
"""

from textual.app import App

TOKENS: dict[str, str] = {
    "surface-0": "#0b0d12",
    "surface-1": "#10131a",
    "surface-2": "#12151d",
    "surface-3": "#1c202b",
    "line": "#272c39",
    "text-1": "#d6dae3",
    "text-2": "#a4abba",
    "text-3": "#79808f",
    "text-4": "#4d5462",
    "text-5": "#343b48",
    "current": "#e8a44c",
    "current-bg": "#241c10",
    "current-line": "#8a6b34",
    "current-text": "#f0d3a4",
    "incoming": "#4ca8e8",
    "incoming-bg": "#10202c",
    "incoming-line": "#35708f",
    "incoming-text": "#a8d6f5",
    "ok": "#6fbf73",
    "danger": "#d9645f",
}


class TokenApp(App[None]):
    """Base application that publishes the design tokens to every stylesheet."""

    def get_css_variables(self) -> dict[str, str]:
        """Add the design tokens to the variables Textual resolves CSS with."""
        return {**super().get_css_variables(), **TOKENS}
