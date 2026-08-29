#!/bin/sh
#
# Crea un entorno de pruebas para la TUI de gconflict.
#
# El script construye dos ramas (mock/test_one y mock/test_two) con los mismos
# cinco archivos y contenido distinto, las fusiona dentro de un worktree Git
# aislado y deja el merge detenido con conflictos. El worktree resultante es el
# directorio que se le pasa a gconflict.
#
# El repositorio principal no se modifica: solo se agregan las dos ramas y un
# worktree fuera del arbol de trabajo actual.

set -eu

BRANCH_ONE="mock/test_one"
BRANCH_TWO="mock/test_two"

HUGE_ENTRIES=240

export GIT_AUTHOR_NAME="gconflict mock"
export GIT_AUTHOR_EMAIL="mock@gconflict.local"
export GIT_COMMITTER_NAME="gconflict mock"
export GIT_COMMITTER_EMAIL="mock@gconflict.local"


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

git_mock() {
    git -C "$MOCK_DIR" "$@"
}


# ---------------------------------------------------------------------------
# Cleanup: eliminar worktree y ramas mock previas
# ---------------------------------------------------------------------------

CLEAN_SCRIPT="$SCRIPT_DIR/clean_mocks.sh"
[ -f "$CLEAN_SCRIPT" ] || die "No se encontro $CLEAN_SCRIPT."

GCONFLICT_MOCK_DIR="$MOCK_DIR" sh "$CLEAN_SCRIPT"

if [ "${1:-}" = "--clean" ]; then
    exit 0
fi

if [ -n "${1:-}" ]; then
    die "Argumento no reconocido: $1 (uso: mock_test.sh [--clean])"
fi


# ---------------------------------------------------------------------------
# Contenido de los archivos
#
# Cada funcion escribe una de las tres variantes del archivo:
#   base     -> ancestro comun de las dos ramas
#   current  -> mock/test_one, el lado CURRENT del conflicto
#   incoming -> mock/test_two, el lado INCOMING del conflicto
# ---------------------------------------------------------------------------

write_auth() {
    file="$MOCK_DIR/src/auth.py"
    case "$1" in
        base)
            cat > "$file" <<'EOF'
"""Autenticacion de usuarios."""

SESSION_TTL = 3600


def authenticate(username, password):
    user = find_user(username)
    if user is None:
        return None
    if user.password != password:
        return None
    return create_session(user)
EOF
            ;;
        current)
            cat > "$file" <<'EOF'
"""Autenticacion de usuarios."""

SESSION_TTL = 7200


def authenticate(username, password):
    user = find_user(username)
    if user is None:
        raise UserNotFoundError(username)
    if not verify_hash(user.password_hash, password):
        raise InvalidCredentialsError(username)
    return create_session(user, ttl=SESSION_TTL)
EOF
            ;;
        incoming)
            cat > "$file" <<'EOF'
"""Autenticacion de usuarios."""

SESSION_TTL = 1800


def authenticate(username, password, *, mfa_token=None):
    user = find_user(username)
    if user is None:
        return None
    if not check_password(user, password):
        return None
    if user.mfa_enabled and not check_mfa(user, mfa_token):
        return None
    return create_session(user)
EOF
            ;;
    esac
}

write_settings() {
    file="$MOCK_DIR/config/settings.json"
    case "$1" in
        base)
            cat > "$file" <<'EOF'
{
  "name": "mock-service",
  "port": 8080,
  "debug": false,
  "database": {
    "host": "localhost",
    "pool_size": 5
  }
}
EOF
            ;;
        current)
            cat > "$file" <<'EOF'
{
  "name": "mock-service",
  "port": 9090,
  "debug": true,
  "database": {
    "host": "db.internal",
    "pool_size": 20,
    "timeout_seconds": 30
  }
}
EOF
            ;;
        incoming)
            cat > "$file" <<'EOF'
{
  "name": "mock-service",
  "port": 8000,
  "debug": false,
  "database": {
    "host": "127.0.0.1",
    "pool_size": 10,
    "ssl": true
  }
}
EOF
            ;;
    esac
}

write_readme() {
    file="$MOCK_DIR/docs/README.md"
    case "$1" in
        base)
            cat > "$file" <<'EOF'
# Mock service

Servicio de ejemplo usado para probar la interfaz de gconflict.

## Instalacion

```bash
pip install mock-service
```

## Uso

Ejecuta el servicio con la configuracion por defecto.

## Licencia

MIT
EOF
            ;;
        current)
            cat > "$file" <<'EOF'
# Mock service

Servicio de ejemplo usado para probar la interfaz de gconflict.

## Instalacion

```bash
uv tool install mock-service
uv tool update-shell
```

## Uso

Ejecuta el servicio con la configuracion por defecto.

## Licencia

Apache-2.0
EOF
            ;;
        incoming)
            cat > "$file" <<'EOF'
# Mock service

Servicio de ejemplo usado para probar la interfaz de gconflict.

## Instalacion

```bash
pipx install mock-service
pipx ensurepath
```

## Uso

Ejecuta el servicio con la configuracion por defecto.

## Licencia

BSD-3-Clause
EOF
            ;;
    esac
}

write_theme() {
    file="$MOCK_DIR/styles/theme.css"
    case "$1" in
        base)
            cat > "$file" <<'EOF'
:root {
  --background: #ffffff;
  --foreground: #202020;
  --accent: #2f6feb;
  --border: #d0d7de;
  --radius: 4px;
  --spacing: 8px;
}

.button {
  background: var(--accent);
  color: var(--background);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: var(--spacing);
}

.panel {
  background: var(--background);
  color: var(--foreground);
}
EOF
            ;;
        current)
            cat > "$file" <<'EOF'
