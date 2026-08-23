from pathlib import Path
from unittest.mock import patch
from types import SimpleNamespace
from collections.abc import Awaitable, Callable

from textual.widgets import ListView

from gconflict.ui.widgets.conflict_rail import ConflictRail

from gconflict import __version__
from gconflict.app import GConflictApp, Resolution, main
from gconflict.models.resolution import Resolution as CanonicalResolution
from gconflict.models.conflicted_file import ConflictedFile, ConflictType
from gconflict.git.operation import GitOperation
from gconflict.models.file_progress import FileProgress
from gconflict.models.repository_context import RepositoryContext
from gconflict.ui.widgets.action_bar import ActionBar
from gconflict.ui.widgets.conflict_panes import ConflictPanes
from gconflict.ui.widgets.conflict_rail import ConflictRail
from gconflict.ui.widgets.file_sidebar import FileSidebar
from gconflict.ui.widgets.repository_header import RepositoryHeader
from gconflict.ui.widgets.result_pane import ResultPane
from gconflict.ui.widgets.status_line import StatusLine


def test_package_and_entrypoint() -> None:
    assert __version__ == "0.1.0"
    assert callable(main)
    assert GConflictApp.TITLE == "gconflict"


def test_main_returns_zero_without_running_when_no_conflicts() -> None:
    service = FakeConflictService([])
    with patch("gconflict.app.ConflictService", return_value=service), patch(
        "gconflict.app.GConflictApp"
    ) as app:
        with patch("sys.argv", ["gconflict", "/workspace/subdirectory"]):
            assert main() == 0
    app.assert_not_called()


def test_main_returns_two_for_invalid_repository_without_running() -> None:
    service = FakeConflictService([])
    service.root = lambda _cwd: (_ for _ in ()).throw(ValueError())  # type: ignore[method-assign]
    with patch("gconflict.app.ConflictService", return_value=service), patch(
        "gconflict.app.GConflictApp"
    ) as app, patch("builtins.print") as printer, patch("sys.argv", ["gconflict"]):
        assert main() == 2
    printer.assert_called_once_with("Not a Git repository.")
    app.assert_not_called()


def test_main_returns_zero_for_version_without_constructing_services_or_ui(capsys) -> None:
    with patch("gconflict.app.ConflictService") as service, patch(
        "gconflict.app.GConflictApp"
    ) as app, patch("sys.argv", ["gconflict", "--version"]), patch(
        "builtins.print"
    ):
        assert main() == 0
    assert capsys.readouterr().out == "gconflict 0.1.0\n"
    assert service.call_count == 0
    app.assert_not_called()


def test_main_returns_four_for_invalid_options_without_constructing_services_or_ui() -> None:
    with patch("gconflict.app.ConflictService") as service, patch(
        "gconflict.app.GConflictApp"
    ) as app, patch("sys.argv", ["gconflict", "--invalid"]):
        assert main() == 4
    assert service.call_count == 0
    app.assert_not_called()


def test_main_runs_app_with_directory_when_conflicts_exist() -> None:
    service = FakeConflictService([Path("conflict.txt")])
    with patch("gconflict.app.ConflictService", return_value=service), patch(
        "gconflict.app.GConflictApp"
    ) as app, patch("sys.argv", ["gconflict", "/workspace/subdirectory"]):
        assert main() == 0
    app.assert_called_once_with(service=service, cwd="/workspace/subdirectory")
    app.return_value.run.assert_called_once_with()


def test_main_reconstructs_spaced_directory_for_app_cwd() -> None:
    service = FakeConflictService([Path("conflict.txt")])
    with patch("gconflict.app.ConflictService", return_value=service), patch(
        "gconflict.app.GConflictApp"
    ) as app, patch(
        "sys.argv",
        ["gconflict", "/Users/mane_alaniz/Documents/Visual", "Studio", "Code/git-merger"],
    ):
        assert main() == 0
    app.assert_called_once_with(
        service=service,
        cwd="/Users/mane_alaniz/Documents/Visual Studio Code/git-merger",
    )
    assert service.calls[0] == (
        "root",
        Path("/Users/mane_alaniz/Documents/Visual Studio Code/git-merger"),
    )


