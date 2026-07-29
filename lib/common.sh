#!/usr/bin/env bash
# =============================================================================
#  resolve-kit/lib/common.sh — Shared functions for resolve-kit scripts
#
#  Source this file in any resolve-kit script:
#    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
#    source "${SCRIPT_DIR}/../lib/common.sh"
#    # Or if installed on PATH:
#    source "$(dirname "$(which resolve-transcode)")/../lib/common.sh"
# =============================================================================

# ── Color helpers ─────────────────────────────────────────────────────────────
if [[ -t 1 ]]; then
  RK_RED='\033[0;31m'; RK_GREEN='\033[0;32m'; RK_YELLOW='\033[1;33m'
  RK_CYAN='\033[0;36m'; RK_BOLD='\033[1m'; RK_DIM='\033[2m'; RK_RESET='\033[0m'
else
  RK_RED=''; RK_GREEN=''; RK_YELLOW=''; RK_CYAN=''; RK_BOLD=''; RK_DIM=''; RK_RESET=''
fi

rk_info()    { echo -e "${RK_CYAN}[INFO]${RK_RESET}  $*"; }
rk_ok()      { echo -e "${RK_GREEN}[OK]${RK_RESET}    $*"; }
rk_warn()    { echo -e "${RK_YELLOW}[WARN]${RK_RESET}  $*"; }
rk_err()     { echo -e "${RK_RED}[ERR]${RK_RESET}   $*" >&2; }
rk_header()  { echo -e "\n${RK_BOLD}$*${RK_RESET}"; }

# ── Constants ──────────────────────────────────────────────────────────────────
RK_RESOLVE_DIR="/opt/resolve"
RK_RESOLVE_BIN="/opt/resolve/bin/resolve"
RK_RESOLVE_CONFIG_DIR="$HOME/.local/share/DaVinciResolve"
RK_RESOLVE_CONFIG="$HOME/.local/share/DaVinciResolve/configs/config.user.xml"
RK_RESOLVE_BLACKMAGIC_CONFIG="$HOME/.config/Blackmagic Design/DaVinci Resolve"
RK_DEFAULT_QUALITY="sq"
RK_DEFAULT_AUDIO_MODE="auto"

# ── DNxHR profiles ────────────────────────────────────────────────────────────
RK_DNXHR_PROFILES="lb sq hq hqx 444"

rk_dnxhr_profile() {
  case "$1" in
    lb)  echo "dnxhr_lb"  ;;
    sq)  echo "dnxhr_sq"  ;;
    hq)  echo "dnxhr_hq"  ;;
    hqx) echo "dnxhr_hqx" ;;
    444) echo "dnxhr_444" ;;
    *)   return 1 ;;
  esac
}

rk_dnxhr_pix_fmt() {
  case "$1" in
    lb|sq|hq) echo "yuv422p" ;;
    hqx)      echo "yuv422p12le" ;;
    444)      echo "yuv444p12le" ;;
    *)        return 1 ;;
  esac
}

rk_dnxhr_description() {
  case "$1" in
    lb)  echo "Low bitrate, offline/proxy editing (~100 Mbps)" ;;
    sq)  echo "Standard quality (~220 Mbps)" ;;
    hq)  echo "High quality (~440 Mbps)" ;;
    hqx) echo "High quality, 12-bit (~660 Mbps)" ;;
    444) echo "Full 4:4:4, maximum quality (~880 Mbps)" ;;
    *)   return 1 ;;
  esac
}

# ── File extension patterns ───────────────────────────────────────────────────
RK_VIDEO_EXTS="mp4|mkv|avi|mov|mxf|wmv|flv|webm|ts|m2ts|mts|mpg|mpeg|m4v|3gp|ogv|vob|rmvb|rm|asf|divx|dv|f4v|hevc|h264|h265"
RK_AUDIO_EXTS="mp3|aac|flac|ogg|m4a|wma|aiff|aif|opus|wav|ape|alac|mka|ac3|dts|eac3|amr|au|ra"

# ── Media detection ───────────────────────────────────────────────────────────
rk_get_media_type() {
  local file="$1"
  local has_video has_audio
  has_video=$(ffprobe -v quiet -select_streams v:0 \
    -show_entries stream=codec_type -of csv=p=0 "$file" 2>/dev/null | head -1)
  has_audio=$(ffprobe -v quiet -select_streams a:0 \
    -show_entries stream=codec_type -of csv=p=0 "$file" 2>/dev/null | head -1)

  if [[ "$has_video" == "video" ]]; then echo "video"
  elif [[ "$has_audio" == "audio" ]]; then echo "audio"
  else echo "unknown"
  fi
}

rk_get_audio_codec() {
  local file="$1"
  ffprobe -v quiet -select_streams a:0 \
    -show_entries stream=codec_name -of csv=p=0 "$file" 2>/dev/null | head -1
}

