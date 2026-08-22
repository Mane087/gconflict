from pathlib import Path
from unittest.mock import patch
from types import SimpleNamespace
from collections.abc import Awaitable, Callable

from textual.widgets import Footer, Header, Label, ListView

from gconflict import __version__
from gconflict.app import GConflictApp, Resolution, main
from gconflict.models.resolution import Resolution as CanonicalResolution
from gconflict.models.conflicted_file import ConflictedFile, ConflictType


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
            [SimpleNamespace(current=["ours\n"], incoming=["theirs\n"])],
        )

    def root(self, cwd: str | Path | None) -> Path:
        self.calls.append(("root", Path(cwd) if cwd is not None else None))
        return self.validated_root

    def conflicted_file_descriptors(self, root: Path) -> list[ConflictedFile]:
        self.calls.append(("conflicted_file_descriptors", root))
        return self.conflicts

    def load_conflicts(self, path: Path) -> tuple[object, list[object]]:
        self.calls.append(("load_conflicts", path))
        return self.loaded

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
        assert service.calls == [
            (
                "root",
                Path("/Users/mane_alaniz/Documents/Visual Studio Code/git-merger"),
            ),
            ("conflicted_file_descriptors", Path("/validated/repository")),
        ]
        listing = app.screen.query_one(ListView)
        assert [item.query_one(Label).render().plain for item in listing.children] == ["one.txt"]

    await _mounted_widgets_for([Path("one.txt")], assertions)


async def test_compose_renders_empty_conflict_message_exactly() -> None:
    async def assertions(_service: FakeConflictService, app: GConflictApp) -> None:
        assert app.screen.query_one(Label).render().plain == "No unresolved Git conflicts found."

    await _mounted_widgets_for([], assertions)


async def test_compose_renders_conflicts_in_order_with_header_footer_and_title() -> None:
    service = FakeConflictService([Path("first.txt"), Path("nested/second.txt")])
    app = GConflictApp(service=service, cwd="/workspace/subdirectory")
    async with app.run_test():
        assert app.screen.query_one(Header)
        listing = app.screen.query_one(ListView)
        assert [item.query_one(Label).render().plain for item in listing.children] == [
            "first.txt", "nested/second.txt"]
        assert app.screen.query_one(Footer)
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
        assert app.screen.query_one("#conflict-count", Label).render().plain == "Conflict 1 / 1 — UNRESOLVED"
        assert app.screen.query_one("#current", Label).render().plain == "CURRENT\nours\n"
        assert app.screen.query_one("#incoming", Label).render().plain == "INCOMING\ntheirs\n"
        assert service.mutation_calls == []


async def test_navigation_updates_active_conflict_and_clamps_boundaries() -> None:
    service = FakeConflictService([Path("file.txt")])
    service.loaded = (
        "snapshot",
        [
            SimpleNamespace(current=["ours 1\n"], incoming=["theirs 1\n"]),
            SimpleNamespace(current=["ours 2\n"], incoming=["theirs 2\n"]),
        ],
    )
    app = GConflictApp(service=service, cwd="/workspace/subdirectory")

    async with app.run_test() as pilot:
        await pilot.press("enter")
        assert app.screen.query_one("#conflict-count", Label).render().plain == "Conflict 1 / 2 — UNRESOLVED"
        await pilot.press("p")
        assert app.active_conflict_index == 0
        await pilot.press("n")
        assert app.active_conflict_index == 1
        assert app.screen.query_one("#current", Label).render().plain == "CURRENT\nours 2\n"
        assert app.screen.query_one("#incoming", Label).render().plain == "INCOMING\ntheirs 2\n"
        await pilot.press("n")
        assert app.active_conflict_index == 1
        assert service.mutation_calls == []