class FakeConflictService:
    def __init__(self, conflicts: list[Path | ConflictedFile]) -> None:
        self.conflicts = [
            conflict
            if isinstance(conflict, ConflictedFile)
            else ConflictedFile(conflict, ConflictType.CONTENT)
            for conflict in conflicts
        ]
        self.calls: list[tuple[str, Path | None]] = []
        self.mutation_calls: list[str] = []
        self.resolve_file_calls: list[tuple[object, list[object], list[Resolution | None]]] = []
        self.resolve_result: object = "saved snapshot"
        self.resolve_error: Exception | None = None
        self.mark_resolved_calls: list[tuple[Path, str | Path | None]] = []
        self.mark_resolved_error: Exception | None = None
        self.validated_root = Path("/validated/repository")
        self.loaded = (
            "snapshot",
            [
                SimpleNamespace(
                    current=["ours\n"],
                    incoming=["theirs\n"],
                    index=0,
                    start_line=1,
                    end_line=5,
                )
            ],
        )
        self.context_result = RepositoryContext(
            root=Path("/validated/repository"),
            name="repository",
            branch="feature/x",
            incoming_ref="main",
            operation=GitOperation.MERGE,
            current_label="ours - feature/x",
            incoming_label="theirs - main",
        )
        self.progress_result: list[FileProgress] | None = None
        self.preview_result = "preview text\n"

    def root(self, cwd: str | Path | None) -> Path:
        self.calls.append(("root", Path(cwd) if cwd is not None else None))
        return self.validated_root

    def conflicted_file_descriptors(self, root: Path) -> list[ConflictedFile]:
        self.calls.append(("conflicted_file_descriptors", root))
        return self.conflicts

    def load_conflicts(self, path: Path) -> tuple[object, list[object]]:
        self.calls.append(("load_conflicts", path))
        return self.loaded

    def context(self, cwd: str | Path | None = None) -> RepositoryContext:
        self.calls.append(("context", Path(cwd) if cwd is not None else None))
        return self.context_result

    def file_progress(self, cwd: str | Path | None = None) -> list[FileProgress]:
        self.calls.append(("file_progress", Path(cwd) if cwd is not None else None))
        if self.progress_result is not None:
            return self.progress_result
        return [FileProgress(conflict, 1) for conflict in self.conflicts]

    def preview_resolution(
        self,
        snapshot: object,
        conflicts: list[object],
        resolutions: list[Resolution | None],
        manual: object = None,
    ) -> str:
        return self.preview_result

    def resolve(self, *args: object, **kwargs: object) -> None:
        self.mutation_calls.append("resolve")
        raise AssertionError("resolve must not be called")

    def resolve_file(
        self,
        snapshot: object,
        conflicts: list[object],
        resolutions: list[Resolution | None],
    ) -> object:
        self.mutation_calls.append("resolve_file")
        self.resolve_file_calls.append((snapshot, conflicts, resolutions))
        if self.resolve_error is not None:
            raise self.resolve_error
        return self.resolve_result

    def save(self, *args: object, **kwargs: object) -> None:
        self.mutation_calls.append("save")
        raise AssertionError("save must not be called")

    def stage(self, *args: object, **kwargs: object) -> None:
        self.mutation_calls.append("stage")
        raise AssertionError("stage must not be called")

    def mark_resolved(
        self, path: Path, cwd: str | Path | None = None
    ) -> None:
        self.mutation_calls.append("mark_resolved")
        self.mark_resolved_calls.append((path, cwd))
        if self.mark_resolved_error is not None:
            raise self.mark_resolved_error


class FakeEditorService:
    def __init__(self, opened: bool = True) -> None:
        self.opened = opened
        self.calls: list[tuple[Path, Path]] = []

    def open_file(self, path: Path, repository_root: Path) -> bool:
        self.calls.append((path, repository_root))
        return self.opened


async def _mounted_widgets_for(
    conflicts: list[Path | ConflictedFile],
    assertions: Callable[[FakeConflictService, GConflictApp], Awaitable[None]],
) -> None:
    service = FakeConflictService(conflicts)
    app = GConflictApp(
        service=service,
        cwd="/Users/mane_alaniz/Documents/Visual Studio Code/git-merger",
    )
    async with app.run_test():
        await assertions(service, app)


