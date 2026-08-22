"""Small subprocess wrapper for Git commands."""

from dataclasses import dataclass
from pathlib import Path
import subprocess
from typing import Sequence


@dataclass(frozen=True)
class GitResult:
    """Result returned by a Git command."""

    stdout: str
    stderr: str
    returncode: int


class GitClient:
    """Run Git commands without invoking a shell."""

    def run(
        self,
        args: Sequence[str],
        *,
        cwd: str | Path | None = None,
        check: bool = True,
    ) -> GitResult:
        """Run ``git`` with the supplied arguments."""
        completed = subprocess.run(
            ["git", *args],
            cwd=cwd,
            capture_output=True,
            text=True,
            check=False,
        )
        result = GitResult(completed.stdout, completed.stderr, completed.returncode)
        if check and result.returncode:
            raise RuntimeError(result.stderr or result.stdout)
        return result
