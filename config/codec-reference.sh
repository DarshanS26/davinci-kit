# DaVinci Resolve codec cheat sheet for Linux
# Reference: https://documents.blackmagicdesign.com/SupportNotes/DaVinci_Resolve_20_Supported_Codec_List.pdf
# Also: ArchWiki, Chris Titus Tech, community research

# ═══════════════════════════════════════════════════════════════════════════════
# CODEC SUPPORT MATRIX — DaVinci Resolve on Linux
# ═══════════════════════════════════════════════════════════════════════════════

# ── Free Version ──────────────────────────────────────────────────────────────
# VIDEO:
#   ❌ H.264 decode/encode
#   ❌ H.265/HEVC decode/encode
#   ✅ DNxHR decode/encode      ← USE THIS
#   ✅ ProRes decode/encode
#   ✅ AV1 decode only (if audio is PCM/MP3)
#
# AUDIO:
#   ❌ AAC (not supported on ANY Linux version, even Studio)
#   ✅ PCM/WAV
#   ✅ MP3
#   ✅ FLAC
#   ✅ ALAC (Apple Lossless) — good for .mov containers
#   ✅ Opus (in .mkv)

# ── Studio Version ────────────────────────────────────────────────────────────
# VIDEO:
#   ✅ H.264 decode/encode
#   ✅ H.265/HEVC decode/encode
#   ✅ All Free codecs
#
# AUDIO:
#   ❌ AAC (still NOT supported on Linux, even Studio)
#   ✅ Everything the Free version supports

# ═══════════════════════════════════════════════════════════════════════════════
# RECOMMENDED FFMPEG TRANSCODE COMMANDS
# ═══════════════════════════════════════════════════════════════════════════════

# ── Import: Convert footage for Resolve ────────────────────────────────────────

# H.264 + AAC → DNxHR HQ + PCM (most common MP4/phone footage)
# ffmpeg -i input.mp4 -c:v dnxhd -profile:v dnxhr_hq -pix_fmt yuv422p -c:a pcm_s24le -ar 48000 -ac 2 output.mov

# H.264 + AAC → DNxHR HQ + ALAC (smaller audio, still lossless)
# ffmpeg -i input.mp4 -c:v dnxhd -profile:v dnxhr_hq -pix_fmt yuv422p -c:a alac output.mov

# H.264 + PCM/MP3 → DNxHR (audio copy, video only transcode)
# ffmpeg -i input.mp4 -c:v dnxhd -profile:v dnxhr_hq -pix_fmt yuv422p -c:a copy output.mov

# AV1 + AAC → copy video, transcode audio only
# ffmpeg -i input.mp4 -c:v copy -c:a pcm_s32le output.mp4

# Proxy quality for faster editing (smaller files)
# ffmpeg -i input.mp4 -c:v dnxhd -profile:v dnxhr_lb -pix_fmt yuv422p -c:a pcm_s16le output.mov

# ── Export: Convert Resolve output for delivery ────────────────────────────────

# YouTube H.264 1080p (recommended)
# ffmpeg -i resolve_export.mov -c:v libx264 -crf 18 -preset slow -pix_fmt yuv420p -c:a aac -b:a 192k -movflags +faststart output.mp4

# YouTube H.264 4K
# ffmpeg -i resolve_export.mov -c:v libx264 -crf 20 -preset slow -pix_fmt yuv420p -c:a aac -b:a 192k -movflags +faststart output.mp4

# H.265 (smaller file, good quality)
# ffmpeg -i resolve_export.mov -c:v libx265 -crf 22 -preset medium -pix_fmt yuv420p -c:a aac -b:a 192k -movflags +faststart output.mp4

# ProRes 422 HQ (for further editing in another NLE)
# ffmpeg -i resolve_export.mov -c:v prores_ks -profile:v 3 -pix_fmt yuv422p10le -c:a pcm_s24le output.mov

# Archive/near-lossless
# ffmpeg -i resolve_export.mov -c:v libx264 -crf 15 -preset slow -pix_fmt yuv420p -c:a flac output.mkv

# ── OBS Studio Recommended Settings ────────────────────────────────────────────
# If recording directly for Resolve on Linux:
#   Video codec: DNxHR (set in OBS → Settings → Output → Recording)
#   Audio codec: PCM (s16le, 48kHz) or Opus
#   Container:   .mov
#   Alternative:  Record with Opus audio in MKV, then remux to MOV

# ── DNxHR Quality Reference ───────────────────────────────────────────────────
# Profile   | Bitrate      | Use Case
# ----------|-------------|--------------------------------------------
# dnxhr_lb  | ~100 Mbps   | Proxy/offline editing
# dnxhr_sq  | ~220 Mbps   | Standard quality
# dnxhr_hq  | ~440 Mbps   | High quality (DEFAULT, best balance)
# dnxhr_hqx | ~660 Mbps   | High quality, 12-bit
# dnxhr_444 | ~880 Mbps   | Full 4:4:4, maximum quality

# ── Audio Codec Comparison ────────────────────────────────────────────────────
# Codec      | Size     | Quality  | Resolve Support | Notes
# -----------|----------|----------|-----------------|----------------------------
# PCM s16le  | Large    | Lossless | ✅               | 16-bit, good default
# PCM s24le  | Larger   | Lossless | ✅               | 24-bit, Resolve standard
# ALAC       | Medium   | Lossless | ✅               | Apple Lossless, smaller than PCM
# FLAC       | Medium   | Lossless | ✅ (in .mkv)    | Best lossless compression
# Opus       | Small    | Lossy    | ✅ (in .mkv)    | Best lossy codec, NOT in .mov
# AAC        | Smallest | Lossy    | ❌               | NOT supported on Linux Resolve