async def test_compose_validates_root_before_listing_and_uses_validated_root() -> None:
    async def assertions(service: FakeConflictService, app: GConflictApp) -> None:
        assert service.calls[:2] == [
            (
                "context",
                Path("/Users/mane_alaniz/Documents/Visual Studio Code/git-merger"),
            ),
            (
                "file_progress",
                Path("/Users/mane_alaniz/Documents/Visual Studio Code/git-merger"),
            ),
        ]
        assert app.screen.query_one(FileSidebar).rows == ["● one.txt\n  ./\n  1 sin resolver"]

    await _mounted_widgets_for([Path("one.txt")], assertions)


async def test_compose_renders_empty_conflict_message_exactly() -> None:
    async def assertions(_service: FakeConflictService, app: GConflictApp) -> None:
        assert app.screen.query_one(FileSidebar).rows == []
        assert app.screen.query_one(ConflictRail).rendered_text == ""

    await _mounted_widgets_for([], assertions)


async def test_compose_renders_conflicts_in_order_with_header_footer_and_title() -> None:
    service = FakeConflictService([Path("first.txt"), Path("nested/second.txt")])
    app = GConflictApp(service=service, cwd="/workspace/subdirectory")
    async with app.run_test():
        assert app.screen.query_one(RepositoryHeader).rendered_text == (
            "gconflict / repository    MERGE    feature/x <- main"
        )
        assert app.screen.query_one(FileSidebar).rows == [
            "● first.txt\n  ./\n  1 sin resolver",
            "● second.txt\n  nested/\n  1 sin resolver",
        ]
        assert app.screen.query_one(ActionBar).rendered_text.startswith("CONFLICT")
        assert app.TITLE == "gconflict"


async def test_selection_updates_selected_file() -> None:
    service = FakeConflictService([Path("first.txt"), Path("nested/second.txt")])
    app = GConflictApp(service=service, cwd="/workspace/subdirectory")

    async with app.run_test() as pilot:
        assert app.selected_file is None
        await pilot.press("down")
        await pilot.press("enter")
        assert app.selected_file == ConflictedFile(
            Path("nested/second.txt"), ConflictType.CONTENT
        )
        assert service.calls[-1] == (
            "load_conflicts", Path("/validated/repository/nested/second.txt")
        )
        assert app.loaded_conflicts
        assert app.screen.query_one(ConflictRail).rendered_text.startswith("Conflict 1 / 1")
        assert app.screen.query_one(ConflictPanes).current_text == "  2 ours"
        assert app.screen.query_one(ConflictPanes).incoming_text == "  2 theirs"
        assert service.mutation_calls == []


async def test_navigation_updates_active_conflict_and_clamps_boundaries() -> None:
    service = FakeConflictService([Path("file.txt")])
    service.loaded = (
        "snapshot",
        [
            SimpleNamespace(current=["ours 1\n"], incoming=["theirs 1\n"], index=0, start_line=1, end_line=5),
            SimpleNamespace(current=["ours 2\n"], incoming=["theirs 2\n"], index=1, start_line=1, end_line=5),
        ],
    )
    app = GConflictApp(service=service, cwd="/workspace/subdirectory")

    async with app.run_test() as pilot:
        await pilot.press("enter")
        assert app.screen.query_one(ConflictRail).rendered_text.startswith("Conflict 1 / 2")
        await pilot.press("p")
        assert app.active_conflict_index == 0
        await pilot.press("n")
        assert app.active_conflict_index == 1
        assert app.screen.query_one(ConflictPanes).current_text == "  2 ours 2"
        assert app.screen.query_one(ConflictPanes).incoming_text == "  2 theirs 2"
        await pilot.press("n")
        assert app.active_conflict_index == 1
        assert service.mutation_calls == []


