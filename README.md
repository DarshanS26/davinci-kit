# DaVinci Resolve Kit

A Linux toolkit for DaVinci Resolve: GUI, transcoding, export presets, media inspection, diagnostics, font fixes, backups, and watch-folder automation.

DaVinci Resolve Free on Linux cannot import the most common phone/camera formats directly: H.264/H.265 video and AAC audio. This project wraps the working Linux workflow in simple commands and a desktop GUI.

## Features

- **GUI** for common Resolve Linux workflows
- **Import transcoding** to DNxHR `.mov` or AV1 `.mkv`
- **Audio conversion** to WAV, FLAC, ALAC, or MP3
- **Delivery exports** to H.264, H.265, AV1, WebM, ProRes, and archive formats
- **GPU-accelerated encoding** with NVENC (NVIDIA), AMF (AMD), QSV (Intel), and VAAPI (AMD/Intel) when available
- **Media compatibility inspection** powered by `ffprobe`
- **Watch folder** automation for automatic transcodes
- **Resolve launch fix** for library mismatches, Wayland/X11 quirks, and GPU offload on hybrid laptops
- **Font path fix** for Fusion/Text tools
- **Backup/restore** for Resolve settings, LUTs, scripts, macros, and fonts
- **System diagnostics** with severity-classified checks for GPU, OpenCL, codecs, library mismatches, disk space, and toolkit status

## Screenshots

<!-- Uncomment after adding screenshots to assets/screenshots/ -->
<!-- ![DaVinci Resolve Kit main window](assets/screenshots/main-window.png) -->
<!-- ![DaVinci Resolve Kit media inspector](assets/screenshots/inspector-warning.png) -->
<!-- ![DaVinci Resolve Kit export delivery options](assets/screenshots/export-tab.png) -->

Screenshots coming soon.

## Requirements

Required:

- Linux
- DaVinci Resolve installed at `/opt/resolve`
- `bash`
- `ffmpeg` and `ffprobe`
- `python3`
- `PyQt6` or `PySide6` for the GUI

Optional:

- `parallel` for `-j` parallel processing
- `inotify-tools` / `inotifywait` for watch folders
- GPU users: working driver and OpenCL runtime (`opencl-nvidia` on Arch, `rocm-opencl` for AMD, `intel-compute-runtime` for Intel)
- `clinfo` for OpenCL diagnostics

Example packages:

```bash
# Arch / EndeavourOS
sudo pacman -S ffmpeg python python-pyqt6 parallel inotify-tools clinfo

# Debian / Ubuntu
sudo apt install ffmpeg python3 python3-pyqt6 parallel inotify-tools clinfo

# Fedora
sudo dnf install ffmpeg python3 python3-qt6 parallel inotify-tools clinfo
```

Package names vary by distro. `install.sh` checks dependencies and warns if something is missing.

## Install

### One-line installer

```bash
curl -fsSL https://raw.githubusercontent.com/DarshanS26/davinci-kit/main/bootstrap.sh | bash
```

This clones the repo to `~/.local/share/resolve-kit`, symlinks all tools to `~/.local/bin`, and installs a desktop entry.

### Manual git install

```bash
git clone https://github.com/DarshanS26/davinci-kit.git
cd resolve-kit
./install.sh
```

Make sure `~/.local/bin` is on your `PATH`:

```bash
echo $PATH | grep -q "$HOME/.local/bin" || echo 'Add ~/.local/bin to PATH'
```

### Arch / EndeavourOS (AUR)

```bash
yay -S resolve-kit
```

### Update

```bash
resolve-kit-update
```

### Uninstall

```bash
./install.sh --remove
```

## Tools

