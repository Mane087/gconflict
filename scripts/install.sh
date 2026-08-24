#!/bin/sh

set -eu

APP_NAME="gconflict"
REPOSITORY="Mane087/gconflict"

INSTALL_ROOT="${GCONFLICT_HOME:-$HOME/.local/share/gconflict}"
BIN_DIR="${GCONFLICT_BIN_DIR:-$HOME/.local/bin}"

UV_DIR="$INSTALL_ROOT/uv"
PYTHON_DIR="$INSTALL_ROOT/python"
TOOLS_DIR="$INSTALL_ROOT/tools"

PYTHON_VERSION="${GCONFLICT_PYTHON_VERSION:-3.13}"


# ---------------------------------------------------------------------------
# Output helpers
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Command helpers
# ---------------------------------------------------------------------------

command_exists() {
    command -v "$1" >/dev/null 2>&1
}


# ---------------------------------------------------------------------------
# Cleanup
# ---------------------------------------------------------------------------

TMP_DIR=""

cleanup() {
    if [ -n "$TMP_DIR" ] && [ -d "$TMP_DIR" ]; then
        rm -rf "$TMP_DIR"
    fi
}

trap cleanup EXIT HUP INT TERM


# ---------------------------------------------------------------------------
# Platform detection
# ---------------------------------------------------------------------------

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

case "$ARCH" in
    arm64|aarch64|x86_64|amd64)
        ;;
    *)
        die "Unsupported architecture: ${ARCH:-unknown}."
        ;;
esac


# ---------------------------------------------------------------------------
# Prerequisites
# ---------------------------------------------------------------------------

command_exists curl || die "curl is required."
command_exists git || die "Git is required."


# ---------------------------------------------------------------------------
# Version helpers
# ---------------------------------------------------------------------------

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

    case "$VERSION" in
        ""|*[!0-9A-Za-z._+-]*)
            die "Invalid gconflict version: $VERSION"
            ;;
    esac
}


resolve_latest_version() {
    log "Resolving latest gconflict release..."

    latest_url="$(
        curl \
            -fsSL \
            -o /dev/null \
            -w '%{url_effective}' \
            "https://github.com/$REPOSITORY/releases/latest"
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


# ---------------------------------------------------------------------------
# Resolve requested gconflict version
# ---------------------------------------------------------------------------

if [ -n "${GCONFLICT_VERSION:-}" ]; then
    normalize_version "$GCONFLICT_VERSION"
else
    resolve_latest_version
fi

PACKAGE_SPEC="git+https://github.com/$REPOSITORY.git@$TAG"


# ---------------------------------------------------------------------------
# Prepare installation directories
# ---------------------------------------------------------------------------

mkdir -p "$INSTALL_ROOT"
mkdir -p "$BIN_DIR"
mkdir -p "$PYTHON_DIR"
mkdir -p "$TOOLS_DIR"


# ---------------------------------------------------------------------------
# Installation information
# ---------------------------------------------------------------------------

log ""
log "Installing $APP_NAME $VERSION"
log "Platform: $PLATFORM ($ARCH)"
log "Python:   $PYTHON_VERSION (uv-managed)"
log "Source:   https://github.com/$REPOSITORY/tree/$TAG"
log ""


# ---------------------------------------------------------------------------
# Install private uv
# ---------------------------------------------------------------------------

UV_BIN="$UV_DIR/uv"

if [ ! -x "$UV_BIN" ]; then
    log "Installing private uv runtime..."

    mkdir -p "$UV_DIR"

    if ! curl -LsSf https://astral.sh/uv/install.sh \
        | env \
            UV_UNMANAGED_INSTALL="$UV_DIR" \
            sh; then

        die "Unable to install uv."
    fi

    if [ ! -x "$UV_BIN" ]; then
        die "uv installation completed but the executable was not found at $UV_BIN."
    fi
else
    log "Using existing private uv installation."
fi


# ---------------------------------------------------------------------------
# Display uv version
# ---------------------------------------------------------------------------

UV_VERSION="$("$UV_BIN" --version 2>/dev/null || true)"

if [ -z "$UV_VERSION" ]; then
    die "Unable to execute uv."
fi

log "uv:       $UV_VERSION"


# ---------------------------------------------------------------------------
# Install uv-managed Python
# ---------------------------------------------------------------------------

log ""
log "Preparing Python $PYTHON_VERSION..."

if ! env \
    UV_PYTHON_INSTALL_DIR="$PYTHON_DIR" \
    "$UV_BIN" python install \
        "$PYTHON_VERSION"; then

    die "Unable to install Python $PYTHON_VERSION."
fi


# ---------------------------------------------------------------------------
# Install gconflict
# ---------------------------------------------------------------------------

log ""
log "Installing $APP_NAME..."

if ! env \
    UV_PYTHON_INSTALL_DIR="$PYTHON_DIR" \
    UV_TOOL_DIR="$TOOLS_DIR" \
    UV_TOOL_BIN_DIR="$BIN_DIR" \
    "$UV_BIN" tool install \
        --managed-python \
        --python "$PYTHON_VERSION" \
        --force \
        "$PACKAGE_SPEC"; then

    die "Unable to install $APP_NAME."
fi


# ---------------------------------------------------------------------------
# Verify executable
# ---------------------------------------------------------------------------

PUBLIC_EXECUTABLE="$BIN_DIR/$APP_NAME"

if [ ! -x "$PUBLIC_EXECUTABLE" ]; then
    die "$APP_NAME was installed but the executable was not found at $PUBLIC_EXECUTABLE."
fi


# ---------------------------------------------------------------------------
# Verify installed package version
# ---------------------------------------------------------------------------

VERSION_OUTPUT="$(
    "$PUBLIC_EXECUTABLE" --version 2>/dev/null || true
)"

if [ -z "$VERSION_OUTPUT" ]; then
    die "$APP_NAME was installed but its smoke test failed."
fi

case "$VERSION_OUTPUT" in
    *"$VERSION"*)
        ;;
    *)
        die "Installed $APP_NAME version does not match requested version $VERSION. Output: $VERSION_OUTPUT"
        ;;
esac


# ---------------------------------------------------------------------------
# Success
# ---------------------------------------------------------------------------

log ""
log "$APP_NAME $VERSION installed successfully."
log ""
log "Executable:"
log "  $PUBLIC_EXECUTABLE"
log ""
log "Runtime:"
log "  $UV_VERSION"
log "  Python $PYTHON_VERSION managed by uv"


# ---------------------------------------------------------------------------
# PATH validation
# ---------------------------------------------------------------------------

case ":$PATH:" in
    *":$BIN_DIR:"*)
        log ""
        log "Run:"
        log ""
        log "  $APP_NAME --version"
        log "  $APP_NAME"
        log ""
        ;;

    *)
        log ""
        warn "$BIN_DIR is not currently in PATH."
        log ""
        log "Add this line to your shell configuration:"
        log ""
        log "  export PATH=\"$BIN_DIR:\$PATH\""
        log ""
        log "For zsh:"
        log ""
        log "  echo 'export PATH=\"$BIN_DIR:\$PATH\"' >> ~/.zshrc"
        log "  source ~/.zshrc"
        log ""
        ;;
esac