async def test_file_selection_resets_active_conflict_index() -> None:
    service = FakeConflictService([Path("first.txt"), Path("second.txt")])
    service.loaded = (
        "snapshot",
        [
            SimpleNamespace(current=["ours 1\n"], incoming=["theirs 1\n"], index=0, start_line=1, end_line=5),
            SimpleNamespace(current=["ours 2\n"], incoming=["theirs 2\n"], index=1, start_line=1, end_line=5),
        ],
    )
    app = GConflictApp(service=service, cwd="/workspace/subdirectory")

    async with app.run_test() as pilot:
        await pilot.press("enter")
        await pilot.press("n")
        assert app.active_conflict_index == 1
        await pilot.press("down")
        await pilot.press("enter")
        assert app.active_conflict_index == 0
        assert app.screen.query_one(ConflictRail).rendered_text.startswith("Conflict 1 / 2")


async def test_resolution_bindings_are_in_memory_and_persist_per_conflict() -> None:
    service = FakeConflictService([Path("file.txt")])
    service.loaded = ("snapshot", [
        SimpleNamespace(current=["ours 1\n"], incoming=["theirs 1\n"], index=0, start_line=1, end_line=5),
        SimpleNamespace(current=["ours 2\n"], incoming=["theirs 2\n"], index=1, start_line=1, end_line=5),
    ])
    app = GConflictApp(service=service, cwd="/workspace/subdirectory")

    async with app.run_test() as pilot:
        await pilot.press("enter")
        for key, resolution in (("c", Resolution.CURRENT), ("i", Resolution.INCOMING),
                                ("b", Resolution.BOTH_CURRENT_FIRST), ("B", Resolution.BOTH_INCOMING_FIRST)):
            await pilot.press(key)
            assert app.resolutions[0] == resolution
        await pilot.press("n")
        assert app.resolutions == [Resolution.BOTH_INCOMING_FIRST, None]
        # The rail marks conflict 1 resolved (*) and conflict 2 active (O).
        assert app.screen.query_one(ConflictRail).rendered_text == (
            "Conflict 2 / 2  ●◉  file.txt:1   [←] [→] navegar conflictos"
        )
        await pilot.press("p")
        assert app.screen.query_one(ConflictRail).rendered_text == (
            "Conflict 1 / 2  ◉○  file.txt:1   [←] [→] navegar conflictos"
        )
        assert service.mutation_calls == []


async def test_undo_restores_successive_prior_resolutions_to_none() -> None:
    service = FakeConflictService([Path("file.txt")])
    app = GConflictApp(service=service, cwd="/workspace/subdirectory")

    async with app.run_test() as pilot:
        await pilot.press("enter")
        await pilot.press("c")
        await pilot.press("i")
        await pilot.press("u")
        assert app.resolutions == [Resolution.CURRENT]
        await pilot.press("u")
        assert app.resolutions == [None]
        await pilot.press("u")
        assert app.resolutions == [None]


async def test_undo_history_is_isolated_per_conflict() -> None:
    service = FakeConflictService([Path("file.txt")])
    service.loaded = ("snapshot", [
        SimpleNamespace(current=["ours\n"], incoming=["theirs\n"], index=0, start_line=1, end_line=5),
        SimpleNamespace(current=["ours\n"], incoming=["theirs\n"], index=1, start_line=1, end_line=5),
    ])
    app = GConflictApp(service=service, cwd="/workspace/subdirectory")

    async with app.run_test() as pilot:
        await pilot.press("enter")
        await pilot.press("c")
        await pilot.press("n")
        await pilot.press("i")
        await pilot.press("u")
        assert app.resolutions == [Resolution.CURRENT, None]
        await pilot.press("p")
        await pilot.press("u")
        assert app.resolutions == [None, None]


async def test_file_selection_resets_undo_history() -> None:
    service = FakeConflictService([Path("first.txt"), Path("second.txt")])
    app = GConflictApp(service=service, cwd="/workspace/subdirectory")

    async with app.run_test() as pilot:
        await pilot.press("enter")
        await pilot.press("c")
        await pilot.press("down")
        await pilot.press("enter")
        await pilot.press("up")
        await pilot.press("enter")
        await pilot.press("u")
        assert app.resolutions == [None]
        assert service.mutation_calls == []