async def test_file_selection_resets_active_conflict_index() -> None:
    service = FakeConflictService([Path("first.txt"), Path("second.txt")])
    service.loaded = (
        "snapshot",
        [
            SimpleNamespace(current=["ours 1\n"], incoming=["theirs 1\n"]),
            SimpleNamespace(current=["ours 2\n"], incoming=["theirs 2\n"]),
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
        assert app.screen.query_one("#conflict-count", Label).render().plain == "Conflict 1 / 2 — UNRESOLVED"


async def test_resolution_bindings_are_in_memory_and_persist_per_conflict() -> None:
    service = FakeConflictService([Path("file.txt")])
    service.loaded = ("snapshot", [
        SimpleNamespace(current=["ours 1\n"], incoming=["theirs 1\n"]),
        SimpleNamespace(current=["ours 2\n"], incoming=["theirs 2\n"]),
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
        assert "UNRESOLVED" in app.screen.query_one("#conflict-count", Label).render().plain
        await pilot.press("p")
        assert "RESOLVED" in app.screen.query_one("#conflict-count", Label).render().plain
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
        SimpleNamespace(current=["ours\n"], incoming=["theirs\n"]),
        SimpleNamespace(current=["ours\n"], incoming=["theirs\n"]),
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
        assert app.screen.query_one("#conflict-count", Label).render().plain == (
            "Save blocked: no loaded snapshot."
        )


async def test_save_is_blocked_until_every_conflict_has_a_resolution() -> None:
    service = FakeConflictService([Path("file.txt")])
    service.loaded = (
        "snapshot",
        [
            SimpleNamespace(current=["ours 1\n"], incoming=["theirs 1\n"]),
            SimpleNamespace(current=["ours 2\n"], incoming=["theirs 2\n"]),
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
        assert app.screen.query_one("#conflict-count", Label).render().plain == (
            "Save blocked: resolve all conflicts before saving."
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
        assert app.screen.query_one("#conflict-count", Label).render().plain == (
            "Save blocked: no loaded conflicts."
        )


async def test_save_with_no_conflicts_and_no_snapshot_is_blocked() -> None:
    service = FakeConflictService([])
    app = GConflictApp(service=service, cwd="/workspace/subdirectory")

    async with app.run_test() as pilot:
        await pilot.press("s")

        assert service.resolve_file_calls == []
        assert app.screen.query_one("#conflict-count", Label).render().plain == (
            "Save blocked: no loaded snapshot."
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
        assert app.screen.query_one("#conflict-count", Label).render().plain == (
            "Saved successfully."
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
        assert app.screen.query_one("#conflict-count", Label).render().plain == (
            "Save failed: disk changed"
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
        assert app.screen.query_one("#conflict-count", Label).render().plain == (
            "Mark resolved blocked: save successfully first."
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
        assert app.screen.query_one("#conflict-count", Label).render().plain == (
            "Marked resolved successfully."
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
        assert app.screen.query_one("#conflict-count", Label).render().plain == (
            "Mark resolved failed: still conflicted"
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
        assert app.screen.query_one("#conflict-count", Label).render().plain == (
            f"Unsupported conflict type: {ConflictType.ADD_ADD.value}\n"
            "Compare/combine externally."
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
        assert app.screen.query_one("#current", Label).render().plain == "CURRENT\nours\n"
        await pilot.press("down")
        await pilot.press("enter")

        assert app.screen.query_one("#conflict-count", Label).render().plain == (
            f"Unsupported conflict type: {ConflictType.MODIFY_DELETE.value}\n"
            "Choose deletion or the modified version externally."
        )
        assert app.screen.query_one("#current", Label).render().plain == ""
        assert app.screen.query_one("#incoming", Label).render().plain == ""
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
            [SimpleNamespace(current=["edited ours\n"], incoming=["edited theirs\n"])],
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
        assert app.screen.query_one("#current", Label).render().plain == (
            "CURRENT\nedited ours\n"
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
        assert app.screen.query_one("#conflict-count", Label).render().plain == (
            "Conflict 0 / 0 — UNRESOLVED"
        )
        assert app.screen.query_one("#current", Label).render().plain == ""
        assert app.screen.query_one("#incoming", Label).render().plain == ""
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
        assert app.screen.query_one("#conflict-count", Label).render().plain == (
            f"Unsupported conflict type: {ConflictType.ADD_ADD.value}\n"
            "Compare/combine externally."
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
        assert app.screen.query_one("#conflict-count", Label).render().plain == (
            "No editor configured. Set GIT_EDITOR, VISUAL, or EDITOR."
        )
        assert service.mutation_calls == []
