"""Safely launch a configured editor for a conflicted file."""

from __future__ import annotations

import os
import shlex
import subprocess
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Any


Runner = Callable[..., Any]


class EditorService:
    """Open repository files without invoking a command shell."""

    def __init__(
        self,
        environ: Mapping[str, str] | None = None,
        runner: Runner = subprocess.run,
    ) -> None:
        self.environ = os.environ if environ is None else environ
        self.runner = runner

    def editor_argv(self) -> list[str]:
        """Return the first configured editor as an argument vector."""
        for variable in ("GIT_EDITOR", "VISUAL", "EDITOR"):
            value = self.environ.get(variable, "").strip()
            if value:
                return shlex.split(value)
        return []

    def open_file(
        self,
        path: str | Path,
        repository_root: str | Path,
        line: int | None = None,
    ) -> bool:
        """Open an absolute repository file, returning false if no editor is set."""
        editor = self.editor_argv()
        if not editor:
            return False

        root = Path(repository_root)
        target = Path(path)
        if not root.is_absolute() or not target.is_absolute():
            raise ValueError("Editor paths must be absolute.")

        resolved_root = root.resolve()
        resolved_target = target.resolve()
        try:
            resolved_target.relative_to(resolved_root)
        except ValueError as error:
            raise ValueError("Editor target must be inside the repository.") from error

        argv: list[str] = list(editor)
        executable = Path(editor[0]).name.lower()
        if line is not None and line > 0 and executable in {"code", "zed"}:
            if executable == "code":
                argv.extend(("--goto", f"{resolved_target}:{line}"))
            else:
                argv.append(f"{resolved_target}:{line}")
        else:
            argv.append(str(resolved_target))

        self.runner(argv, check=False)
        return True
