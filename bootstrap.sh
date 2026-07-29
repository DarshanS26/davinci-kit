#!/usr/bin/env bash
# resolve-kit curl bootstrap installer
set -euo pipefail

# Ensure git is installed
if ! command -v git >/dev/null 2>&1; then
    echo "[ERR] git is required to install resolve-kit." >&2
    exit 1
fi

DEST="${RESOLVE_KIT_HOME:-$HOME/.local/share/resolve-kit}"
REPO_URL="${RESOLVE_KIT_REPO:-https://github.com/DarshanS26/davinci-kit.git}"
BRANCH="${RESOLVE_KIT_BRANCH:-main}"

if [ -d "$DEST" ]; then
    if [ -d "$DEST/.git" ]; then
        echo "Updating existing installation in $DEST..."
        cd "$DEST"
        git fetch origin "$BRANCH"
        git checkout "$BRANCH"
        git pull --ff-only origin "$BRANCH"
    else
        echo "[ERR] Destination directory '$DEST' exists but is not a git repository." >&2
        echo "      Please remove or rename it and try again." >&2
        exit 1
    fi
else
    echo "Cloning resolve-kit into $DEST..."
    mkdir -p "$(dirname "$DEST")"
    git clone --depth=1 --branch "$BRANCH" "$REPO_URL" "$DEST"
fi

echo "Running install.sh..."
cd "$DEST"
./install.sh

echo "=================================================="
echo "Installed DaVinci Resolve Kit."
echo "Commands: davinci-kit, davinci-kit-transcode, davinci-kit-export, davinci-kit-info, ..."
echo "Update later with: davinci-kit-update"
echo "=================================================="
