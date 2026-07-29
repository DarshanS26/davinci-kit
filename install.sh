#!/usr/bin/env bash
# =============================================================================
#  install.sh — Symlink resolve-kit scripts to ~/.local/bin
#
#  Usage:
#    ./install.sh          # Install all scripts
#    ./install.sh --remove # Remove all symlinks
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BIN_DIR="$HOME/.local/bin"
APP_DIR="$HOME/.local/share/applications"
DESKTOP_FILE="davinci-kit.desktop"
REMOVE=false

[[ "${1:-}" == "--remove" ]] && REMOVE=true

# ---- helpers ----------------------------------------------------------------

info()  { echo -e "\033[1;34m[INFO]\033[0m  $*"; }
warn()  { echo -e "\033[1;33m[WARN]\033[0m  $*"; }
ok()    { echo -e "\033[1;32m[OK]\033[0m    $*"; }

check_cmd() {
  if command -v "$1" &>/dev/null; then
    ok "$1 found: $(command -v "$1")"
    return 0
  fi

  warn "$1 not found — $2"
  return 1
}

# ---- scripts list -----------------------------------------------------------

scripts=(
  "resolve-gui"
  "resolve-transcode"
  "resolve-audio"
  "resolve-export"
  "resolve-fix"
  "resolve-backup"
  "resolve-fonts"
  "resolve-watch"
  "resolve-info"
  "resolve-kit-update"
)

# =============================================================================
if $REMOVE; then
# =============================================================================
  echo "Removing resolve-kit symlinks from $BIN_DIR..."
  for script in "${scripts[@]}"; do
    target="$BIN_DIR/$script"
    if [[ -L "$target" ]]; then
      # Safety: only remove symlinks that point into our bin/ directory
      link_target="$(readlink "$target")"
      if [[ "$link_target" == "$SCRIPT_DIR/bin/"* ]]; then
        rm "$target"
        echo "  Removed: $script"
      else
        warn "Skipped: $script (symlink points to $link_target, not resolve-kit)"
      fi
    else
      echo "  Not found: $script (skipping)"
    fi
  done
  # Desktop entry
  if [[ -f "$APP_DIR/$DESKTOP_FILE" ]]; then
    rm -f "$APP_DIR/$DESKTOP_FILE"
    echo "  Removed: $DESKTOP_FILE"
  fi
  # Refresh desktop database
  if command -v update-desktop-database &>/dev/null; then
    update-desktop-database "$APP_DIR" 2>/dev/null || true
    echo "  Desktop database updated."
  fi
  echo "Done."

