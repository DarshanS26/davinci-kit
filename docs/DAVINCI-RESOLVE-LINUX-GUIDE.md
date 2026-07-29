# DaVinci Resolve on Linux — Complete Reference

> Everything you need to know about running DaVinci Resolve on Linux, with practical notes for Arch-based distros and hybrid NVIDIA laptops. Based on community research, Blackmagic documentation, ArchWiki notes, and field testing.

---

## Table of Contents

1. [The Big Picture](#1-the-big-picture)
2. [Codec Support — The #1 Problem](#2-codec-support--the-1-problem)
3. [GPU & OpenCL Setup](#3-gpu--opencl-setup)
4. [Library Mismatch Crashes](#4-library-mismatch-crashes)
5. [Hybrid GPU (PRIME) Setup](#5-hybrid-gpu-prime-setup)
6. [Transcoding Workflow](#6-transcoding-workflow)
7. [Export/Delivery Workflow](#7-exportdelivery-workflow)
8. [Font Path Issues](#8-font-path-issues)
9. [OBS Recording Settings](#9-obs-recording-settings)
10. [Proxy Editing Workflow](#10-proxy-editing-workflow)
11. [Installation on Arch/EndeavourOS](#11-installation-on-archendeavourOS)
12. [Window & UI Issues](#12-window--ui-issues)
13. [AAC Plugin (Studio Only)](#13-aac-plugin-studio-only)
14. [Backup & Migration](#14-backup--migration)
15. [Troubleshooting Checklist](#15-troubleshooting-checklist)
16. [Example Configuration](#16-example-configuration)
17. [Sources & References](#17-sources--references)

---

## 1. The Big Picture

DaVinci Resolve on Linux works, but it's not plug-and-play. The free version has **critical codec limitations**, the installation requires **specific GPU/OpenCL setup**, and Arch-based distros need **library fixups**. Once configured correctly, it runs well and can even outperform Windows on the same hardware.

**What works great:**
- DNxHR/ProRes editing workflow
- Color grading (Resolve's original purpose)
- Fusion compositing
- Fairlight audio (with supported formats)
- NVIDIA CUDA/OpenCL acceleration

**What doesn't work (Free version on Linux):**
- H.264/H.265 video decode or encode
- AAC audio decode or encode
- Hardware encoding (NVENC)
- External scripting (Python/Lua only works from within Resolve)

**What doesn't work (Even Studio on Linux):**
- AAC audio (licensing issue — no Linux version supports it)

---

## 2. Codec Support — The #1 Problem

This is the single most important thing to understand. If you get this wrong, your video imports as **black screen with no audio**.

### Free Version on Linux

| Video Codec | Decode | Encode | Notes |
|---|---|---|---|
| H.264 | ❌ | ❌ | Most common codec — **must transcode** |
| H.265/HEVC | ❌ | ❌ | Must transcode |
| DNxHR | ✅ | ✅ | **Use this — the primary working codec** |
| ProRes | ✅ | ✅ | Works well, larger than DNxHR |
| AV1 | ✅ (decode) | ❌ | Only if audio is PCM/MP3 |

| Audio Codec | Support | Notes |
|---|---|---|
| AAC | ❌ | **Not supported on ANY Linux version** |
| PCM/WAV | ✅ | Safe default |
| MP3 | ✅ | Decent lossy option |
| FLAC | ✅ | In .mkv containers |
| ALAC | ✅ | Good for .mov containers |
| Opus | ✅ | In .mkv containers |

### Studio Version on Linux

| Video Codec | Decode | Encode | Notes |
|---|---|---|---|
| H.264 | ✅ | ✅ | Studio unlocks this |
| H.265/HEVC | ✅ | ✅ | Studio unlocks this |
| AAC Audio | ❌ | ❌ | **Still NOT supported even in Studio** |

### Why AAC Doesn't Work on Linux

AAC is encumbered by Via LA patent pools. On Windows/macOS, the OS vendor (Microsoft/Apple) has already paid for system-wide AAC licenses. On Linux, there's no corporate licensee. Blackmagic won't bundle unlicensed codecs in their closed-source product, and they can't use GPL libraries (FFmpeg/GStreamer). This is unlikely to change.

### The Standard Workflow

```
┌─────────────────┐     ffmpeg transcode     ┌─────────────────┐
│  Source footage  │  ─────────────────────→  │  DNxHR/PCM .mov │
│  (MP4/H264/AAC) │     resolve-transcode    │  Resolve import  │
└─────────────────┘                          └────────┬────────┘
                                                      │
                                              Edit in Resolve
                                                      │
                                                      ▼
                                             ┌─────────────────┐
                                             │  DNxHR export   │
                                             │  from Resolve    │
                                             └────────┬────────┘
                                                      │
                                              ffmpeg transcode
                                           (resolve-export)
                                                      │
                                                      ▼
                                             ┌─────────────────┐
                                             │  H.264/AAC .mp4  │
                                             │  Final delivery   │
                                             └─────────────────┘
```

### Transcode Commands Reference

**Import — Convert footage for Resolve (most common):**
```bash
# H.264 + AAC → DNxHR HQ + PCM (most common MP4/phone footage)
ffmpeg -i input.mp4 -c:v dnxhd -profile:v dnxhr_hq -pix_fmt yuv422p \
  -c:a pcm_s24le -ar 48000 -ac 2 output.mov

# H.264 + AAC → DNxHR HQ + ALAC (smaller audio, still lossless)
ffmpeg -i input.mp4 -c:v dnxhd -profile:v dnxhr_hq -pix_fmt yuv422p \
  -c:a alac output.mov

# H.264 + PCM/MP3 → DNxHR (video only transcode, audio copy)
ffmpeg -i input.mp4 -c:v dnxhd -profile:v dnxhr_hq -pix_fmt yuv422p \
  -c:a copy output.mov

# AV1 + AAC → copy video, transcode audio only
ffmpeg -i input.mp4 -c:v copy -c:a pcm_s32le output.mp4

# Proxy quality for fast offline editing
ffmpeg -i input.mp4 -c:v dnxhd -profile:v dnxhr_lb -pix_fmt yuv422p \
  -c:a pcm_s16le output.mov

# Or use resolve-transcode:
resolve-transcode -q hq /path/to/footage          # High quality (default)
resolve-transcode -q lb /path/to/footage          # Proxy quality
resolve-transcode -q hqx -j 4 /path/to/raw       # 12-bit, 4 parallel
resolve-transcode -a alac /path/to/footage         # ALAC audio (smaller)
resolve-transcode video.mp4                         # Single file
```

**Export — Convert Resolve output for delivery:**
```bash
# YouTube H.264 1080p (recommended)
ffmpeg -i resolve_export.mov -c:v libx264 -crf 18 -preset slow \
  -pix_fmt yuv420p -c:a aac -b:a 192k -movflags +faststart output.mp4

# YouTube H.264 4K
ffmpeg -i resolve_export.mov -c:v libx264 -crf 20 -preset slow \
  -pix_fmt yuv420p -c:a aac -b:a 192k -movflags +faststart output.mp4

# H.265 (smaller file)
ffmpeg -i resolve_export.mov -c:v libx265 -crf 22 -preset medium \
  -pix_fmt yuv420p -c:a aac -b:a 192k -movflags +faststart output.mp4

# ProRes 422 HQ (for further editing in another NLE)
ffmpeg -i resolve_export.mov -c:v prores_ks -profile:v 3 \
  -pix_fmt yuv422p10le -c:a pcm_s24le output.mov

# Or use resolve-export:
resolve-export -p youtube export.mov              # YouTube H.264
resolve-export -p h265 export.mov                 # H.265
resolve-export -p prores export.mov               # ProRes 422 HQ
resolve-export -p archive export.mov              # Near-lossless
```

### DNxHR Quality Tiers

| Profile | FFmpeg Name | Bitrate | File Size | Use Case |
|---|---|---|---|---|
| LB | `dnxhr_lb` | ~100 Mbps | ~0.75 GB/min | Proxy/offline editing |
| SQ | `dnxhr_sq` | ~220 Mbps | ~1.6 GB/min | Standard quality |
| HQ | `dnxhr_hq` | ~440 Mbps | ~3.3 GB/min | **Default, best balance** |
| HQX | `dnxhr_hqx` | ~660 Mbps | ~5 GB/min | 12-bit, high quality |
| 444 | `dnxhr_444` | ~880 Mbps | ~6.6 GB/min | 4:4:4, maximum quality |

**Warning:** DNxHR files are 4-5x larger than H.264 originals. Budget 3-5 GB/minute at HQ quality.

### Audio Codec Comparison

| Codec | Container | Size | Quality | Resolve Support | Best For |
|---|---|---|---|---|---|
| PCM s16le | .mov/.wav | Large | Lossless 16-bit | ✅ | Quick transcode |
| PCM s24le | .mov/.wav | Larger | Lossless 24-bit | ✅ | **Best quality** |
| ALAC | .mov | Medium | Lossless | ✅ | Smaller than PCM |
| FLAC | .mkv | Medium | Lossless | ✅ | Archiving |
| Opus | .mkv | Small | Lossy | ✅ | OBS recording |
| AAC | .mp4/.mov | Smallest | Lossy | ❌ | **Not supported** |

---

## 3. GPU & OpenCL Setup

Resolve **requires** a working OpenCL runtime. Without it, it will either crash on startup or run in CPU-only mode (extremely slow).

### NVIDIA (Best Experience)

```bash
# Install NVIDIA drivers + OpenCL
sudo pacman -S nvidia-utils nvidia-open opencl-nvidia

# Verify
clinfo -l
# Should show:
# Platform #0: NVIDIA CUDA
#  `-- Device #0: NVIDIA GeForce RTX 3050 Laptop GPU
```

### AMD (Workable)

```bash
# Install ROCm/OpenCL
sudo pacman -S rocm-hip-runtime opencl-mesa

# For pre-Vega GPUs, set:
export ROC_ENABLE_PRE_VEGA=1
```

### Intel iGPU (Functional but Slow)

```bash
# Install Intel compute runtime
sudo pacman -S intel-compute-runtime

# Verify
clinfo -l
# Should show Intel device
```

**Performance expectation:** Intel iGPU adequate for 1080p only. 4K will be painful.

### GPU Hierarchy for DaVinci Resolve on Linux

1. **NVIDIA (best)** — CUDA + NVENC hardware encode/decode. RTX 3060+ recommended.
2. **AMD (workable)** — ROCm/OpenCL. RX 6800+ for 4K.
3. **Intel iGPU (functional but slow)** — Works via `intel-compute-runtime`. Adequate for 1080p.

---

## 4. Library Mismatch Crashes

### The Problem

DaVinci Resolve is built for Rocky Linux (RHEL-based) and bundles older versions of key libraries (glib 2.80.x). Arch-based distros have much newer versions (glib 2.88.x). When Resolve starts, it finds its own older libraries first, but some components load newer system libraries. This version mismatch causes **immediate crashes or silent failures**.

### Symptoms

- Resolve won't start — exits immediately with no window
- `symbol lookup error: /usr/lib/libpango-1.0.so.0: undefined symbol: g_once_init_leave_pointer`
- Segfault on startup

### The Fix

Preload the system's newer libraries so Resolve uses consistent versions:

```bash
# Method 1: LD_PRELOAD wrapper (resolve-fix)
export LD_PRELOAD="/usr/lib/libglib-2.0.so.0:/usr/lib/libgobject-2.0.so.0:/usr/lib/libgio-2.0.so.0:/usr/lib/libgmodule-2.0.so.0"
export LD_LIBRARY_PATH="/usr/lib:$LD_LIBRARY_PATH"
exec /opt/resolve/bin/resolve "$@"
```

```bash
# Method 2: Copy system libs into Resolve's lib dir
sudo cp /usr/lib/libglib-2.0.so.0 /opt/resolve/libs/
sudo cp /usr/lib/libgobject-2.0.so.0 /opt/resolve/libs/
sudo cp /usr/lib/libgio-2.0.so.0 /opt/resolve/libs/
sudo cp /usr/lib/libgmodule-2.0.so.0 /opt/resolve/libs/
```

```bash
# Method 3: Chris Titus Tech's resolve-fix script
# https://github.com/ChrisTitusTech/resolve-linux
```

### When to Use `resolve-fix`

Use `resolve-fix` when Resolve exits immediately, crashes after a rolling-release system update, or reports GLib/GIO/Pango symbol errors. If Resolve already launches cleanly, you may not need the library preload path.

---

## 5. Hybrid GPU (PRIME) Setup

### The Problem

On laptops with both Intel iGPU and NVIDIA dGPU, Resolve may use Intel for OpenGL (UI rendering) but NVIDIA for CUDA compute. This causes the error:

```
OpenGL context is not running on the GPU marked as Main Display GPU
```

And the UI may be sluggish or glitchy.

### The Fix

Use PRIME render offload to force NVIDIA for everything:

```bash
# PRIME launcher environment
export __NV_PRIME_RENDER_OFFLOAD=1
export __GLX_VENDOR_LIBRARY_NAME=nvidia
export __VK_LAYER_NV_optimus=NVIDIA_only
export QT_AUTO_SCREEN_SCALE_FACTOR=1
export QT_SCALE_FACTOR=1.0
exec /opt/resolve/bin/resolve "$@"
```

The `resolve-fix` launcher sets these variables for you. If you maintain a separate desktop entry, make sure it launches through that wrapper or exports equivalent variables.

### EnvyControl GPU Mode

```bash
# Check current mode
envycontrol --query

# Switch to hybrid (NVIDIA on-demand, recommended for laptops)
sudo envycontrol -s hybrid

# Switch to NVIDIA only (better performance, worse battery)
sudo envycontrol -s nvidia

# Switch to integrated (no NVIDIA, best battery)
sudo envycontrol -s integrated
```

Hybrid mode + PRIME offload is recommended for daily use. Switch to NVIDIA only when doing heavy Resolve sessions.

---

## 6. Transcoding Workflow

### Automatic Transcoding with resolve-transcode

```bash
# Basic usage
resolve-transcode /path/to/footage                # HQ quality, auto audio
resolve-transcode -q sq /path/to/footage          # Standard quality
resolve-transcode -q lb /path/to/footage          # Proxy quality
resolve-transcode -q hqx -j 4 /path/to/raw        # 12-bit, 4 parallel jobs
resolve-transcode -a alac /path/to/footage         # ALAC audio (smaller)
resolve-transcode video.mp4                        # Single file
resolve-transcode vid1.mp4 vid2.mkv               # Multiple files
resolve-transcode -o /mnt/edit /mnt/raw            # Custom output dir
resolve-transcode -n /path/to/footage              # Dry-run preview
```

### Smart Audio Handling (auto mode)

The `resolve-transcode` script with `-a auto` (default) automatically:

| Source Audio | Action | Reason |
|---|---|---|
| PCM (any) | Copy as-is | Already lossless and compatible |
| FLAC | Pass through | Lossless, supported in .mov |
| ALAC | Pass through | Lossless, supported in .mov |
| AAC | Transcode to PCM 24-bit | AAC not supported |
| Opus | Transcode to PCM 24-bit | Only in .mkv, not .mov |
| MP3 | Transcode to PCM 24-bit | Compatible but lossy |
| No audio | Skip (-an) | No track to process |

### Auto-Watch Folder

```bash
# Install inotify-tools first
sudo pacman -S inotify-tools

# Watch a folder for new files
resolve-watch ~/Downloads

# Watch with specific quality
resolve-watch -q sq /mnt/ingest

# Run as background daemon
resolve-watch -d /mnt/ingest
```

### Manual FFmpeg Commands

See [Section 2](#2-codec-support--the-1-problem) above for the full command reference, or check `config/codec-reference.sh` in this project.

---

## 7. Export/Delivery Workflow

After editing in Resolve, export as DNxHR/PCM .mov from the Deliver page, then convert:

```bash
# YouTube 1080p (most common)
resolve-export -p youtube export.mov

# YouTube 4K
resolve-export -p youtube4k export.mov

# H.265 (smaller file, good quality)
resolve-export -p h265 export.mov

# ProRes (for further editing in another NLE)
resolve-export -p prores export.mov

# WebM (VP9 + Opus, for web embedding)
resolve-export -p webm export.mov

# Near-lossless archive (H.264 CRF 15 + FLAC)
resolve-export -p archive export.mov

# Batch convert a directory
resolve-export -p youtube ~/exports/

# Dry-run preview
resolve-export -n export.mov
```

All outputs use `.delivery.` suffix to avoid naming collisions (e.g., `export.delivery.mp4`).

---

## 8. Font Path Issues

### The Problem

DaVinci Resolve on Linux only imports fonts from `/usr/share/fonts` by default. Fonts installed in `~/.local/share/fonts` or `~/.fonts` are invisible to Resolve's text/titling tools.

### The Fix

```bash
# Run resolve-fonts to update Fusion path map
resolve-fonts
```

This script:
1. Creates `~/.local/share/fonts` and `~/.fonts` if they don't exist
2. Updates the Resolve Fusion path map to include user font directories
3. Refreshes the fontconfig cache

**Manual method:**
1. Open Resolve → Fusion → Fusion Settings → Path Map
2. Find "Fonts:" entry
3. Change from `SystemFonts:` to `SystemFonts:;$HOME/.local/share/fonts:$HOME/.fonts`
4. Restart Resolve

---

## 9. OBS Recording Settings

If recording directly for Resolve on Linux, you can skip the transcode entirely by recording in a Resolve-compatible format:

**OBS Settings → Output → Recording:**
- **Video codec:** DNxHR (or ProRes if you prefer)
- **Audio codec:** PCM s16le 48kHz (or Opus at 256kbps if you prefer lossy)
- **Container:** .mov
- **Resolution/FPS:** Match your project

Chris Titus Tech recommends:
- Video: DNxHR
- Audio: Opus (sounds better than AAC, supported by Resolve in .mkv container)
- If you use Opus, record to .mkv and remux to .mov: `ffmpeg -i recording.mkv -c:v copy -c:a pcm_s24le recording.mov`

**Alternative: Record H.264/Opus in OBS, then auto-transcode with `resolve-watch`.**

---

## 10. Proxy Editing Workflow

For 4K footage on limited hardware, use a proxy workflow:

1. **Create proxy files** (lower resolution, easier to decode):
   ```bash
   resolve-transcode -q lb /path/to/4k_footage   # DNxHR LB proxies
   ```

2. **Edit with proxies** — In Resolve, go to Playback → Proxy Mode → Half Resolution

3. **Re-link to full quality** — Before final render, disable proxy mode and relink to original DNxHR HQ files

Proxy editing is also available natively in Resolve:
- **Playback → Render Cache → Smart** — enables background rendering cache
- This caches decoded frames for smooth playback of heavy timelines

---

## 11. Installation on Arch/EndeavourOS

### Method 1: AUR Package (Recommended)

```bash
# Install from AUR
yay -S davinci-resolve

# For Studio version:
yay -S davinci-resolve-studio
```

Since version 19.1.3-2, you must download the installer from Blackmagic's website and place it in the build directory.

### Method 2: DavinciBox (Distrobox/Container)

```bash
# Container-based approach — avoids dependency hell
# https://github.com/zelikos/davincibox
```

### Post-Install Fixes

```bash
# 1. Verify OpenCL
clinfo -l

# 2. If no OpenCL platforms, install the right driver
# NVIDIA:
sudo pacman -S opencl-nvidia
# AMD:
sudo pacman -S opencl-mesa  # or rocm-opencl-runtime
# Intel:
sudo pacman -S intel-compute-runtime

# 3. Test Resolve launch
resolve-fix      # Launch with library, Wayland/X11, and PRIME fixes

# 4. If Wayland issues, force X11:
QT_QPA_PLATFORM=xcb /opt/resolve/bin/resolve

# 5. Fix audio (PipeWire/PulseAudio)
sudo pacman -S pipewire-alsa
```

---

## 12. Window & UI Issues

### Can't Move or Maximize Resolve Window

On KDE Wayland, Resolve windows may not have title bars or may be unmovable.

**Fix 1:** Hold `Super` key and drag the window.

**Fix 2:** Press `Alt+F10` to maximize.

**Fix 3:** Create a KDE window rule:
- System Settings → Window Management → Window Rules
- Add rule for window class `resolve`
- Set "No titlebar and frame" to "Force: No"

> ### HiDPI / UI Scaling — CORRECT METHOD (Confirmed Working)
>
> Resolve's internal UI scaling is controlled by `DisplayScale` in `config.user.xml`, NOT by Qt environment variables.
>
> **The critical gotcha:** `QT_SCALE_FACTOR` **compounds** with `DisplayScale`. It MUST be 1.0.
>
> **Correct settings:**
>
> ```bash
> # In resolve-fix / desktop launcher:
> export QT_AUTO_SCREEN_SCALE_FACTOR=1
> export QT_SCALE_FACTOR=1.0          # MUST be 1.0 — compounds with DisplayScale!
> ```
>
> ```xml
> <!-- In ~/.local/share/DaVinciResolve/configs/config.user.xml -->
> <DisplayScale>125</DisplayScale>     <!-- This does the actual scaling -->
> ```
>
> | Setting | Value | Purpose |
> |---|---|---|
> | `DisplayScale` (config.user.xml) | 125 | Internal UI scaling (text, icons, panels) |
> | `QT_SCALE_FACTOR` (launcher env) | 1.0 | Must be 1.0 — if 1.25, compounds to 1.56x (too big!) |
> | `QT_AUTO_SCREEN_SCALE_FACTOR` | 1 | Let Qt auto-detect screen (doesn't affect Resolve) |
>
> **How to change:**
> 1. Close Resolve: `killall resolve`
> 2. Edit `~/.local/share/DaVinciResolve/configs/config.user.xml`
> 3. Change `<DisplayScale>125</DisplayScale>` to desired value
> 4. Make sure `QT_SCALE_FACTOR=1.0` in your Resolve launcher
> 5. Relaunch Resolve
>
> **Valid DisplayScale values:** 100, 110, 115, 125, 150, 200 (125 is the sweet spot for 1080p laptops)
>
> **What DOESN'T work:**
> - `QT_SCALE_FACTOR=1.25` alone → Resolve ignores Qt scaling (uses custom rendering)
> - `QT_SCALE_FACTOR=1.25` + `DisplayScale=125` → compounds to ~1.56x (way too big)
> - `QT_QPA_PLATFORM=xcb` (XWayland) → no effect on Resolve's scaling, adds title bar
> - Editing `DisplayScale` while Resolve is running → gets overwritten on exit
>
> ### Window Title Bar (KDE Wayland)
>
> On KDE Wayland, Resolve runs frameless by design (no title bar). This is actually good — more screen space for editing.
>
> - Hold **Super** key and drag to move the window
> - Press **Alt+F10** to maximize
> - If you really want a title bar: create a KDE window rule (System Settings → Window Management → Window Rules → force border for wmclass `resolve`)

---

## 13. IOEncoder Plugins (Studio Only — ❌ Not Available on Free)

### ⚠️ Important: These plugins ONLY work on DaVinci Resolve Studio

The Free version of DaVinci Resolve **does NOT support IOEncoder plugins**. This is a hard limitation — there is no workaround. The IOPlugins system that these plugins use is locked behind the Studio license.

### FFmpeg Encoder Plugin (Studio Only)

Repository: https://github.com/EdvinNilsson/ffmpeg_encoder_plugin

Adds H.264, H.265, and AV1 video encoders to the Deliver tab in Resolve Studio:
- x264 (software H.264)
- x265 (software H.265/HEVC)
- SVT-AV1 (software AV1)
- VAAPI hardware encoding (AMD/Intel)
- NVENC hardware encoding (NVIDIA)

```bash
# Arch AUR
yay -S davinci-ffmpeg-encoder-plugin

# Or manual install:
# Download from: https://github.com/EdvinNilsson/ffmpeg_encoder_plugin/releases
# Unzip to: /opt/resolve/IOPlugins/
```

After installation, these codecs appear in the **Deliver → Codec** dropdown inside Resolve.

### AAC-FDK Encoder Plugin (Studio Only)

Repository: https://github.com/hexitnz/Resolve-Linux-Studio-AAC-FDK-Encoder-plugin

Adds AAC audio encoding to the Deliver tab. This is the only way to get AAC audio output from Resolve on Linux (even Studio doesn't have native AAC).

```bash
sudo pacman -S libfdk-aac
# Clone and build from the repo, or:
yay -S davinci-ffmpeg-encoder-plugin  # includes this
```

### What Chris Titus Tech Said

In his video, Chris Titus mentioned: *"There's actually a FFmpeg encoder plugin I highly recommend installing in your DaVinci Resolve."

He didn't explicitly clarify that this is **Studio-only**. The plugin's own GitHub repo is titled **"FFmpeg Encoder Plugin for DaVinci Resolve Studio"** and states: *"DaVinci Resolve Studio — Required"*. Chris likely uses Resolve Studio (a $295 one-time purchase) for his YouTube workflow.

### For Free Version Users

Since plugins don't work on the Free version, your export workflow remains:

```
Resolve Free → Export DNxHR/PCM .mov
                ↓
         resolve-export (ffmpeg)
                ↓
        H.264/AAC .mp4 for delivery
```

This is exactly what `resolve-export` handles — it's the external alternative to having encoders inside Resolve.

---

## 14. Backup & Migration

### Using resolve-backup

```bash
# Create backup
resolve-backup

# Backup to specific directory
resolve-backup -o ~/backups

# Dry-run preview
resolve-backup -n

# Restore from backup
resolve-backup --restore resolve-backup-20260722.tar.gz
```

**What's backed up:**
- `/opt/resolve` (excluding plugins/ and LUT/)
- `~/.local/share/DaVinciResolve/` (configs, LUTs, scripts, macros)
- `~/.config/Blackmagic Design/DaVinci Resolve/` (preferences)
- `~/.local/share/fonts/` (user fonts)
- `~/.fonts/` (legacy user fonts)
- `~/.config/fontconfig/` (font configuration)

### Manual Backup Points

| Path | Contents |
|---|---|
| `~/.local/share/DaVinciResolve/configs/` | User preferences, keybindings |
| `~/.local/share/DaVinciResolve/LUT/` | Custom LUTs |
| `~/.local/share/DaVinciResolve/Fusion/` | Fusion templates, macros |
| `~/.local/share/DaVinciResolve/logs/` | Debug logs |
| `~/.config/Blackmagic Design/` | Additional user data |

---

## 15. Troubleshooting Checklist

### Resolve won't start

1. ✅ Check OpenCL: `clinfo -l` — must show a GPU platform
2. ✅ Try library fix: `resolve-fix` — preloads newer system libraries
3. ✅ Force X11: `QT_QPA_PLATFORM=xcb /opt/resolve/bin/resolve`
4. ✅ Check logs: `~/.local/share/DaVinciResolve/logs/ResolveDebug.txt`
5. ✅ Check conflicting OpenCL ICDs in `/etc/OpenCL/vendors/`
6. ✅ Reset config: `rm -r ~/.local/share/DaVinciResolve/configs` (returns to onboarding)

### Black video on import

1. ✅ Check codec: `ffprobe input.mp4`
2. ✅ If H.264/H.265 → transcode with `resolve-transcode`
3. ✅ If AAC audio → transcode audio too (`-a pcm` or `-a alac`)

### No audio on import

1. ✅ Check audio codec: `ffprobe input.mp4`
2. ✅ AAC is NOT supported on any Linux version — transcode to PCM/ALAC
3. ✅ Install `pipewire-alsa` if using PipeWire

### GPU memory full error

1. ✅ Switch NVIDIA to performance mode: `envycontrol -s nvidia`
2. ✅ Or use PRIME offload: `__NV_PRIME_RENDER_OFFLOAD=1`
3. ✅ Close other GPU-intensive apps (browsers, games)

### Resolve window won't move/maximize

1. ✅ Hold Super key and drag
2. ✅ Alt+F10 to maximize
3. ✅ Create KDE window rule for `resolve` class

### Fonts missing in titles

1. ✅ Run `resolve-fonts` to update Fusion font path
2. ✅ Or manually add paths in Fusion Settings → Path Map → Fonts
3. ✅ Restart Resolve after font changes

### Audio not playing in timeline

1. ✅ Install `pipewire-alsa`
2. ✅ Check Resolve audio settings: Fairlight → Audio Settings
3. ✅ Test with ALSA: `aplay /usr/share/sounds/alsa/Front_Center.wav`

---

## 16. Example Configuration

A typical working Linux setup looks like this:

| Component | Example |
|---|---|
| Distro | Arch-based, Fedora, Debian/Ubuntu, or another current Linux distro |
| GPU | NVIDIA, AMD, or Intel with a working OpenCL runtime |
| Resolve path | `/opt/resolve` |
| Source media workflow | Transcode H.264/H.265/AAC media before import |
| Editing codec | DNxHR or ProRes for intermediate editing |
| Delivery workflow | Export DNxHR/ProRes from Resolve, then run `resolve-export` |

### Recommended launch environment for hybrid NVIDIA systems

```bash
export __NV_PRIME_RENDER_OFFLOAD=1
export __GLX_VENDOR_LIBRARY_NAME=nvidia
export __VK_LAYER_NV_optimus=NVIDIA_only
export QT_AUTO_SCREEN_SCALE_FACTOR=1
export QT_SCALE_FACTOR=1.0
exec /opt/resolve/bin/resolve "$@"
```

If your desktop needs 125% Resolve UI scaling, set `DisplayScale=125` inside `~/.local/share/DaVinciResolve/configs/config.user.xml` and keep `QT_SCALE_FACTOR=1.0`. Do not set both to 1.25/125%; they compound.

### Installed toolkit commands

| Tool | Purpose |
|---|---|
| `resolve-gui` | Desktop GUI for the toolkit |
| `resolve-transcode` | Batch transcode media for import |
| `resolve-audio` | Convert audio files to Resolve-friendly formats |
| `resolve-export` | Convert Resolve renders for delivery |
| `resolve-fix` | Launch Resolve with compatibility fixes |
| `resolve-backup` | Backup/restore configs and assets |
| `resolve-fonts` | Fix Fusion font paths |
| `resolve-watch` | Auto-transcode a watch folder |
| `resolve-info` | System diagnostics |

---

## 17. Sources & References

- **Chris Titus Tech — resolve-linux**: https://github.com/ChrisTitusTech/resolve-linux
  - Video: https://youtu.be/oHsboGBxUuc
  - Transcode script, backup script, library fix, font fix

- **ArchWiki — DaVinci Resolve**: https://wiki.archlinux.org/title/DaVinci_Resolve
  - Installation, codec support matrix, GPU drivers, troubleshooting

- **jchai01 — DaVinci Resolve Linux Resources**: https://jchai01.github.io/posts/davinci-comprehensive-guide-linux/
  - AAC workaround, incron auto-transcode, Studio magic bytes

- **Alecaddd — FFmpeg Cheatsheet**: https://alecaddd.com/davinci-resolve-ffmpeg-cheatsheet-for-linux/
  - MP4→MOV commands, MKV multi-track, export commands

- **Toxblh — AAC Encoder Plugin (Studio)**: https://github.com/Toxblh/davinci-linux-aac-codec
  - AAC encoding for Studio version

- **hexitnz — AAC-FDK Plugin (Studio)**: https://github.com/hexitnz/Resolve-Linux-Studio-AAC-FDK-Encoder-plugin
  - Alternative AAC encoder plugin

- **DavinciBox (Distrobox)**: https://github.com/zelikos/davincibox
  - Container-based Resolve installation

- **Blackmagic — Supported Codec List (PDF)**: https://documents.blackmagicdesign.com/SupportNotes/DaVinci_Resolve_20_Supported_Codec_List.pdf
  - Official codec support documentation

- **DaVinci Resolve Checker**: https://github.com/Ashark/davinci-resolve-checker
  - Validates system configuration for Resolve

---

*Last updated: 2026-07-22*
