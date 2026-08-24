#!/bin/sh

set -eu

APP_NAME="gconflict"
REPOSITORY="Mane087/gconflict"

INSTALL_ROOT="${GCONFLICT_HOME:-$HOME/.local/share/gconflict}"
BIN_DIR="${GCONFLICT_BIN_DIR:-$HOME/.local/bin}"

log() {
    printf '%s\n' "$*"
}

warn() {
    printf 'warning: %s\n' "$*" >&2
}

die() {
    printf 'error: %s\n' "$*" >&2
    exit 1
}

command_exists() {
    command -v "$1" >/dev/null 2>&1
}

find_python() {
    if [ -n "${PYTHON:-}" ]; then
        if command_exists "$PYTHON" &&
           "$PYTHON" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 13) else 1)' >/dev/null 2>&1; then
            command -v "$PYTHON"
            return 0
        fi
    fi

    for candidate in python3.14 python3.13 python3; do
        if command_exists "$candidate" &&
           "$candidate" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 13) else 1)' >/dev/null 2>&1; then
            command -v "$candidate"
            return 0
        fi
    done

    return 1
}

normalize_version() {
    case "$1" in
        v*)
            TAG="$1"
            VERSION="${1#v}"
            ;;
        *)
            TAG="v$1"
            VERSION="$1"
            ;;
    esac
}

resolve_latest_version() {
    latest_url="$(
        curl -fsSL             -o /dev/null             -w '%{url_effective}'             "https://github.com/$REPOSITORY/releases/latest"
    )" || die "Unable to resolve the latest GitHub release."

    latest_url="${latest_url%/}"
    latest_tag="${latest_url##*/}"

    case "$latest_tag" in
        v*)
            normalize_version "$latest_tag"
            ;;
        *)
            die "Latest GitHub release does not use the expected vX.Y.Z tag format."
            ;;
    esac
}

cleanup() {
    if [ -n "${TMP_DIR:-}" ] && [ -d "$TMP_DIR" ]; then
        rm -rf "$TMP_DIR"
    fi
}

trap cleanup EXIT HUP INT TERM

command_exists curl || die "curl is required."
command_exists git || die "Git is required."

OS="$(uname -s 2>/dev/null || true)"
ARCH="$(uname -m 2>/dev/null || true)"

case "$OS" in
    Darwin)
        PLATFORM="macOS"
        ;;
    Linux)
        PLATFORM="Linux"
        ;;
    *)
        die "Unsupported operating system: ${OS:-unknown}. gconflict currently supports macOS and Linux."
        ;;
esac

PYTHON_BIN="$(find_python)" || die "Python 3.13 or newer is required. Install a compatible Python version and run the installer again."

PYTHON_VERSION="$(
    "$PYTHON_BIN" -c 'import sys; print(".".join(map(str, sys.version_info[:3])))'
)"

if [ -n "${GCONFLICT_VERSION:-}" ]; then
    normalize_version "$GCONFLICT_VERSION"
else
    resolve_latest_version
fi

PACKAGE_URL="https://github.com/$REPOSITORY/archive/refs/tags/$TAG.tar.gz"

VERSION_DIR="$INSTALL_ROOT/versions/$VERSION"
CURRENT_LINK="$INSTALL_ROOT/current"
TARGET_VENV="$VERSION_DIR/venv"
TARGET_EXECUTABLE="$TARGET_VENV/bin/$APP_NAME"
PUBLIC_EXECUTABLE="$BIN_DIR/$APP_NAME"

log ""
log "Installing $APP_NAME $VERSION"
log "Platform: $PLATFORM ($ARCH)"
log "Python:   $PYTHON_VERSION"
log "Source:   $PACKAGE_URL"
log ""

mkdir -p "$INSTALL_ROOT/versions"
mkdir -p "$BIN_DIR"

if [ -x "$TARGET_EXECUTABLE" ]; then
    INSTALLED_VERSION="$(
        "$TARGET_VENV/bin/python" -c 'from importlib.metadata import version; print(version("gconflict"))' 2>/dev/null || true
    )"

    if [ "$INSTALLED_VERSION" = "$VERSION" ]; then
        log "$APP_NAME $VERSION is already installed."
    else
        warn "Existing installation for $VERSION is invalid; reinstalling it."
        rm -rf "$VERSION_DIR"
    fi
fi

if [ ! -x "$TARGET_EXECUTABLE" ]; then
    TMP_DIR="$INSTALL_ROOT/.install-$VERSION-$$"

    rm -rf "$TMP_DIR"
    mkdir -p "$TMP_DIR"

    "$PYTHON_BIN" -m venv "$TMP_DIR/venv"

    "$TMP_DIR/venv/bin/python" -m pip install         --disable-pip-version-check         --upgrade pip

    "$TMP_DIR/venv/bin/python" -m pip install         --disable-pip-version-check         "$PACKAGE_URL"

    INSTALLED_VERSION="$(
        "$TMP_DIR/venv/bin/python" -c 'from importlib.metadata import version; print(version("gconflict"))'
    )"

    if [ "$INSTALLED_VERSION" != "$VERSION" ]; then
        die "Installed package version '$INSTALLED_VERSION' does not match requested version '$VERSION'."
    fi

    rm -rf "$VERSION_DIR"
    mv "$TMP_DIR" "$VERSION_DIR"
    TMP_DIR=""
fi

if [ -e "$CURRENT_LINK" ] && [ ! -L "$CURRENT_LINK" ]; then
    die "$CURRENT_LINK already exists and is not a symbolic link."
fi

rm -f "$CURRENT_LINK"
ln -s "$VERSION_DIR" "$CURRENT_LINK"

if [ -e "$PUBLIC_EXECUTABLE" ] && [ ! -L "$PUBLIC_EXECUTABLE" ]; then
    die "$PUBLIC_EXECUTABLE already exists and is not a symbolic link."
fi

rm -f "$PUBLIC_EXECUTABLE"
ln -s "$CURRENT_LINK/venv/bin/$APP_NAME" "$PUBLIC_EXECUTABLE"

if ! "$PUBLIC_EXECUTABLE" --version >/dev/null 2>&1; then
    die "$APP_NAME was installed but its smoke test failed."
fi

log ""
log "$APP_NAME $VERSION installed successfully."
log "Executable: $PUBLIC_EXECUTABLE"

case ":$PATH:" in
    *":$BIN_DIR:"*)
        log ""
        log "Run:"
        log "  $APP_NAME --version"
        ;;
    *)
        log ""
        warn "$BIN_DIR is not currently in PATH."
        log "Add this line to your shell configuration:"
        log ""
        log "  export PATH="$BIN_DIR:\$PATH""
        log ""
        log "Then restart your terminal or reload the shell configuration."
        ;;
esac