rk_get_video_codec() {
  local file="$1"
  ffprobe -v quiet -select_streams v:0 \
    -show_entries stream=codec_name -of csv=p=0 "$file" 2>/dev/null | head -1
}

# ── Dependency checking ────────────────────────────────────────────────────────
rk_check_deps() {
  local missing=()
  for cmd in ffmpeg ffprobe; do
    command -v "$cmd" &>/dev/null || missing+=("$cmd")
  done
  if [[ ${#missing[@]} -gt 0 ]]; then
    rk_err "Missing required tools: ${missing[*]}"
    echo "  Arch: sudo pacman -S ffmpeg" >&2
    return 1
  fi

  local encoders
  encoders="$(ffmpeg -hide_banner -encoders 2>/dev/null || true)"
  if ! echo "$encoders" | grep -qE '\s+dnxhd\s+'; then
    rk_err "ffmpeg build does not include the DNxHD/DNxHR encoder."
    echo "  Arch: sudo pacman -S ffmpeg" >&2
    return 1
  fi
}

# ── Smart audio args ──────────────────────────────────────────────────────────
# Returns ffmpeg audio args based on the audio mode and source codec
# Usage: rk_audio_args <file> <audio_mode>
#   audio_mode: auto | pcm | alac
rk_audio_args() {
  local file="$1"
  local mode="$2"
  local acodec

  case "$mode" in
    alac)
      echo "-c:a alac"
      ;;
    pcm)
      echo "-c:a pcm_s24le -ar 48000 -ac 2"
      ;;
    auto)
      acodec=$(rk_get_audio_codec "$file")
      case "$acodec" in
        pcm_*|flac|alac)
          # Already lossless — copy or compatible format
          if [[ "$acodec" == "flac" ]]; then
            echo "-c:a flac"
          elif [[ "$acodec" == "alac" ]]; then
            echo "-c:a alac"
          else
            echo "-c:a copy"
          fi
          ;;
        ""|none)
          echo "-an"
          ;;
        *)
          # AAC, Opus, MP3, etc — transcode to PCM 24-bit
          echo "-c:a pcm_s24le -ar 48000 -ac 2"
          ;;
      esac
      ;;
    *)
      rk_err "Unknown audio mode: $mode" >&2
      return 1
      ;;
  esac
}

# ── Resolve system info ───────────────────────────────────────────────────────
rk_is_resolve_installed() {
  [[ -d "$RK_RESOLVE_DIR" ]]
}

rk_get_resolve_version() {
  if [[ -f "$RK_RESOLVE_BIN" ]]; then
    strings "$RK_RESOLVE_BIN" 2>/dev/null | grep -oP '\d+\.\d+\.\d+' | head -1 || echo "unknown"
  else
    echo "not installed"
  fi
}

rk_get_gpu() {
  if command -v nvidia-smi &>/dev/null && nvidia-smi --query-gpu=name --format=csv,noheader 2>/dev/null | grep -q .; then
    echo "nvidia:$(nvidia-smi --query-gpu=name --format=csv,noheader 2>/dev/null | head -1)"
  elif command -v lspci &>/dev/null; then
    local line
    line=$(lspci 2>/dev/null | grep -iE 'vga|3d|display' | head -1)
    if echo "$line" | grep -qi amd; then
      echo "amd:$line"
    elif echo "$line" | grep -qi intel; then
      echo "intel:$line"
    else
      echo "unknown:$line"
    fi
  else
    echo "unknown:Not detected"
  fi
}

rk_get_opencl_info() {
  if command -v clinfo &>/dev/null; then
    clinfo -l 2>/dev/null || echo "no platforms"
  else
    echo "clinfo not installed"
  fi
}

rk_detect_lib_dir() {
  for dir in /usr/lib/x86_64-linux-gnu /usr/lib64 /usr/lib; do
    if [[ -f "$dir/libglib-2.0.so.0" ]]; then
      echo "$dir"
      return
    fi
  done
  echo "/usr/lib"
}

rk_check_library_mismatch() {
  local libdir
  libdir="$(rk_detect_lib_dir)"
  local mismatches=0
  for lib in libglib-2.0.so.0 libgio-2.0.so.0 libgmodule-2.0.so.0 libgobject-2.0.so.0; do
    local sys_ver res_ver
    sys_ver=$(readlink "$libdir/$lib" 2>/dev/null || echo "missing")
    res_ver=$(readlink /opt/resolve/libs/$lib 2>/dev/null || echo "missing")
    if [[ "$sys_ver" != "missing" ]] && [[ "$res_ver" != "missing" ]]; then
      local sys_num res_num
      sys_num=$(echo "$sys_ver" | grep -oP '\d+\.\d+\.\d+' | head -1)
      res_num=$(echo "$res_ver" | grep -oP '\d+\.\d+\.\d+' | head -1)
      if [[ "$sys_num" > "$res_num" ]]; then
        ((mismatches++))
      fi
    fi
  done
  echo "$mismatches"
}