async def test_save_is_blocked_without_snapshot_and_preserves_state_with_feedback() -> None:
    service = FakeConflictService([Path("file.txt")])
    app = GConflictApp(service=service, cwd="/workspace/subdirectory")

    async with app.run_test() as pilot:
        initial_state = (
            app.snapshot,
            app.loaded_conflicts,
            app.resolutions,
            app._resolution_history,
            app.active_conflict_index,
        )
        await pilot.press("s")
        assert service.resolve_file_calls == []
        assert (
            app.snapshot,
            app.loaded_conflicts,
            app.resolutions,
            app._resolution_history,
            app.active_conflict_index,
        ) == initial_state
        assert app.screen.query_one(StatusLine).rendered_text == (
            "⚠ No puedes guardar todavia\n  selecciona un archivo"
        )


async def test_save_is_blocked_until_every_conflict_has_a_resolution() -> None:
    service = FakeConflictService([Path("file.txt")])
    service.loaded = (
        "snapshot",
        [
            SimpleNamespace(current=["ours 1\n"], incoming=["theirs 1\n"], index=0, start_line=1, end_line=5),
            SimpleNamespace(current=["ours 2\n"], incoming=["theirs 2\n"], index=1, start_line=1, end_line=5),
        ],
    )
    app = GConflictApp(service=service, cwd="/workspace/subdirectory")

    async with app.run_test() as pilot:
        await pilot.press("enter")
        await pilot.press("c")
        loaded_conflicts = app.loaded_conflicts
        resolutions = app.resolutions
        history = app._resolution_history
        await pilot.press("s")
        assert service.resolve_file_calls == []
        assert app.snapshot == "snapshot"
        assert app.loaded_conflicts is loaded_conflicts
        assert app.resolutions is resolutions
        assert app._resolution_history is history
        assert app.resolutions == [CanonicalResolution.CURRENT, None]
        assert app.screen.query_one(StatusLine).rendered_text == (
            "⚠ No puedes guardar todavia\n  falta 1 de 2 conflictos sin eleccion"
        )


async def test_repeated_save_after_success_is_blocked() -> None:
    service = FakeConflictService([Path("file.txt")])
    app = GConflictApp(service=service, cwd="/workspace/subdirectory")

    async with app.run_test() as pilot:
        await pilot.press("enter")
        await pilot.press("c")
        await pilot.press("s")
        await pilot.press("s")

        assert len(service.resolve_file_calls) == 1
        assert app.screen.query_one(StatusLine).rendered_text == (
            "⚠ No puedes guardar todavia\n  el archivo no tiene conflictos cargados"
        )


async def test_save_with_no_conflicts_and_no_snapshot_is_blocked() -> None:
    service = FakeConflictService([])
    app = GConflictApp(service=service, cwd="/workspace/subdirectory")

    async with app.run_test() as pilot:
        await pilot.press("s")

        assert service.resolve_file_calls == []
        assert app.screen.query_one(StatusLine).rendered_text == (
            "⚠ No puedes guardar todavia\n  selecciona un archivo"
        )


async def test_save_calls_resolve_file_with_exact_state_and_clears_only_on_success() -> None:
    service = FakeConflictService([Path("file.txt")])
    app = GConflictApp(service=service, cwd="/workspace/subdirectory")

    async with app.run_test() as pilot:
        await pilot.press("enter")
        assert app.snapshot == "snapshot"
        await pilot.press("c")
        snapshot = app.snapshot
        loaded_conflicts = app.loaded_conflicts
        resolutions = app.resolutions
        await pilot.press("s")

        assert Resolution is CanonicalResolution
        assert len(service.resolve_file_calls) == 1
        call = service.resolve_file_calls[0]
        assert call[0] is snapshot
        assert call[1] is loaded_conflicts
        assert call[2] is resolutions
        assert call[2] == [CanonicalResolution.CURRENT]
        assert app.snapshot == "saved snapshot"
        assert app.loaded_conflicts == []
        assert app.resolutions == []
        assert app._resolution_history == []
        assert app.active_conflict_index == 0
        assert app.screen.query_one(StatusLine).rendered_text == (
            "✓ Guardado - file.txt\n  1 conflictos resueltos - r para hacer git add"
        )