:root {
  --background: #10141b;
  --foreground: #e6edf3;
  --accent: #6fbf73;
  --accent-muted: #3d6b45;
  --border: #30363d;
  --radius: 8px;
  --spacing: 12px;
  --font-size: 14px;
}

.button {
  background: var(--accent);
  color: var(--background);
  border: 1px solid var(--accent-muted);
  border-radius: var(--radius);
  padding: var(--spacing) calc(var(--spacing) * 2);
  font-size: var(--font-size);
  transition: background 120ms ease-in-out;
}

.button:hover {
  background: var(--accent-muted);
}

.panel {
  background: var(--background);
  color: var(--foreground);
  border: 1px solid var(--border);
}
EOF
            ;;
        incoming)
            cat > "$file" <<'EOF'
:root {
  --background: #fafafa;
  --foreground: #1b1f24;
  --accent: #d97757;
  --accent-strong: #b45c3f;
  --border: #c9d1d9;
  --radius: 2px;
  --spacing: 6px;
  --shadow: 0 1px 2px rgba(0, 0, 0, 0.12);
}

.button {
  background: transparent;
  color: var(--accent);
  border: 2px solid var(--accent);
  border-radius: var(--radius);
  padding: var(--spacing);
  box-shadow: var(--shadow);
  text-transform: uppercase;
}

.button:active {
  background: var(--accent-strong);
  color: var(--background);
}

.panel {
  background: var(--background);
  color: var(--foreground);
  box-shadow: var(--shadow);
}
EOF
            ;;
    esac
}

# Archivo extenso: un unico conflicto de HUGE_ENTRIES lineas por lado, para
# forzar el scroll en CURRENT, INCOMING y RESULT.
write_huge_module() {
    variant="$1"
    file="$MOCK_DIR/src/huge_module.py"

    {
        cat <<'EOF'
"""Catalogo extenso usado para probar el scroll de los paneles."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Record:
    identifier: int
    label: str
    category: str
    enabled: bool


def build_records() -> list[Record]:
    return [
EOF

        index=1
        while [ "$index" -le "$HUGE_ENTRIES" ]; do
            case "$variant" in
                base)
                    printf '        Record(identifier=%s, label="registro-base-%s", category="general", enabled=True),\n' \
                        "$index" "$index"
                    ;;
                current)
                    printf '        Record(identifier=%s, label="registro-current-%s", category="current-batch", enabled=%s),\n' \
                        "$index" "$index" "$( [ $((index % 2)) -eq 0 ] && echo True || echo False )"
                    ;;
                incoming)
                    printf '        Record(identifier=%s, label="registro-incoming-%s", category="incoming-batch", enabled=%s),\n' \
                        "$index" "$index" "$( [ $((index % 3)) -eq 0 ] && echo False || echo True )"
                    ;;
            esac
            index=$((index + 1))
        done

        cat <<'EOF'
    ]


def total() -> int:
    return len(build_records())
EOF
    } > "$file"
}

write_all_files() {
    variant="$1"
    write_auth "$variant"
    write_settings "$variant"
    write_readme "$variant"
    write_theme "$variant"
    write_huge_module "$variant"
}


# ---------------------------------------------------------------------------
# Construccion del entorno
# ---------------------------------------------------------------------------

log ""
log "Creando entorno mock"
log "  repositorio: $REPO_ROOT"
log "  worktree:    $MOCK_DIR"
log ""

# El commit raiz es un arbol vacio, asi el worktree no arrastra los archivos
# del repositorio real.
EMPTY_TREE="$(git_repo hash-object -t tree /dev/null)"
ROOT_COMMIT="$(git_repo commit-tree "$EMPTY_TREE" -m "mock: commit raiz vacio")"

git_repo branch "$BRANCH_ONE" "$ROOT_COMMIT"
git_repo worktree add --quiet "$MOCK_DIR" "$BRANCH_ONE"

mkdir -p "$MOCK_DIR/src" "$MOCK_DIR/config" "$MOCK_DIR/docs" "$MOCK_DIR/styles"

log "Commit base con los 5 archivos..."
write_all_files base
git_mock add -A
git_mock commit --quiet -m "mock: version base de los archivos"

git_mock branch "$BRANCH_TWO"

log "Cambios en $BRANCH_ONE (lado CURRENT)..."
write_all_files current
git_mock add -A
git_mock commit --quiet -m "mock: cambios de test_one"

log "Cambios en $BRANCH_TWO (lado INCOMING)..."
git_mock checkout --quiet "$BRANCH_TWO"
write_all_files incoming
git_mock add -A
git_mock commit --quiet -m "mock: cambios de test_two"

log "Fusionando $BRANCH_TWO en $BRANCH_ONE..."
git_mock checkout --quiet "$BRANCH_ONE"
git_mock merge --no-edit "$BRANCH_TWO" >/dev/null 2>&1 || true

CONFLICTED="$(git_mock diff --name-only --diff-filter=U)"
[ -n "$CONFLICTED" ] || die "El merge no genero conflictos; el entorno mock no es utilizable."


# ---------------------------------------------------------------------------
# Resumen
# ---------------------------------------------------------------------------

log ""
log "Entorno listo. Archivos en conflicto:"
printf '%s\n' "$CONFLICTED" | sed 's/^/  /'
log ""
log "El archivo src/huge_module.py tiene un conflicto de $HUGE_ENTRIES lineas por"
log "lado para probar el scroll en CURRENT, INCOMING y RESULT."
log ""
log "Ejecuta la TUI con:"
log ""
log "  $REPO_ROOT/.venv/bin/gconflict \"$MOCK_DIR\""
log ""
log "Para eliminar el entorno:"
log ""
log "  $SCRIPT_DIR/clean_mocks.sh"
log ""