# =============================================================================
else
# =============================================================================
  # ---- dependency checks ----------------------------------------------------
  echo "Checking dependencies..."
  missing_required=0

  check_cmd ffmpeg  "required for transcode/export/audio/watch"     || missing_required=1
  check_cmd ffprobe "required for transcode/export/audio/watch"     || missing_required=1
  check_cmd python3 "required for resolve-gui (GUI)"                || missing_required=1

  # GUI requires PyQt6 or PySide6 — check if python3 can import either
  if command -v python3 &>/dev/null; then
    if python3 -c "import PyQt6" 2>/dev/null; then
      ok "PyQt6 found (GUI backend)"
    elif python3 -c "import PySide6" 2>/dev/null; then
      ok "PySide6 found (GUI backend)"
    else
      warn "PyQt6/PySide6 not found — resolve-gui will not work"
      warn "  Install one of: python-pyqt6  or  python-pyside6"
    fi
  fi

  # Optional tools
  check_cmd parallel    "optional — enables -j parallel jobs in transcode/export/audio" || true
  check_cmd inotifywait "optional — required only for resolve-watch"                    || true

  if [[ $missing_required -eq 1 ]]; then
    echo
    warn "Some required tools are missing. resolve-kit will install but certain"
    warn "commands may not work until dependencies are satisfied."
    echo
  fi

  # ---- ensure target directories exist --------------------------------------
  mkdir -p "$BIN_DIR"
  mkdir -p "$APP_DIR"

  # ---- symlink scripts ------------------------------------------------------
  echo
  echo "Installing resolve-kit scripts to $BIN_DIR..."

  for script in "${scripts[@]}"; do
    source="$SCRIPT_DIR/bin/$script"
    target="$BIN_DIR/$script"

    if [[ ! -f "$source" ]]; then
      warn "Missing: $script (not in $SCRIPT_DIR/bin/)"
      continue
    fi

    # Safety: only replace symlinks that point into our bin/ directory or files
    # we previously installed. Never remove an unrelated binary.
    if [[ -L "$target" ]]; then
      link_target="$(readlink "$target")"
      if [[ "$link_target" == "$SCRIPT_DIR/bin/"* ]]; then
        rm "$target"
      else
        warn "Skipped: $script (existing symlink points to $link_target)"
        continue
      fi
    elif [[ -f "$target" ]]; then
      warn "Skipped: $script (existing file at $target — not overwriting)"
      continue
    fi

    ln -s "$source" "$target"
    echo "  Linked: $script → $source"
  done

  # ---- install icon --------------------------------------------------------
  ICON_DIR="$HOME/.local/share/icons/hicolor/scalable/apps"
  mkdir -p "$ICON_DIR"
  if [[ -f "$SCRIPT_DIR/packaging/resolve-kit.svg" ]]; then
    cp "$SCRIPT_DIR/packaging/resolve-kit.svg" "$ICON_DIR/resolve-kit.svg"
    echo "  Installed: $ICON_DIR/resolve-kit.svg"
    if command -v gtk-update-icon-cache &>/dev/null; then
      gtk-update-icon-cache -f -t "$HOME/.local/share/icons/hicolor" 2>/dev/null || true
    fi
  else
    warn "packaging/resolve-kit.svg not found — desktop entry will fall back to system icon"
  fi

  # ---- install desktop entry ------------------------------------------------
  echo
  echo "Installing desktop entry..."

  cat > "$APP_DIR/$DESKTOP_FILE" <<DESKTOP
[Desktop Entry]
Type=Application
Name=DaVinci Resolve Kit
GenericName=DaVinci Resolve Linux Studio Toolkit
Comment=Transcode, export, diagnose, and optimize DaVinci Resolve on Linux
Exec=${BIN_DIR}/resolve-gui
Icon=resolve-kit
StartupWMClass=davinci-kit
Terminal=false
Categories=AudioVideo;Video;AudioVideoEditing;Qt;
Keywords=DaVinci;Resolve;Transcode;FFmpeg;DNxHR;Video;Linux;Export;
DESKTOP
  echo "  Installed: $APP_DIR/$DESKTOP_FILE"

  # Refresh desktop database
  if command -v update-desktop-database &>/dev/null; then
    update-desktop-database "$APP_DIR" 2>/dev/null || true
    echo "  Desktop database updated."
  fi

  # ---- legacy check ---------------------------------------------------------
  if [[ -f "$BIN_DIR/resolve-prime" ]] && [[ ! -L "$BIN_DIR/resolve-prime" ]]; then
    echo
    warn "resolve-prime found (legacy, replaced by resolve-fix)"
    warn "  You can remove it with: rm ~/.local/bin/resolve-prime"
  fi

  # ---- summary --------------------------------------------------------------
  echo
  echo "Installed! Available commands:"
  echo "  resolve-gui        — Graphical interface studio for resolve-kit"
  echo "  resolve-transcode  — Batch transcode media for Resolve (DNxHR / AV1)"
  echo "  resolve-audio      — Batch convert audio files for Resolve (WAV/FLAC/ALAC/MP3)"
  echo "  resolve-export     — Convert Resolve exports for delivery (H.264/H.265/AV1/NVENC)"
  echo "  resolve-fix        — Launch Resolve with library fix + NVIDIA GPU offload"
  echo "  resolve-backup     — Backup/restore Resolve settings"
  echo "  resolve-fonts      — Fix font paths in Fusion"
  echo "  resolve-watch      — Auto-transcode watch folder (DNxHR / AV1)"
  echo "  resolve-info       — System diagnostics"
  echo "  resolve-kit-update — Update resolve-kit via git"
fi
