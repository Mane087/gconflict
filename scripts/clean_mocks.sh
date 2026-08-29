#!/bin/sh
#
# Elimina el entorno de pruebas creado por mock_test.sh.
#
# Quita el worktree mock (por ruta y por cualquier worktree registrado sobre
# las ramas mock), ejecuta git worktree prune y borra las ramas mock/test_one
# y mock/test_two. Es idempotente: si no hay nada que limpiar, no falla.

set -eu

BRANCH_ONE="mock/test_one"
BRANCH_TWO="mock/test_two"


# ---------------------------------------------------------------------------
# Output helpers
# ---------------------------------------------------------------------------

log() {
    printf '%s\n' "$*"
}

die() {
    printf 'error: %s\n' "$*" >&2
    exit 1
}


# ---------------------------------------------------------------------------
# Prerequisites
# ---------------------------------------------------------------------------

command -v git >/dev/null 2>&1 || die "Git es requerido."

SCRIPT_DIR="$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)"

REPO_ROOT="$(git -C "$SCRIPT_DIR" rev-parse --show-toplevel 2>/dev/null || true)"
[ -n "$REPO_ROOT" ] || die "El script debe ejecutarse dentro de un repositorio Git."

MOCK_DIR="${GCONFLICT_MOCK_DIR:-$(dirname -- "$REPO_ROOT")/gconflict-mock}"

git_repo() {
    git -C "$REPO_ROOT" "$@"
}


# ---------------------------------------------------------------------------
# Limpieza
# ---------------------------------------------------------------------------

remove_worktree_of_branch() {
    branch="$1"
    git_repo worktree list --porcelain \
        | awk -v branch="refs/heads/$branch" '
            /^worktree /  { path = substr($0, 10) }
            /^branch /    { if (substr($0, 8) == branch) print path }
        ' \
        | while IFS= read -r path; do
            [ -n "$path" ] || continue
            log "  worktree: $path"
            git_repo worktree remove --force "$path" >/dev/null 2>&1 || rm -rf "$path"
        done
}

delete_branch() {
    branch="$1"
    if git_repo show-ref --verify --quiet "refs/heads/$branch"; then
        log "  rama: $branch"
        git_repo branch -D "$branch" >/dev/null
    fi
}

log "Limpiando entorno mock..."

if [ -e "$MOCK_DIR" ]; then
    log "  worktree: $MOCK_DIR"
    git_repo worktree remove --force "$MOCK_DIR" >/dev/null 2>&1 || true
    rm -rf "$MOCK_DIR"
fi

remove_worktree_of_branch "$BRANCH_ONE"
remove_worktree_of_branch "$BRANCH_TWO"

git_repo worktree prune

delete_branch "$BRANCH_ONE"
delete_branch "$BRANCH_TWO"

log "Entorno mock eliminado."