| Command | Purpose |
|---|---|
| `resolve-gui` | Desktop GUI for the toolkit |
| `resolve-transcode` | Convert source media to Resolve-friendly DNxHR or AV1 |
| `resolve-audio` | Convert audio files to WAV, FLAC, ALAC, or MP3 |
| `resolve-export` | Convert Resolve renders to delivery formats |
| `resolve-fix` | Launch Resolve with Linux compatibility fixes |
| `resolve-backup` | Back up or restore Resolve settings and assets |
| `resolve-fonts` | Add user font directories to Resolve/Fusion |
| `resolve-watch` | Auto-transcode new files in a folder |
| `resolve-info` | Print Resolve/Linux diagnostics |
| `resolve-kit-update` | Update resolve-kit via git |

## Quick Start

Launch the GUI:

```bash
resolve-gui
```

Transcode footage before importing into Resolve:

```bash
resolve-transcode ~/Videos/footage
resolve-transcode -q lb ~/Videos/footage          # proxy quality
resolve-transcode -q hqx -j 4 ~/Videos/raw       # high quality, parallel
resolve-transcode -c av1 ~/Videos/footage        # compact AV1 output
```

Convert a Resolve render for delivery:

```bash
resolve-export export.mov                         # H.264 (CPU default)
resolve-export -p h265 export.mov
resolve-export -p nvenc export.mov               # NVIDIA GPU encode
resolve-export -p youtube4k -r 4k export.mov
```

Convert audio-only files:

```bash
resolve-audio voice-note.m4a
resolve-audio -f flac ~/Audio/session
```

Watch a folder:

```bash
resolve-watch ~/Downloads
resolve-watch -q lb -d ~/Videos/ingest
```

Diagnose your setup:

```bash
resolve-info
```

## Why Transcoding Is Needed

DaVinci Resolve Free on Linux has different codec support than the Windows/macOS builds.

| Codec | Resolve Free on Linux |
|---|---|
| H.264 video | Not supported |
| H.265/HEVC video | Not supported |
| AAC audio | Not supported on Linux, including Studio |
| DNxHR / DNxHD | Supported |
| ProRes | Supported |
| PCM / WAV | Supported |
| FLAC / ALAC | Supported |
| AV1 video | Supported for import on current Resolve versions, with compatible audio |

Typical workflow:

```text
Camera/phone MP4 → resolve-transcode → edit in Resolve → DNxHR render → resolve-export → final MP4/WebM/etc.
```

## DNxHR Quality Presets

| Preset | Use case |
|---|---|
| `lb` | Proxy/offline editing, smaller files |
| `sq` | Standard quality |
| `hq` | Default, good balance |
| `hqx` | 12-bit high quality |
| `444` | Maximum quality, very large files |

DNxHR is an intermediate editing format. Expect much larger files than H.264/H.265 sources.

## Notes for Linux Users

- Resolve needs a working GPU compute stack. Check with `clinfo -l`.
- On hybrid GPU laptops, `resolve-fix` automatically detects your GPU vendor and applies the right offload settings.
- If Resolve starts crashing after a rolling-release distro update, try `resolve-fix`.
- If user-installed fonts do not appear in Fusion/Text tools, run `resolve-fonts`.
- If the UI scale is wrong, see `docs/DAVINCI-RESOLVE-LINUX-GUIDE.md` for the `DisplayScale`/`QT_SCALE_FACTOR` details.
- The export tab detects available GPU encoders (NVENC, AMF, QSV, VAAPI) automatically from your ffmpeg build.

## Documentation

- `docs/DAVINCI-RESOLVE-LINUX-GUIDE.md` — practical Linux guide: codecs, OpenCL, launch fixes, fonts, backups, and troubleshooting.

## Roadmap

- AppImage build for download without git
- Demo video
- More codec compatibility testing across distros
- Distro-specific troubleshooting notes

## Credits

This project builds on public Linux Resolve knowledge from:

- Chris Titus Tech's `resolve-linux`
- ArchWiki DaVinci Resolve documentation
- jchai01's DaVinci Resolve Linux resources
- Alecaddd's FFmpeg/Resolve notes
- Blackmagic Design's supported codec documentation

## License

MIT — see `LICENSE`.