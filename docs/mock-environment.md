# Mock environment for testing the TUI

`scripts/mock_test.sh` builds a throwaway repository state with real merge
conflicts so you can exercise the gconflict interface without touching your own
work. `scripts/clean_mocks.sh` removes it.

Both scripts are POSIX `sh` and only need Git.

## What the environment looks like

The environment lives in a separate Git worktree, by default a sibling of the
repository root:

```
Documentos/Projects/
├── gconflict/        # this repository, untouched
└── gconflict-mock/   # the worktree with the conflicted merge
```

Inside that worktree the script creates two branches from a common root commit:

| Branch          | Role in the TUI     |
| --------------- | ------------------- |
| `mock/test_one` | CURRENT (`ours`)    |
| `mock/test_two` | INCOMING (`theirs`) |

Both branches contain the same five files with different content, and the
script leaves `git merge mock/test_two` stopped with conflicts in all of them:

| File                   | Conflicts | Purpose                                       |
| ---------------------- | --------- | --------------------------------------------- |
| `src/auth.py`          | 2         | Several small conflicts in one file           |
| `src/huge_module.py`   | 1         | 240 lines per side, to test scrolling         |
| `config/settings.json` | 1         | Single short conflict                         |
| `docs/README.md`       | 2         | Conflicts separated by untouched context      |
| `styles/theme.css`     | 2         | Medium-sized conflicts                        |

The conflict in `src/huge_module.py` is the one that exercises the scroll in the
three sections: CURRENT and INCOMING hold 240 lines each, and RESULT
reconstructs a file of roughly 260 lines.

## Step by step

### 1. Create the environment

From the repository root:

```bash
sh scripts/mock_test.sh
```

The script:

1. Removes any previous mock environment (worktree and both branches). This
   runs first, so re-running the script always starts from a clean state.
2. Creates a root commit with an empty tree, so the mock worktree does not carry
   the files of this repository.
3. Commits the base version of the five files, branches `mock/test_two` from it,
   and commits a different version of the same files on each branch.
4. Merges `mock/test_two` into `mock/test_one` and leaves the merge stopped.

On success it prints the conflicted files and the command to launch the TUI.

### 2. Check that the interface is running your code

`.venv/bin/gconflict` runs whatever copy of the package is installed in the
virtual environment. If it is a regular (non-editable) install, your local
changes under `src/` are **not** what you see on screen.

Verify which copy is imported:

```bash
.venv/bin/python -c "import gconflict; print(gconflict.__file__)"
```

- A path under `src/gconflict/` means the editable install is in place.
- A path under `.venv/lib/.../site-packages/gconflict/` means you are running an
  installed snapshot. Reinstall in editable mode:

  ```bash
  .venv/bin/python -m pip install -e ".[dev]"
  ```

  Or run from the source tree without reinstalling:

  ```bash
  PYTHONPATH=src .venv/bin/python -c "from gconflict.app import main; main()" ../gconflict-mock
  ```

### 3. Open the TUI on the mock environment

```bash
.venv/bin/gconflict ../gconflict-mock
```

The sidebar lists the five conflicted files.

### 4. Remove the environment

```bash
sh scripts/clean_mocks.sh
```

This removes the mock worktree, prunes stale worktree registrations, and deletes
`mock/test_one` and `mock/test_two`. It is idempotent: running it when there is
nothing to clean is not an error.

`sh scripts/mock_test.sh --clean` does the same thing; it delegates to
`clean_mocks.sh`.

### Resetting after resolving files

Saving (`s`) and marking a file as resolved (`r`) in the TUI writes to the mock
worktree and stages the file, so it stops being reported as conflicted. To get
all five conflicts back, run `sh scripts/mock_test.sh` again: it rebuilds the
environment from scratch.

## Options

| Variable            | Default                          | Effect                                  |
| ------------------- | -------------------------------- | --------------------------------------- |
| `GCONFLICT_MOCK_DIR`| `<parent of repo>/gconflict-mock`| Where the mock worktree is created      |

Both scripts read the same variable, so if you create the environment somewhere
else, pass the same value when cleaning it:

```bash
GCONFLICT_MOCK_DIR=/tmp/gconflict-mock sh scripts/mock_test.sh
GCONFLICT_MOCK_DIR=/tmp/gconflict-mock sh scripts/clean_mocks.sh
```

## Verifying the state by hand

```bash
git worktree list                                  # the mock worktree is listed
git branch --list 'mock/*'                         # both branches exist
git -C ../gconflict-mock status --short            # five files reported as UU
git -C ../gconflict-mock grep -c '^<<<<<<<' -- .   # conflicts per file
```

## Notes

- The scripts only add two branches and one worktree to this repository. The
  main working tree, its branch, and its uncommitted changes are left alone.
- Commits in the mock environment are authored as `gconflict mock
  <mock@gconflict.local>`, set through `GIT_AUTHOR_*` and `GIT_COMMITTER_*`, so
  your Git identity is not used.
- Resolving conflicts inside the mock worktree is safe: nothing is pushed, and
  `clean_mocks.sh` discards the whole environment.
