"""Application entrypoint for gconflict."""

import argparse
from pathlib import Path

from textual.app import App, ComposeResult
from textual import on
from textual.widgets import Footer, Header, Label, ListItem, ListView
from textual.worker import Worker, WorkerState

from gconflict import __version__
from gconflict.models.resolution import Resolution
from gconflict.models.conflicted_file import ConflictedFile, ConflictType
from gconflict.services.conflict_service import ConflictService
from gconflict.services.editor_service import EditorService


class GConflictApp(App[None]):
    """Minimal Textual application shell."""

    TITLE = "gconflict"
    BINDINGS = [
        ("n", "next_conflict", "Next"), ("p", "previous_conflict", "Previous"),
        ("u", "undo", "Undo"),
        ("s", "save", "Save"),
        ("r", "mark_resolved", "Mark resolved"),
        ("c", "resolve_current", "Current"), ("i", "resolve_incoming", "Incoming"),
        ("b", "resolve_both_current_first", "Both (Current first)"),
        ("B", "resolve_both_incoming_first", "Both (Incoming first)"),
        ("e", "edit", "Edit externally"),
    ]

    def __init__(
        self,
        service: ConflictService | None = None,
        editor_service: EditorService | None = None,
        cwd: str | Path | None = None,
    ) -> None:
        super().__init__()
        self.service = service or ConflictService()
        self.editor_service = editor_service or EditorService()
        self.cwd = cwd
        self.selected_file: ConflictedFile | None = None
        self._conflicted_files: list[ConflictedFile] = []
        self.snapshot: object | None = None
        self.loaded_conflicts: list[object] = []
        self.resolutions: list[Resolution | None] = []
        self._resolution_history: list[list[Resolution | None]] = []
        self.active_conflict_index = 0
        self._save_succeeded = False
        self._editor_worker: Worker[bool] | None = None

    def compose(self) -> ComposeResult:
        yield Header()
        root = self.service.root(self.cwd)
        conflicted_files = self.service.conflicted_file_descriptors(root)
        if conflicted_files:
            self._conflicted_files = conflicted_files
            yield ListView(
                *(ListItem(Label(str(descriptor.path))) for descriptor in conflicted_files)
            )
            yield Label("Conflict 0 / 0", id="conflict-count")
            yield Label("CURRENT", id="current")
            yield Label("INCOMING", id="incoming")
        else:
            yield Label("No unresolved Git conflicts found.", id="conflict-count")
        yield Footer()

    @on(ListView.Selected)
    def file_selected(self, event: ListView.Selected) -> None:
        if event.list_view.index is not None:
            self.selected_file = self._conflicted_files[event.list_view.index]
            self._reload_selected_file()

    def _reload_selected_file(self) -> None:
        """Clear transient state and rebuild it from the selected file."""
        assert self.selected_file is not None
        self.snapshot = None
        self.loaded_conflicts = []
        self.resolutions = []
        self._resolution_history = []
        self.active_conflict_index = 0
        self._save_succeeded = False
        if self.selected_file.conflict_type is not ConflictType.CONTENT:
            self.query_one("#conflict-count", Label).update(self._unsupported_message())
            self.query_one("#current", Label).update("")
            self.query_one("#incoming", Label).update("")
            return
        root = self.service.root(self.cwd)
        absolute_path = root / self.selected_file.path
        self.snapshot, self.loaded_conflicts = self.service.load_conflicts(absolute_path)
        self.resolutions = [None] * len(self.loaded_conflicts)
        self._resolution_history = [[] for _ in self.loaded_conflicts]
        if not self.loaded_conflicts:
            self.query_one("#current", Label).update("")
            self.query_one("#incoming", Label).update("")
        self._render_active_conflict()

    def action_edit(self) -> None:
        """Open the selected file in a worker without blocking the UI."""
        if self.selected_file is None:
            return
        root = self.service.root(self.cwd)
        absolute_path = root / self.selected_file.path
        self._editor_worker = self.run_worker(
            lambda: self.editor_service.open_file(absolute_path, root),
            thread=True,
        )

    @on(Worker.StateChanged)
    def _editor_worker_state_changed(self, event: Worker.StateChanged) -> None:
        """Handle editor completion through Textual's worker event API."""
        if event.worker is not self._editor_worker:
            return
        if event.state is WorkerState.ERROR:
            self.query_one("#conflict-count", Label).update(
                f"Editor failed: {event.worker.error}"
            )
            return
        if event.state is not WorkerState.SUCCESS:
            return
        opened = event.worker.result
        if not opened:
            self.query_one("#conflict-count", Label).update(
                "No editor configured. Set GIT_EDITOR, VISUAL, or EDITOR."
            )
            return
        self._reload_selected_file()

    def _render_active_conflict(self) -> None:
        count = len(self.loaded_conflicts)
        status = "RESOLVED" if count and self.resolutions[self.active_conflict_index] else "UNRESOLVED"
        self.query_one("#conflict-count", Label).update(
            f"Conflict {self.active_conflict_index + 1 if count else 0} / {count} — {status}"
        )
        if count:
            conflict = self.loaded_conflicts[self.active_conflict_index]
            self.query_one("#current", Label).update(f"CURRENT\n{''.join(conflict.current)}")
            self.query_one("#incoming", Label).update(f"INCOMING\n{''.join(conflict.incoming)}")

    def action_next_conflict(self) -> None:
        if self.loaded_conflicts:
            self.active_conflict_index = min(
                self.active_conflict_index + 1, len(self.loaded_conflicts) - 1
            )
            self._render_active_conflict()

    def action_previous_conflict(self) -> None:
        if self.loaded_conflicts:
            self.active_conflict_index = max(self.active_conflict_index - 1, 0)
            self._render_active_conflict()

    def _set_resolution(self, resolution: Resolution) -> None:
        if self._unsupported_selected():
            return
        if self.loaded_conflicts:
            index = self.active_conflict_index
            self._resolution_history[index].append(self.resolutions[index])
            self.resolutions[index] = resolution
            self._render_active_conflict()

    def action_undo(self) -> None:
        if self.loaded_conflicts:
            history = self._resolution_history[self.active_conflict_index]
            if history:
                self.resolutions[self.active_conflict_index] = history.pop()
                self._render_active_conflict()

    def action_save(self) -> None:
        if self._unsupported_selected():
            return
        if self.snapshot is None:
            self.query_one("#conflict-count", Label).update(
                "Save blocked: no loaded snapshot."
            )
            return
        if not self.loaded_conflicts:
            self.query_one("#conflict-count", Label).update(
                "Save blocked: no loaded conflicts."
            )
            return
        if any(resolution is None for resolution in self.resolutions):
            self.query_one("#conflict-count", Label).update(
                "Save blocked: resolve all conflicts before saving."
            )
            return

        try:
            snapshot = self.service.resolve_file(
                self.snapshot, self.loaded_conflicts, self.resolutions  # type: ignore[arg-type]
            )
        except Exception as error:
            self.query_one("#conflict-count", Label).update(f"Save failed: {error}")
            return

        self.snapshot = snapshot
        self.loaded_conflicts = []
        self.resolutions = []
        self._resolution_history = []
        self.active_conflict_index = 0
        self._save_succeeded = True
        self.query_one("#conflict-count", Label).update("Saved successfully.")

    def action_mark_resolved(self) -> None:
        if self._unsupported_selected():
            return
        if not self._save_succeeded or self.selected_file is None:
            self.query_one("#conflict-count", Label).update(
                "Mark resolved blocked: save successfully first."
            )
            return

        try:
            self.service.mark_resolved(self.selected_file.path, cwd=self.cwd)
        except Exception as error:
            self.query_one("#conflict-count", Label).update(
                f"Mark resolved failed: {error}"
            )
            return

        self.query_one("#conflict-count", Label).update(
            "Marked resolved successfully."
        )

    def action_resolve_current(self) -> None:
        self._set_resolution(Resolution.CURRENT)

    def action_resolve_incoming(self) -> None:
        self._set_resolution(Resolution.INCOMING)

    def action_resolve_both_current_first(self) -> None:
        self._set_resolution(Resolution.BOTH_CURRENT_FIRST)

    def action_resolve_both_incoming_first(self) -> None:
        self._set_resolution(Resolution.BOTH_INCOMING_FIRST)

    def _unsupported_selected(self) -> bool:
        if (
            self.selected_file is not None
            and self.selected_file.conflict_type is not ConflictType.CONTENT
        ):
            self.query_one("#conflict-count", Label).update(
                self._unsupported_message()
            )
            return True
        return False

    def _unsupported_message(self) -> str:
        """Describe how an unsupported conflict must be handled externally."""
        assert self.selected_file is not None
        guidance = {
            ConflictType.ADD_ADD: "Compare/combine externally.",
            ConflictType.MODIFY_DELETE: "Choose deletion or the modified version externally.",
            ConflictType.OTHER: "Use external Git tools.",
        }[self.selected_file.conflict_type]
        return (
            f"Unsupported conflict type: {self.selected_file.conflict_type.value}\n"
            f"{guidance}"
        )


def main() -> int:
    """Launch the application."""
    parser = argparse.ArgumentParser(prog="gconflict")
    parser.add_argument("directory", nargs="*", default=[])
    parser.add_argument("--version", action="version", version=f"gconflict {__version__}")
    try:
        args = parser.parse_args()
    except SystemExit as error:
        return 0 if error.code == 0 else 4
    cwd = " ".join(args.directory) if args.directory else None
    service = ConflictService()
    try:
        root = service.root(cwd)
    except Exception:
        print("Not a Git repository.")
        return 2

    if not service.conflicted_file_descriptors(root):
        print("No unresolved Git conflicts found.")
        return 0

    GConflictApp(service=service, cwd=cwd).run()
    return 0
