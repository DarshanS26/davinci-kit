#!/usr/bin/env bash
# resolve-kit AppImage build script
set -euo pipefail

# Make sure we are running from project root
cd "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")/../.."

# 1. Read version
VERSION=$(grep '"version":' config/resolve-kit.json | cut -d'"' -f4)
echo "Building resolve-kit AppImage version $VERSION..."

# 2. Setup temp AppDir
APPDIR="/tmp/Resolve-Kit.AppDir"
rm -rf "$APPDIR"
mkdir -p "$APPDIR/usr/bin"
mkdir -p "$APPDIR/usr/share/resolve-kit"

# 3. Copy source files
cp -r bin gui lib config "$APPDIR/usr/share/resolve-kit/"
mkdir -p "$APPDIR/usr/share/resolve-kit/docs"
cp docs/DAVINCI-RESOLVE-LINUX-GUIDE.md "$APPDIR/usr/share/resolve-kit/docs/"
# Copy LICENSE and README.md
cp LICENSE "$APPDIR/usr/share/resolve-kit/"
cp README.md "$APPDIR/usr/share/resolve-kit/"

# 4. Clean up excluded files
while IFS= read -r pattern || [ -n "$pattern" ]; do
    [[ -z "$pattern" || "$pattern" =~ ^# ]] && continue
    find "$APPDIR" -name "$pattern" -exec rm -rf {} + 2>/dev/null || true
done < packaging/appimage/excludelist

# Remove planning/internal docs not caught by excludelist (find -name matches basenames only)
rm -f "$APPDIR/usr/share/resolve-kit/docs/GUI-REDESIGN-PROPOSAL.md"
rm -f "$APPDIR/usr/share/resolve-kit/docs/INSPECTOR-TAB-PLAN.md"
rm -f "$APPDIR/usr/share/resolve-kit/docs/UI-SCALING.md"
rm -f "$APPDIR/usr/share/resolve-kit/docs/NEXT-RELEASE-IMPLEMENTATION-PLAN.md"
rm -f "$APPDIR/usr/share/resolve-kit/docs/OUTREACH-COPY.md"

# Remove all __pycache__ folders and pyc files explicitly
find "$APPDIR" -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find "$APPDIR" -name "*.pyc" -delete 2>/dev/null || true

# 5. Add AppImage metadata at root
cp packaging/appimage/AppRun "$APPDIR/"
chmod +x "$APPDIR/AppRun"
cp packaging/appimage/resolve-kit.desktop "$APPDIR/"
cp packaging/davinci-kit.svg "$APPDIR/"
ln -sf davinci-kit.svg "$APPDIR/.DirIcon"

# Symlink entry point inside usr/bin
ln -sf ../share/resolve-kit/bin/davinci-kit "$APPDIR/usr/bin/davinci-kit"

# 6. Locate or download appimagetool
if ! command -v appimagetool >/dev/null 2>&1; then
    if [ ! -f "packaging/appimage/appimagetool" ]; then
        echo "appimagetool not found on system. Downloading continuous release..."
        curl -Lo packaging/appimage/appimagetool "https://github.com/AppImage/AppImageKit/releases/download/continuous/appimagetool-x86_64.AppImage"
        chmod +x packaging/appimage/appimagetool
    fi
    APPIMAGETOOL="packaging/appimage/appimagetool"
else
    APPIMAGETOOL="appimagetool"
fi

# Run with --appimage-extract-and-run if FUSE is not available
RUN_CMD="$APPIMAGETOOL"
if ! "$APPIMAGETOOL" --version >/dev/null 2>&1; then
    RUN_CMD="$APPIMAGETOOL --appimage-extract-and-run"
fi

# 7. Build AppImage
mkdir -p dist
export ARCH=x86_64
echo "Running appimagetool..."
$RUN_CMD "$APPDIR" "dist/DaVinci-Resolve-Kit-${VERSION}-x86_64.AppImage"

echo "AppImage created successfully: dist/DaVinci-Resolve-Kit-${VERSION}-x86_64.AppImage"