async def test_save_failure_preserves_all_state_and_shows_error() -> None:
    service = FakeConflictService([Path("file.txt")])
    service.resolve_error = RuntimeError("disk changed")
    app = GConflictApp(service=service, cwd="/workspace/subdirectory")

    async with app.run_test() as pilot:
        await pilot.press("enter")
        await pilot.press("c")
        snapshot = app.snapshot
        loaded_conflicts = app.loaded_conflicts
        resolutions = app.resolutions
        history = app._resolution_history
        selected_file = app.selected_file
        active_index = app.active_conflict_index
        await pilot.press("s")

        assert len(service.resolve_file_calls) == 1
        assert app.snapshot is snapshot
        assert app.loaded_conflicts is loaded_conflicts
        assert app.resolutions is resolutions
        assert app._resolution_history is history
        assert app.selected_file is selected_file
        assert app.active_conflict_index == active_index
        assert app.screen.query_one(StatusLine).rendered_text == (
            "⚠ Save fallo\n  disk changed"
        )


async def test_mark_resolved_is_blocked_until_save_succeeds() -> None:
    service = FakeConflictService([Path("file.txt")])
    service.resolve_error = RuntimeError("disk changed")
    app = GConflictApp(service=service, cwd="/workspace/subdirectory")

    async with app.run_test() as pilot:
        await pilot.press("enter")
        await pilot.press("r")
        assert service.mark_resolved_calls == []
        await pilot.press("c")
        await pilot.press("s")
        await pilot.press("r")

        assert service.mark_resolved_calls == []
        assert app.screen.query_one(StatusLine).rendered_text == (
            "⚠ Marcar resuelto bloqueado\n  guarda primero con s"
        )


async def test_mark_resolved_runs_after_successful_save() -> None:
    service = FakeConflictService([Path("file.txt")])
    app = GConflictApp(service=service, cwd="/workspace/subdirectory")

    async with app.run_test() as pilot:
        await pilot.press("enter")
        await pilot.press("c")
        await pilot.press("s")
        await pilot.press("r")

        assert service.mark_resolved_calls == [
            (Path("file.txt"), "/workspace/subdirectory")
        ]
        assert app.screen.query_one(StatusLine).rendered_text == (
            "✓ Marcado como resuelto\n  file.txt ya no aparece como conflictivo"
        )


async def test_mark_resolved_failure_shows_error_after_successful_save() -> None:
    service = FakeConflictService([Path("file.txt")])
    service.mark_resolved_error = RuntimeError("still conflicted")
    app = GConflictApp(service=service, cwd="/workspace/subdirectory")

    async with app.run_test() as pilot:
        await pilot.press("enter")
        await pilot.press("c")
        await pilot.press("s")
        await pilot.press("r")

        assert service.mark_resolved_calls == [
            (Path("file.txt"), "/workspace/subdirectory")
        ]
        assert app.screen.query_one(StatusLine).rendered_text == (
            "⚠ Marcar resuelto fallo\n  still conflicted"
        )


async def test_unsupported_conflict_blocks_loading_resolution_save_and_staging() -> None:
    descriptor = ConflictedFile(Path("file.txt"), ConflictType.ADD_ADD)
    service = FakeConflictService([descriptor])
    app = GConflictApp(service=service, cwd="/workspace/subdirectory")

    async with app.run_test() as pilot:
        await pilot.press("enter")
        await pilot.press("c")
        await pilot.press("s")
        await pilot.press("r")

        assert app.selected_file == descriptor
        assert not any(call[0] == "load_conflicts" for call in service.calls)
        assert service.mutation_calls == []
        assert app.screen.query_one(StatusLine).rendered_text == (
            "⚠ Conflicto add_add - no soportado\n"
            "  1 compara las dos versiones fuera - "
            "2 deja la que quieras - 3 vuelve y marca resuelto"
        )


