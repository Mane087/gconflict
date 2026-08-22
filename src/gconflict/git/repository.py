"""Git repository helpers."""

from pathlib import Path

from .client import GitClient
from .index import GitIndex
from .operation import GitOperation
from gconflict.models.conflicted_file import ConflictedFile


def _confined_relative_path(root: Path, path: str | Path) -> Path:
    """Return a normalized relative path that remains within ``root``."""
    candidate = Path(path)
    if candidate.is_absolute():
        raise ValueError("Repository paths must be relative.")

    parts: list[str] = []
    for part in candidate.parts:
        if part in ("", "."):
            continue
        if part == "..":
            if not parts:
                raise ValueError("Repository path escapes the repository root.")
            parts.pop()
        else:
            parts.append(part)

    if not parts:
        raise ValueError("Repository path must identify a path within the repository.")

    relative_path = Path(*parts)
    resolved_root = root.resolve()
    resolved_candidate = (resolved_root / relative_path).resolve(strict=False)
    try:
        resolved_candidate.relative_to(resolved_root)
    except ValueError as error:
        raise ValueError(
            "Repository path resolves outside the repository root."
        ) from error
    return relative_path


class GitRepository:
    """Represent a repository resolved from a working directory."""

    def __init__(self, client: GitClient | None = None) -> None:
        self.client = client or GitClient()
        self.index = GitIndex(self.client)

    def root(self, cwd: str | Path | None = None) -> Path:
        """Return the repository root containing ``cwd``."""
        result = self.client.run(["rev-parse", "--show-toplevel"], cwd=cwd)
        return Path(result.stdout.strip())

    def current_branch(self, cwd: str | Path | None = None) -> str | None:
        """Return the checked-out branch, or None on a detached HEAD."""
        result = self.client.run(
            ["symbolic-ref", "--quiet", "--short", "HEAD"], cwd=cwd, check=False
        )
        return result.stdout.strip() or None

    def incoming_ref(self, cwd: str | Path | None = None) -> str | None:
        """Name the reference being applied by the operation in progress."""
        operation = self.operation(cwd)
        if operation is GitOperation.NONE:
            return None

        if operation is GitOperation.REBASE:
            located = self.client.run(
                ["rev-parse", "--git-path", "rebase-merge/head-name"],
                cwd=cwd,
                check=False,
            )
            head_name = Path(located.stdout.strip())
            if not head_name.is_absolute():
                head_name = (Path.cwd() if cwd is None else Path(cwd)) / head_name
            try:
                reference = head_name.read_text(encoding="utf-8").strip()
            except OSError:
                return None
            return reference.removeprefix("refs/heads/") or None

        marker = {
            GitOperation.MERGE: "MERGE_HEAD",
            GitOperation.CHERRY_PICK: "CHERRY_PICK_HEAD",
            GitOperation.REVERT: "REVERT_HEAD",
        }[operation]

        named = self.client.run(
            ["name-rev", "--name-only", "--refs=refs/heads/*", marker],
            cwd=cwd,
            check=False,
        )
        name = named.stdout.strip()
        if name and name != "undefined":
            # name-rev appends a distance suffix such as "main~3".
            return name.partition("~")[0]

        short = self.client.run(["rev-parse", "--short", marker], cwd=cwd, check=False)
        return short.stdout.strip() or None

    def conflicted_files(self, cwd: str | Path | None = None) -> list[Path]:
        """Return paths of files with unresolved merge conflicts."""
        result = self.client.run(
            ["diff", "--name-only", "--diff-filter=U"],
            cwd=cwd,
        )
        return [Path(line) for line in result.stdout.splitlines() if line]

    def conflicted_file_descriptors(
        self, cwd: str | Path | None = None
    ) -> list[ConflictedFile]:
        """Return classified descriptors for unresolved files."""
        root = self.root(cwd)
        return self.index.conflicted_file_descriptors(root)

    def stage(
        self, path: str | Path, cwd: str | Path | None = None
    ) -> None:
        """Stage ``path`` relative to its repository root."""
        root = self.root(cwd)
        relative_path = _confined_relative_path(root, path)
        self.client.run(["add", "--", str(relative_path)], cwd=root)

    def operation(self, cwd: str | Path | None = None) -> GitOperation:
        """Return the Git operation currently in progress in ``cwd``."""
        queried_cwd = Path.cwd() if cwd is None else Path(cwd)
        rebase_paths = []
        for path_name in ("rebase-merge", "rebase-apply"):
            result = self.client.run(
                ["rev-parse", "--git-path", path_name], cwd=cwd, check=False
            )
            if result.returncode == 0 and result.stdout.strip():
                path = Path(result.stdout.strip())
                rebase_paths.append(path if path.is_absolute() else queried_cwd / path)
        if any(path.exists() for path in rebase_paths):
            return GitOperation.REBASE

        for marker, operation in (
            ("CHERRY_PICK_HEAD", GitOperation.CHERRY_PICK),
            ("REVERT_HEAD", GitOperation.REVERT),
            ("MERGE_HEAD", GitOperation.MERGE),
        ):
            result = self.client.run(
                ["rev-parse", "-q", "--verify", marker], cwd=cwd, check=False
            )
            if result.returncode == 0:
                return operation
        return GitOperation.NONE
