from pathlib import Path

import pytest

from gconflict.services.editor_service import EditorService


def test_editor_precedence_and_quoted_arguments() -> None:
    calls: list[tuple[list[str], bool]] = []
    service = EditorService(
        environ={"GIT_EDITOR": 'code --profile "Git Conflicts"', "VISUAL": "zed", "EDITOR": "vim"},
        runner=lambda argv, check: calls.append((argv, check)),
    )

    assert service.open_file(Path("/repo/file name.txt"), Path("/repo")) is True
    assert calls == [
        (["code", "--profile", "Git Conflicts", "/repo/file name.txt"], False)
    ]


def test_no_configured_editor_does_not_start_a_process() -> None:
    calls: list[list[str]] = []
    service = EditorService(environ={}, runner=lambda argv, **_kwargs: calls.append(argv))

    assert service.open_file(Path("/repo/file.txt"), Path("/repo")) is False
    assert calls == []


@pytest.mark.parametrize(
    ("editor", "expected"),
    [
        ("code", ["code", "--goto", "/repo/file.txt:12"]),
        ("zed", ["zed", "/repo/file.txt:12"]),
        ("vim", ["vim", "/repo/file.txt"]),
    ],
)
def test_line_arguments_are_supported_only_for_code_and_zed(
    editor: str, expected: list[str]
) -> None:
    calls: list[list[str]] = []
    service = EditorService(
        environ={"EDITOR": editor}, runner=lambda argv, **_kwargs: calls.append(argv)
    )

    service.open_file(Path("/repo/file.txt"), Path("/repo"), line=12)

    assert calls == [expected]


@pytest.mark.parametrize(
    ("target", "root"),
    [(Path("relative.txt"), Path("/repo")), (Path("/other/file.txt"), Path("/repo"))],
)
def test_target_must_be_absolute_and_confined_to_repository(
    target: Path, root: Path
) -> None:
    service = EditorService(environ={"EDITOR": "vim"})

    with pytest.raises(ValueError):
        service.open_file(target, root)
