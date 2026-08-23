"""Application entrypoint for gconflict."""

import argparse
from pathlib import Path

from textual.app import ComposeResult
from textual import on
from textual.containers import Horizontal, Vertical
from textual.widgets import ListView
from textual.worker import Worker, WorkerState

from gconflict import __version__
from gconflict.git.operation import GitOperation
from gconflict.models.conflicted_file import ConflictedFile, ConflictType
from gconflict.models.file_progress import FileProgress
from gconflict.models.repository_context import RepositoryContext
from gconflict.models.resolution import Resolution
from gconflict.services.conflict_service import ConflictService
from gconflict.services.editor_service import EditorService
from gconflict.ui.tokens import TokenApp
from gconflict.ui.widgets.action_bar import Action, ActionBar
from gconflict.ui.widgets.conflict_panes import ConflictPanes
from gconflict.ui.widgets.conflict_rail import ConflictRail
from gconflict.ui.widgets.file_sidebar import FileSidebar, SidebarEntry
from gconflict.ui.widgets.repository_header import RepositoryHeader
from gconflict.ui.widgets.result_pane import ResultPane
from gconflict.ui.widgets.status_line import StatusKind, StatusLine


class GConflictApp(TokenApp):
    """Textual interface for resolving Git conflicts."""

    TITLE = "gconflict"
    CSS_PATH = "ui/app.tcss"
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

    _CONTINUE_COMMANDS = {
        GitOperation.MERGE: "git merge --continue",
        GitOperation.REBASE: "git rebase --continue",
        GitOperation.CHERRY_PICK: "git cherry-pick --continue",
        GitOperation.REVERT: "git revert --continue",
        GitOperation.NONE: "git commit",
    }

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
        self._repo_context: RepositoryContext | None = None
        self._progress: list[FileProgress] = []
        self._resolved_paths: set[Path] = set()

    def compose(self) -> ComposeResult:
        yield RepositoryHeader()
        with Horizontal(id="body"):
            yield FileSidebar()
            with Vertical(id="editor"):
                yield ConflictRail()
                yield ConflictPanes()
                yield ResultPane()
        yield StatusLine()
        yield ActionBar()

    def on_mount(self) -> None:
        """Load repository state once the widgets exist."""
        self._repo_context = self.service.context(self.cwd)
        self._progress = self.service.file_progress(self.cwd)
        self._conflicted_files = [item.file for item in self._progress]
        self.query_one(RepositoryHeader).set_context(self._repo_context)
        self._refresh_view()
        self.query_one(FileSidebar).query_one(ListView).focus()

    @on(ListView.Selected)
    def file_selected(self, event: ListView.Selected) -> None:
        # Resolve through the sidebar, never by row position: ListView.clear()
        # removes deferred, so a stale row can outlive the file it pointed at.
        entry = self.query_one(FileSidebar).entry_for(event.item.id)
        if entry is None:
            return
        for item in self._progress:
            if item.file.path == entry.path:
                self.selected_file = item.file
                self._reload_selected_file()
                return

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
            title, detail = self._unsupported_message(self.selected_file.conflict_type)
            self.query_one(StatusLine).show(StatusKind.BLOCKED, title, detail)
            self.query_one(ConflictPanes).clear()
            self.query_one(ResultPane).clear()
            self.query_one(ConflictRail).clear()
            self._refresh_actions()
            return
        root = self.service.root(self.cwd)
        absolute_path = root / self.selected_file.path
        self.snapshot, self.loaded_conflicts = self.service.load_conflicts(absolute_path)
        self.resolutions = [None] * len(self.loaded_conflicts)
        self._resolution_history = [[] for _ in self.loaded_conflicts]
        self.query_one(StatusLine).clear()
        self._refresh_view()

    def _refresh_view(self) -> None:
        """Rebuild every widget from the current in-memory state."""
        sidebar = self.query_one(FileSidebar)
        sidebar.set_entries(
            [self._sidebar_entry(item) for item in self._progress],
            selected=self._selected_index(),
        )
        sidebar.set_progress(
            conflicts_resolved=sum(1 for item in self.resolutions if item is not None),
            conflicts_total=sum(item.total for item in self._progress),
            files_resolved=len(self._resolved_paths),
            files_total=len(self._progress),
        )
        self._render_active_conflict()
        self._refresh_actions()

    def _sidebar_entry(self, item: FileProgress) -> SidebarEntry:
        """Describe one file for the sidebar."""
        if not item.supported:
            return SidebarEntry(item.file.path, "!", "no soportado")
        if item.file.path in self._resolved_paths:
            return SidebarEntry(item.file.path, "+", "guardado - staged")
        return SidebarEntry(item.file.path, "*", f"{item.total} sin resolver")

    def _selected_index(self) -> int | None:
        """Return the position of the selected file, highlighting the first by default."""
        if self.selected_file is None:
            return 0 if self._progress else None
        for position, item in enumerate(self._progress):
            if item.file.path == self.selected_file.path:
                return position
        return None

    def _refresh_actions(self) -> None:
        """Rebuild the action bar from what is currently allowed."""
        supported = (
            self.selected_file is not None
            and self.selected_file.conflict_type is ConflictType.CONTENT
        )
        active = self.resolutions[self.active_conflict_index] if self.resolutions else None
        pending = sum(1 for item in self.resolutions if item is None)

        conflict_actions = [
            Action("c", "Current", "CONFLICT", supported, active=active is Resolution.CURRENT),
            Action("i", "Incoming", "CONFLICT", supported, active=active is Resolution.INCOMING),
            Action(
                "b", "Both C-I", "CONFLICT", supported,
                active=active is Resolution.BOTH_CURRENT_FIRST,
            ),
            Action(
                "B", "Both I-C", "CONFLICT", supported,
                active=active is Resolution.BOTH_INCOMING_FIRST,
            ),
            Action("u", "Undo", "CONFLICT", supported),
            Action("e", "Editor externo", "CONFLICT", self.selected_file is not None),
        ]

        file_actions = [
            Action(
                "s", "Save", "FILE", supported and not pending,
                reason=self._save_reason(),
            ),
            Action(
                "r", "Mark resolved", "FILE", self._save_succeeded,
                reason="" if self._save_succeeded else "guarda primero con s",
            ),
        ]
        repo_actions = [
            Action("up/down", "Elegir archivo", "REPO"),
            Action("enter", "Abrir archivo", "REPO"),
            Action("q", "Salir", "REPO"),
        ]
        self.query_one(ActionBar).set_actions(
            [*conflict_actions, *file_actions, *repo_actions]
        )

    def _save_reason(self) -> str:
        """Explain in one clause why Save is unavailable, or return an empty string."""
        if self.selected_file is None:
            return "selecciona un archivo"
        if self.selected_file.conflict_type is not ConflictType.CONTENT:
            return "tipo de conflicto no soportado"
        if self.snapshot is None:
            return "no hay archivo cargado"
        if not self.loaded_conflicts:
            return "el archivo no tiene conflictos cargados"
        pending = sum(1 for item in self.resolutions if item is None)
        if not pending:
            return ""
        return (
            f"falta{'n' if pending != 1 else ''} {pending} "
            f"de {len(self.resolutions)} conflictos sin eleccion"
        )

    def action_edit(self) -> None:
        """Open the selected file in a worker without blocking the UI."""
        if self.selected_file is None:
            return
        root = self.service.root(self.cwd)
        absolute_path = root / self.selected_file.path
        self.query_one(StatusLine).show(
            StatusKind.INFO,
            "Editor externo abierto",
            "al cerrarlo se relee el archivo desde disco",
        )
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
            self.query_one(StatusLine).show(
                StatusKind.BLOCKED, "El editor fallo", str(event.worker.error)
            )
            return
        if event.state is not WorkerState.SUCCESS:
            return
        opened = event.worker.result
        if not opened:
            self.query_one(StatusLine).show(
                StatusKind.BLOCKED,
                "No encontre un editor",
                "define GIT_EDITOR, VISUAL o EDITOR",
            )
            return
        self._reload_selected_file()

    def _render_active_conflict(self) -> None:
        """Render the active conflict into the panes and the result preview."""
        panes = self.query_one(ConflictPanes)
        result = self.query_one(ResultPane)
        rail = self.query_one(ConflictRail)
        if not self.loaded_conflicts or self._repo_context is None:
            panes.clear()
            result.clear()
            rail.clear()
            return

        conflict = self.loaded_conflicts[self.active_conflict_index]
        assert self.selected_file is not None
        rail.show(
            self.active_conflict_index,
            self.resolutions,
            f"{self.selected_file.path}:{conflict.start_line}",
        )
        panes.show(
            conflict,
            self.resolutions[self.active_conflict_index],
            self._repo_context.current_label,
            self._repo_context.incoming_label,
        )

        if any(resolution is None for resolution in self.resolutions):
            result.clear()
            return
        text = self.service.preview_resolution(
            self.snapshot, self.loaded_conflicts, self.resolutions
        )
        result.show(text, saved=self._save_succeeded)

    def action_next_conflict(self) -> None:
        if self.loaded_conflicts:
            self.active_conflict_index = min(
                self.active_conflict_index + 1, len(self.loaded_conflicts) - 1
            )
            self._refresh_view()

    def action_previous_conflict(self) -> None:
        if self.loaded_conflicts:
            self.active_conflict_index = max(self.active_conflict_index - 1, 0)
            self._refresh_view()

    def _set_resolution(self, resolution: Resolution) -> None:
        if self._unsupported_selected():
            return
        if self.loaded_conflicts:
            index = self.active_conflict_index
            self._resolution_history[index].append(self.resolutions[index])
            self.resolutions[index] = resolution
            self._refresh_view()

    def action_undo(self) -> None:
        if self.loaded_conflicts:
            history = self._resolution_history[self.active_conflict_index]
            if history:
                self.resolutions[self.active_conflict_index] = history.pop()
                self._refresh_view()

    def action_save(self) -> None:
        if self._unsupported_selected():
            return
        reason = self._save_reason()
        if reason:
            self.query_one(StatusLine).show(
                StatusKind.BLOCKED, "No puedes guardar todavia", reason
            )
            return

        try:
            snapshot = self.service.resolve_file(
                self.snapshot, self.loaded_conflicts, self.resolutions  # type: ignore[arg-type]
            )
        except Exception as error:
            self.query_one(StatusLine).show(StatusKind.BLOCKED, "Save fallo", str(error))
            return

        resolved = len(self.loaded_conflicts)
        self.snapshot = snapshot
        self.loaded_conflicts = []
        self.resolutions = []
        self._resolution_history = []
        self.active_conflict_index = 0
        self._save_succeeded = True
        assert self.selected_file is not None
        self.query_one(StatusLine).show(
            StatusKind.SUCCESS,
            f"Guardado - {self.selected_file.path.name}",
            f"{resolved} conflictos resueltos - r para hacer git add",
        )
        self._refresh_view()

    def action_mark_resolved(self) -> None:
        if self._unsupported_selected():
            return
        if not self._save_succeeded or self.selected_file is None:
            self.query_one(StatusLine).show(
                StatusKind.BLOCKED, "Marcar resuelto bloqueado", "guarda primero con s"
            )
            return

        try:
            self.service.mark_resolved(self.selected_file.path, cwd=self.cwd)
        except Exception as error:
            self.query_one(StatusLine).show(
                StatusKind.BLOCKED, "Marcar resuelto fallo", str(error)
            )
            return

        self._resolved_paths.add(self.selected_file.path)
        self._progress = self.service.file_progress(self.cwd)
        self._conflicted_files = [item.file for item in self._progress]
        if not self._progress:
            self._report_all_resolved(len(self._resolved_paths))
            return
        self.query_one(StatusLine).show(
            StatusKind.SUCCESS,
            "Marcado como resuelto",
            f"{self.selected_file.path.name} ya no aparece como conflictivo",
        )
        self._refresh_view()

    def _continue_hint(self) -> str:
        """Name the command the user must run; gconflict never runs it."""
        operation = self._repo_context.operation if self._repo_context else GitOperation.NONE
        return self._CONTINUE_COMMANDS[operation]

    def _report_all_resolved(self, staged: int) -> None:
        """Announce that nothing is left and hand Git back to the user."""
        files = "archivo" if staged == 1 else "archivos"
        self.query_one(StatusLine).show(
            StatusKind.SUCCESS,
            f"Todo resuelto - {staged} {files} en el index",
            f"gconflict no hace commit: te toca {self._continue_hint()}",
        )
        self.query_one(ActionBar).set_actions([])

    def action_resolve_current(self) -> None:
        self._set_resolution(Resolution.CURRENT)

    def action_resolve_incoming(self) -> None:
        self._set_resolution(Resolution.INCOMING)

    def action_resolve_both_current_first(self) -> None:
        self._set_resolution(Resolution.BOTH_CURRENT_FIRST)

    def action_resolve_both_incoming_first(self) -> None:
        self._set_resolution(Resolution.BOTH_INCOMING_FIRST)

    def _unsupported_selected(self) -> bool:
        """Report an unsupported selection, and say what to do instead."""
        if (
            self.selected_file is not None
            and self.selected_file.conflict_type is not ConflictType.CONTENT
        ):
            title, detail = self._unsupported_message(self.selected_file.conflict_type)
            self.query_one(StatusLine).show(StatusKind.BLOCKED, title, detail)
            return True
        return False

    @staticmethod
    def _unsupported_message(conflict_type: ConflictType) -> tuple[str, str]:
        """Explain an unsupported conflict and the way out of it."""
        steps = {
            ConflictType.ADD_ADD: (
                "1 compara las dos versiones fuera - "
                "2 deja la que quieras - 3 vuelve y marca resuelto"
            ),
            ConflictType.MODIFY_DELETE: (
                "1 decide fuera entre borrado y version modificada - "
                "2 deja el resultado - 3 vuelve y marca resuelto"
            ),
            ConflictType.OTHER: (
                "1 resuelvelo con herramientas de Git - "
                "2 deja el resultado - 3 vuelve y marca resuelto"
            ),
        }[conflict_type]
        return f"Conflicto {conflict_type.value} - no soportado", steps


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