async def test_switching_from_content_to_unsupported_clears_content_and_shows_guidance() -> None:
    descriptors = [
        ConflictedFile(Path("content.txt"), ConflictType.CONTENT),
        ConflictedFile(Path("file.txt"), ConflictType.MODIFY_DELETE),
    ]
    service = FakeConflictService(descriptors)
    app = GConflictApp(service=service, cwd="/workspace/subdirectory")

    async with app.run_test() as pilot:
        await pilot.press("enter")
        assert app.screen.query_one(ConflictPanes).current_text == "  2 ours"
        await pilot.press("down")
        await pilot.press("enter")

        assert app.screen.query_one(StatusLine).rendered_text == (
            "⚠ Conflicto modify_delete - no soportado\n"
            "  1 decide fuera entre borrado y version modificada - "
            "2 deja el resultado - 3 vuelve y marca resuelto"
        )
        assert app.screen.query_one(ConflictPanes).current_text == ""
        assert app.screen.query_one(ConflictPanes).incoming_text == ""
        assert service.mutation_calls == []


async def test_edit_content_runs_editor_and_reloads_without_mutating_repository() -> None:
    service = FakeConflictService([Path("file.txt")])
    editor = FakeEditorService()
    app = GConflictApp(
        service=service, editor_service=editor, cwd="/workspace/subdirectory"
    )

    async with app.run_test() as pilot:
        await pilot.press("enter")
        await pilot.press("c")
        service.loaded = (
            "reloaded snapshot",
            [SimpleNamespace(current=["edited ours\n"], incoming=["edited theirs\n"], index=0, start_line=1, end_line=5)],
        )
        await pilot.press("e")
        await pilot.pause()

        assert editor.calls == [
            (Path("/validated/repository/file.txt"), Path("/validated/repository"))
        ]
        assert app.snapshot == "reloaded snapshot"
        assert app.resolutions == [None]
        assert app._resolution_history == [[]]
        assert app.active_conflict_index == 0
        assert app._save_succeeded is False
        assert app.screen.query_one(ConflictPanes).current_text == (
            "  2 edited ours"
        )
        assert service.mutation_calls == []


async def test_edit_content_with_no_conflicts_clears_stale_content() -> None:
    service = FakeConflictService([Path("file.txt")])
    editor = FakeEditorService()
    app = GConflictApp(
        service=service, editor_service=editor, cwd="/workspace/subdirectory"
    )

    async with app.run_test() as pilot:
        await pilot.press("enter")
        service.loaded = ("reloaded snapshot", [])
        await pilot.press("e")
        await pilot.pause()

        assert app.loaded_conflicts == []
        assert app.screen.query_one(ConflictRail).rendered_text == ""
        assert app.screen.query_one(ConflictPanes).current_text == ""
        assert app.screen.query_one(ConflictPanes).incoming_text == ""
        assert app._save_succeeded is False
        assert service.mutation_calls == []


async def test_edit_unsupported_runs_editor_and_rebuilds_unsupported_state() -> None:
    descriptor = ConflictedFile(Path("file.txt"), ConflictType.ADD_ADD)
    service = FakeConflictService([descriptor])
    editor = FakeEditorService()
    app = GConflictApp(
        service=service, editor_service=editor, cwd="/workspace/subdirectory"
    )

    async with app.run_test() as pilot:
        await pilot.press("enter")
        await pilot.press("e")
        await pilot.pause()

        assert editor.calls == [
            (Path("/validated/repository/file.txt"), Path("/validated/repository"))
        ]
        assert app.snapshot is None
        assert app.loaded_conflicts == []
        assert app.resolutions == []
        assert app.screen.query_one(StatusLine).rendered_text == (
            "⚠ Conflicto add_add - no soportado\n"
            "  1 compara las dos versiones fuera - "
            "2 deja la que quieras - 3 vuelve y marca resuelto"
        )
        assert service.mutation_calls == []


async def test_edit_with_no_editor_does_not_reload_or_mutate() -> None:
    service = FakeConflictService([Path("file.txt")])
    editor = FakeEditorService(opened=False)
    app = GConflictApp(
        service=service, editor_service=editor, cwd="/workspace/subdirectory"
    )

    async with app.run_test() as pilot:
        await pilot.press("enter")
        load_calls = [call for call in service.calls if call[0] == "load_conflicts"]
        await pilot.press("e")
        await pilot.pause()

        assert len([call for call in service.calls if call[0] == "load_conflicts"]) == len(load_calls)
        assert app.screen.query_one(StatusLine).rendered_text == (
            "⚠ No encontre un editor\n  define GIT_EDITOR, VISUAL o EDITOR"
        )
        assert service.mutation_calls == []


