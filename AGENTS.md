# AGENTS.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

`gconflict` — a Textual TUI that resolves Git merge conflicts. Python 3.13+, `src/` layout,
single runtime dependency (`textual`). `plan.md` (Spanish, ~2700 lines) is the authoritative
spec: it holds the numbered business rules (`RN-001`…`RN-025`), the layer design, and the
iteration order. Consult it before changing behavior — most design questions are already
answered there.

## Commands

The project is installed editable into `.venv/` (Python 3.14). Use that interpreter directly;
the venv is not auto-activated.

```bash
.venv/bin/python -m pip install -e ".[dev]"   # setup / re-sync
.venv/bin/python -m pytest -q --asyncio-mode=auto            # full suite (117 tests)
.venv/bin/python -m pytest tests/git/test_repository.py -q --asyncio-mode=auto
.venv/bin/python -m pytest -q --asyncio-mode=auto -k test_save_calls_resolve_file   # single test
.venv/bin/python -m pytest --cov=gconflict --asyncio-mode=auto
.venv/bin/gconflict [directory]               # run the TUI
```

`--asyncio-mode=auto` is mandatory. `tests/test_app.py` uses bare `async def` tests driven by
Textual's `app.run_test()` pilot, and neither `pyproject.toml` nor a `conftest.py` sets
`asyncio_mode`. Without the flag those 25 tests fail with "async def functions are not natively
supported" — that is a config gap, not a regression. `pytest-asyncio` is also installed but not
declared in the `dev` extra.

There is no linter, formatter, or type checker configured. This directory is not itself a Git
repository (`git init` has never been run here).

## Architecture

Layers, strictly one-directional (`app → services → {git, conflicts, filesystem} → models`):

- `models/` — pure dataclasses/enums: `Conflict` (current/incoming/base + 1-based
  `start_line`/`end_line`), `Resolution`, `ConflictedFile`/`ConflictType`, `GitOperation`.
- `git/` — `GitClient` runs `subprocess.run(["git", ...])` and returns `GitResult`;
  `GitIndex` parses `git ls-files -u` and classifies a path's stage set into a `ConflictType`;
  `GitRepository` composes both and owns `_confined_relative_path`, the path-containment guard.
- `conflicts/` — the resolution engine, all pure functions: `parse_conflicts` (text → list of
  `Conflict`), `resolve_conflict` (conflict + `Resolution` → resolved lines),
  `reconstruct_text` (original text + conflicts + resolved lines → new text).
- `filesystem/snapshot.py` — `load_text_file`/`save_text_file`. A `TextFileSnapshot` carries a
  sha256 of the raw bytes; saving re-reads the file, compares the hash, and refuses with
  `ConcurrentModificationError` if it changed, then writes via temp-file + `os.replace`,
  preserving BOM and mode. Rejects symlinks and non-regular files. The module docstring
  documents the residual TOCTOU window — do not claim it is closed.
- `services/` — `ConflictService` is the only seam the UI talks to (root discovery, descriptor
  listing, `load_conflicts`, `resolve_file`, `mark_resolved`). `EditorService` builds an argv
  from `GIT_EDITOR` → `VISUAL` → `EDITOR` via `shlex.split`, verifies the target is inside the
  repo root, and adds `--goto file:line` for `code`/`zed`.
- `app.py` — `GConflictApp` plus `main()`. The app holds all conflict state in memory
  (`loaded_conflicts`, `resolutions`, `_resolution_history`, `snapshot`) and never touches Git
  or the filesystem except through the two injected services.

Both services are constructor-injected and defaulted (`service or ConflictService()`), which is
how every test substitutes a fake.

## Invariants

These come from `plan.md` and are enforced by tests — breaking one breaks the product's
contract, not just a test:

- **Git is the source of truth.** No parallel model of the repository; query Git each time.
  Never reimplement staging, index reading, or merge logic.
- **Never `shell=True`,** and always pass `--` before user paths in Git argv.
- **Resolutions are literal.** `BOTH_CURRENT_FIRST` concatenates current then incoming, byte for
  byte. No deduplication, reordering, or semantic interpretation of code, ever.
- **Nothing outside a conflict's marker range may change.** Line endings, whitespace, BOM, and
  file mode are preserved through the save round-trip.
- **No automatic mutation.** The app never commits, never runs `--continue`/`--abort`, and never
  stages implicitly. `s` (save to disk) and `r` (`git add`) are separate, explicit actions, and
  `r` is blocked until a save succeeded (`_save_succeeded`). `mark_resolved` additionally
  verifies no markers remain, that Git still reports the file conflicted, and that Git stops
  reporting it afterward.
- **Fail safe.** Anything not confidently understood is left untouched. Only `ConflictType.CONTENT`
  is resolvable; `ADD_ADD`, `MODIFY_DELETE`, and `OTHER` render guidance and block every mutating
  action (`_unsupported_selected`). diff3/zdiff3 markers raise rather than being parsed.
- **UI says CURRENT/INCOMING, never ours/theirs** — the mapping depends on the in-progress
  operation (`GitOperation`), so `ours == current branch` must not be assumed.

## Conventions

- Tests mirror the source tree (`tests/git/test_repository.py` ↔ `src/gconflict/git/repository.py`).
  Hand-written fakes (`FakeConflictService`, `FakeEditorService`) that record a `calls` list are
  preferred over `unittest.mock` for the service seam; `Mock()` is used for `GitClient`.
  `tmp_path` + a real `git init` is used where Git behavior itself is under test.
- Assertions are exact: full rendered label strings, whole `call_args_list` sequences, and
  `service.mutation_calls == []` to prove read-only paths stayed read-only. Match that precision.
- CLI exit codes are fixed: `0` success/no conflicts, `2` not a Git repository, `4` bad arguments.
  `--version`/`--help` must return before any service or UI object is constructed.
- `main()` accepts the directory as `nargs="*"` and rejoins it with spaces, so unquoted paths
  containing spaces work (this repo's own path has two). Keep that behavior.
- Docstrings are one-line and imperative; comments are rare and explain *why*. README and
  `plan.md` are in Spanish; code, identifiers, and docstrings are in English.