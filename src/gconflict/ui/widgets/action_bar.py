"""Available actions, grouped by what they are allowed to touch."""

from collections.abc import Sequence
from dataclasses import dataclass

from rich.text import Text
from textual.events import Click
from textual.widgets import Static

SCOPES = ("CONFLICT", "FILE", "REPO")
_SCOPE_WIDTH = max(len(scope) for scope in SCOPES) + 2


@dataclass(frozen=True)
class Action:
    """One keyboard action and whether the user may take it right now."""

    key: str
    label: str
    scope: str
    enabled: bool = True
    reason: str = ""
    active: bool = False


class ActionBar(Static):
    """Show one row per scope, in SCOPES order, with blocking reasons."""

    DEFAULT_CSS = """
    ActionBar {
        height: auto;
        padding: 1 2;
        background: $surface-2;
        border-top: solid $line;
    }
    """

    def __init__(self) -> None:
        super().__init__("")
        self._rendered_text = ""
        self._actions: tuple[Action, ...] = ()
        self._expanded = False

    @property
    def rendered_text(self) -> str:
        """Return the plain text currently displayed."""
        return self._rendered_text

    def set_actions(self, actions: Sequence[Action]) -> None:
        """Replace every action shown."""
        for action in actions:
            if action.scope not in SCOPES:
                raise ValueError(f"unknown action scope: {action.scope}")

        self._actions = tuple(actions)
        self._refresh_content()
        self.refresh()

    def on_click(self, event: Click) -> None:
        """Toggle the action groups when the compact control is clicked."""
        event.stop()
        self._expanded = not self._expanded
        self._refresh_content()
        self.refresh()

    def _refresh_content(self) -> None:
        """Refresh the compact control and, when open, all action groups."""
        text = Text()
        text.append("▾ Actions" if self._expanded else "▸ Actions", style="bold #d6dae3")
        if self._expanded:
            for scope in SCOPES:
                in_scope = [action for action in self._actions if action.scope == scope]
                if not in_scope:
                    continue
                text.append("\n")
                text.append(scope.ljust(_SCOPE_WIDTH), style="#4d5462")
                for position, action in enumerate(in_scope):
                    if position:
                        text.append("  ")
                    self._append_action(text, action)

        self._rendered_text = text.plain
        self.update(text)

    @staticmethod
    def _append_action(text: Text, action: Action) -> None:
        """Append one action as a chip: the key in its own box, then the label."""
        if not action.enabled:
            key_style = "#4d5462 on #171b24"
            label_style = "#4d5462 on #171b24"
        elif action.active:
            key_style = "bold #1a1408 on #e8a44c"
            label_style = "#f0d3a4 on #241c10"
        else:
            key_style = "bold #d6dae3 on #2e3442"
            label_style = "#a4abba on #171b24"

        text.append(f" {action.key} ", style=key_style)
        text.append(f" {action.label} ", style=label_style)
        if action.reason:
            text.append(f" {action.reason}", style="#4d5462")