async def test_unsupported_file_explains_itself_and_keeps_only_the_editor() -> None:
    service = FakeConflictService(
        [ConflictedFile(Path("priv/logo.png"), ConflictType.ADD_ADD)]
    )
    app = GConflictApp(service=service, cwd="/workspace/subdirectory")

    async with app.run_test() as pilot:
        await pilot.press("enter")
        assert app.screen.query_one(StatusLine).rendered_text == (
            "⚠ Conflicto add_add - no soportado\n"
            "  1 compara las dos versiones fuera - "
            "2 deja la que quieras - 3 vuelve y marca resuelto"
        )
        bar = app.screen.query_one(ActionBar).rendered_text
        assert " e  Editor externo " in bar
        assert " s  Save  tipo de conflicto no soportado" in bar
        assert app.screen.query_one(ConflictPanes).current_text == ""
        assert app.screen.query_one(ConflictRail).rendered_text == ""
        assert service.mutation_calls == []


async def test_unsupported_file_blocks_every_resolution_key() -> None:
    service = FakeConflictService(
        [ConflictedFile(Path("priv/logo.png"), ConflictType.MODIFY_DELETE)]
    )
    app = GConflictApp(service=service, cwd="/workspace/subdirectory")

    async with app.run_test() as pilot:
        await pilot.press("enter")
        for key in ("c", "i", "b", "B", "s", "r"):
            await pilot.press(key)
        assert app.resolutions == []
        assert service.mutation_calls == []


async def test_last_resolved_file_reports_the_users_next_step() -> None:
    service = FakeConflictService([Path("lib/user.ex")])
    app = GConflictApp(service=service, cwd="/workspace/subdirectory")

    async with app.run_test() as pilot:
        await pilot.press("enter")
        await pilot.press("c")
        await pilot.press("s")
        service.progress_result = []
        await pilot.press("r")
        assert app.screen.query_one(StatusLine).rendered_text == (
            "✓ Todo resuelto - 1 archivo en el index\n"
            "  gconflict no hace commit: te toca git merge --continue"
        )
        assert app.screen.query_one(ActionBar).rendered_text == ""
        assert service.mark_resolved_calls == [
            (Path("lib/user.ex"), "/workspace/subdirectory")
        ]


async def test_continue_hint_follows_the_operation() -> None:
    service = FakeConflictService([Path("lib/user.ex")])
    service.context_result = RepositoryContext(
        root=Path("/validated/repository"),
        name="repository",
        branch="feature/x",
        incoming_ref="main",
        operation=GitOperation.REBASE,
        current_label="rebased base",
        incoming_label="commit being applied",
    )
    app = GConflictApp(service=service, cwd="/workspace/subdirectory")

    async with app.run_test():
        assert app._continue_hint() == "git rebase --continue"


async def test_selecting_a_stale_row_after_the_file_list_shrinks_does_not_crash() -> None:
    """ListView.clear() removes deferred, so old rows outlive a shrinking refresh."""
    service = FakeConflictService([Path("first.txt"), Path("second.txt")])
    app = GConflictApp(service=service, cwd="/workspace/subdirectory")

    async with app.run_test() as pilot:
        sidebar = app.screen.query_one(FileSidebar)
        stale = sidebar.item_ids[1]
        service.progress_result = [
            FileProgress(ConflictedFile(Path("first.txt"), ConflictType.CONTENT), 1)
        ]
        app._progress = service.file_progress(app.cwd)
        app._conflicted_files = [item.file for item in app._progress]
        app._refresh_view()

        listing = sidebar.query_one(ListView)
        listing.post_message(ListView.Selected(listing, listing.children[1], 1))
        await pilot.pause()

        assert app.selected_file is None
        assert service.mutation_calls == []
        assert sidebar.entry_for(stale) is None
