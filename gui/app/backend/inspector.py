import os
import subprocess
import json
from pathlib import Path

COLOR_SPACE_MAP = {
    "bt709": "Rec.709",
    "bt2020nc": "Rec.2020 NCL",
    "bt2020c": "Rec.2020 CL",
    "smpte170m": "SMPTE 170M (SD)",
    "smpte240m": "SMPTE 240M",
    "rgb": "RGB",
    "xyz": "XYZ",
    "unspecified": "Unspecified"
}

COLOR_TRANSFER_MAP = {
    "bt709": "Rec.709 (SDR)",
    "smpte2084": "PQ (HDR)",
    "arib-std-b67": "HLG (HDR)",
    "bt2020-10": "Rec.2020 10-bit",
    "srgb": "sRGB",
    "linear": "Linear"
}

COLOR_PRIMARIES_MAP = {
    "bt709": "Rec.709",
    "bt2020": "Rec.2020",
    "smpte170m": "SMPTE 170M (SD)",
    "smpte240m": "SMPTE 240M",
    "bt470bg": "PAL/SECAM",
    "bt470m": "NTSC"
}

COLOR_RANGE_MAP = {
    "tv": "Limited (TV 16-235)",
    "pc": "Full (PC 0-255)"
}

PIXEL_FORMAT_MAP = {
    "yuv420p": ("8-bit", "4:2:0"),
    "yuv422p": ("8-bit", "4:2:2"),
    "yuv444p": ("8-bit", "4:4:4"),
    "yuv420p10le": ("10-bit", "4:2:0"),
    "yuv422p10le": ("10-bit", "4:2:2"),
    "yuv444p10le": ("10-bit", "4:4:4"),
    "yuv420p12le": ("12-bit", "4:2:0"),
    "yuv422p12le": ("12-bit", "4:2:2"),
    "yuv444p12le": ("12-bit", "4:4:4"),
    "yuv420p16le": ("16-bit", "4:2:0"),
    "rgb24": ("8-bit", "RGB"),
    "rgb48le": ("16-bit", "RGB"),
    "gbrp10le": ("10-bit", "RGB"),
    "nv12": ("8-bit", "4:2:0 (interleaved)"),
    "p010le": ("10-bit", "4:2:0 (interleaved)")
}

RESOLVE_VIDEO_CODECS = {
    "h264": {"supported": False, "name": "H.264 (AVC)", "note": "Studio version only on Linux"},
    "hevc": {"supported": False, "name": "H.265 (HEVC)", "note": "Studio version only on Linux"},
    "av1": {"supported": True, "name": "AV1", "note": "GPU-accelerated decode (NVIDIA)"},
    "dnxhd": {"supported": True, "name": "DNxHD / DNxHR", "note": "Native professional intermediate"},
    "prores": {"supported": True, "name": "ProRes", "note": "Native professional master"},
    "vp9": {"supported": True, "name": "VP9", "note": "Supported in Resolve"},
    "ffv1": {"supported": True, "name": "FFV1", "note": "Supported in Resolve"},
    "cineform": {"supported": True, "name": "CineForm", "note": "Supported in Resolve"},
    "none": {"supported": True, "name": "No Video Stream", "note": "Audio-only file"}
}

RESOLVE_AUDIO_CODECS = {
    "aac": {"supported": False, "name": "AAC", "note": "Not supported on Linux (Free or Studio)"},
    "opus": {"supported": False, "name": "Opus", "note": "Not supported natively in Resolve"},
    "vorbis": {"supported": False, "name": "Vorbis", "note": "Not supported natively in Resolve"},
    "pcm_s16le": {"supported": True, "name": "PCM 16-bit", "note": "Universal support"},
    "pcm_s24le": {"supported": True, "name": "PCM 24-bit", "note": "Universal support"},
    "pcm_s32le": {"supported": True, "name": "PCM 32-bit", "note": "Universal support"},
    "flac": {"supported": True, "name": "FLAC", "note": "Lossless, supported"},
    "alac": {"supported": True, "name": "ALAC", "note": "Apple Lossless, supported"},
    "mp3": {"supported": True, "name": "MP3", "note": "Supported"},
    "ac3": {"supported": True, "name": "AC-3", "note": "Supported"},
    "none": {"supported": True, "name": "No Audio Stream", "note": "Mute video stream"}
}

def compute_resolve_compat(vcodec: str, acodec: str) -> dict:
    vcodec_clean = (vcodec or "none").lower()
    acodec_clean = (acodec or "none").lower()

    v_match = None
    for k, info in RESOLVE_VIDEO_CODECS.items():
        if k == vcodec_clean or k in vcodec_clean:
            v_match = info
            break
    if not v_match:
        v_match = {"supported": False, "name": vcodec.upper() if vcodec else "Unknown", "note": "Unknown or unsupported video codec"}

    a_match = None
    for k, info in RESOLVE_AUDIO_CODECS.items():
        if k == acodec_clean or k in acodec_clean:
            a_match = info
            break
    if not a_match:
        a_match = {"supported": False, "name": acodec.upper() if acodec else "Unknown", "note": "Unknown or unsupported audio codec"}

    v_ok = bool(v_match["supported"])
    a_ok = bool(a_match["supported"])

    issues = []
    structured_issues = []

    if not v_ok and vcodec_clean != "none":
        video_note = "Studio-only on Linux" if vcodec_clean in ["h264", "hevc"] else v_match["note"]
        structured_issues.append({"label": "Video", "text": f"{v_match['name']} is {video_note}."})
        issues.append(f"Video Codec '{v_match['name']}': {v_match['note']}")

    if not a_ok and acodec_clean != "none":
        audio_note = "unsupported on Linux" if acodec_clean in ["aac", "opus", "vorbis"] else a_match["note"]
        structured_issues.append({"label": "Audio", "text": f"{a_match['name']} is {audio_note}."})
        issues.append(f"Audio Codec '{a_match['name']}': {a_match['note']}")

    if v_ok and a_ok:
        verdict = "full"
        badge_text = "Ready for Resolve"
        badge_color = "#00e5ff"
        title = "Ready for Resolve"
        summary = "Video and audio are supported by Resolve on Linux. You can import this file directly."
    elif v_ok and not a_ok:
        verdict = "partial_audio"
        badge_text = "Audio needs conversion"
        badge_color = "#ffb74d"
        title = "Audio needs conversion"
        summary = "Resolve Free on Linux cannot play back the audio stream in this file."
    elif not v_ok and a_ok:
        verdict = "partial_video"
        badge_text = "Needs transcode"
        badge_color = "#ffb74d"
        title = "Needs transcode"
        summary = "Resolve Free on Linux cannot import this file as-is."
    else:
        verdict = "incompatible"
        badge_text = "Needs transcode"
        badge_color = "#ff5252"
        title = "Needs transcode"
        summary = "Resolve Free on Linux cannot import this file as-is."

    return {
        "verdict": verdict,
        "badge_text": badge_text,
        "badge_color": badge_color,
        "v_ok": v_ok,
        "a_ok": a_ok,
        "v_name": v_match["name"],
        "a_name": a_match["name"],
        "issues": issues,
        "title": title,
        "summary": summary,
        "video_status": "OK" if v_ok else "Needs transcode",
        "audio_status": "OK" if a_ok else "Needs transcode",
        "structured_issues": structured_issues
    }

def get_file_info(file_path: str) -> dict:
    """Inspects a media file using ffprobe and returns concise summary specs."""
    info = {
        "path": file_path,
        "filename": os.path.basename(file_path),
        "filesize_bytes": 0,
        "filesize_str": "0 MB",
        "duration_sec": 0.0,
        "duration_str": "00:00",
        "width": 0,
        "height": 0,
        "resolution_str": "N/A",
        "vcodec": "none",
        "acodec": "none",
        "media_type": "unknown",
        "bitrate_mbps": 0.0,
        "valid": False
    }

    if not os.path.exists(file_path):
        return info

    try:
        size = os.path.getsize(file_path)
        info["filesize_bytes"] = size
        info["filesize_str"] = format_size(size)

        cmd = [
            "ffprobe", "-v", "quiet",
            "-print_format", "json",
            "-show_format", "-show_streams",
            file_path
        ]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
        if res.returncode == 0:
            data = json.loads(res.stdout)
            format_data = data.get("format", {})
            streams = data.get("streams", [])

            info["duration_sec"] = float(format_data.get("duration", 0.0))
            info["duration_str"] = format_duration(info["duration_sec"])

            fmt_bitrate = int(format_data.get("bit_rate", 0))
            if fmt_bitrate > 0:
                info["bitrate_mbps"] = round(fmt_bitrate / 1_000_000, 2)
            elif info["duration_sec"] > 0:
                info["bitrate_mbps"] = round((size * 8) / info["duration_sec"] / 1_000_000, 2)

            for s in streams:
                codec_type = s.get("codec_type")
                if codec_type == "video" and info["vcodec"] == "none":
                    info["vcodec"] = s.get("codec_name", "unknown")
                    info["width"] = s.get("width", 0)
                    info["height"] = s.get("height", 0)
                    if info["width"] and info["height"]:
                        if info["width"] >= 3840:
                            info["resolution_str"] = f"{info['width']}x{info['height']} (4K)"
                        elif info["width"] >= 1920:
                            info["resolution_str"] = f"{info['width']}x{info['height']} (1080p)"
                        else:
                            info["resolution_str"] = f"{info['width']}x{info['height']}"
                    info["media_type"] = "video"
                elif codec_type == "audio" and info["acodec"] == "none":
                    info["acodec"] = s.get("codec_name", "unknown")
                    if info["media_type"] == "unknown":
                        info["media_type"] = "audio"

            info["valid"] = True
    except Exception:
        pass

    return info

def get_detailed_media_info(file_path: str) -> dict:
    """Deep inspection of a media file. Returns structured details for Inspector tab."""
    summary = get_file_info(file_path)
    if not summary.get("valid"):
        return {"summary": summary, "valid": False}

    detailed = {
        "summary": summary,
        "valid": True,
        "container": {},
        "video": None,
        "audio_streams": [],
        "compat": compute_resolve_compat(summary.get("vcodec"), summary.get("acodec"))
    }

    try:
        cmd = [
            "ffprobe", "-v", "quiet",
            "-print_format", "json",
            "-show_format", "-show_streams",
            file_path
        ]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
        if res.returncode == 0:
            data = json.loads(res.stdout)
            fmt = data.get("format", {})
            streams = data.get("streams", [])

            # Container
            tags = fmt.get("tags", {})
            created = tags.get("creation_time", "N/A")
            device = tags.get("com.android.version") or tags.get("encoder") or tags.get("model") or "N/A"
            bitrate_raw = int(fmt.get("bit_rate", 0))
            bitrate_str = f"{round(bitrate_raw / 1_000_000, 2)} Mbps" if bitrate_raw > 0 else "N/A"

            detailed["container"] = {
                "format_long": fmt.get("format_long_name", "N/A"),
                "size_str": format_size(int(fmt.get("size", 0))),
                "duration_str": format_duration(float(fmt.get("duration", 0.0))),
                "bitrate_str": bitrate_str,
                "nb_streams": fmt.get("nb_streams", len(streams)),
                "created": created,
                "device": device
            }

            # Streams
            for s in streams:
                stype = s.get("codec_type")
                cname = s.get("codec_name", "unknown")
                clong = s.get("codec_long_name", cname.upper())

                if stype == "video" and detailed["video"] is None:
                    w = s.get("width", 0)
                    h = s.get("height", 0)

                    # Frame rate parsing
                    fps_str = "N/A"
                    r_fps = s.get("r_frame_rate", "")
                    if "/" in r_fps:
                        num, den = map(float, r_fps.split("/"))
                        if den > 0: fps_str = f"{round(num / den, 2)} fps"

                    pix_fmt = s.get("pix_fmt", "")
                    bit_depth, chroma = PIXEL_FORMAT_MAP.get(pix_fmt, ("N/A", "N/A"))

                    cspace = COLOR_SPACE_MAP.get(s.get("color_space"), s.get("color_space", "Unspecified"))
                    ctransfer = COLOR_TRANSFER_MAP.get(s.get("color_transfer"), s.get("color_transfer", "Unspecified"))
                    cprimaries = COLOR_PRIMARIES_MAP.get(s.get("color_primaries"), s.get("color_primaries", "Unspecified"))
                    crange = COLOR_RANGE_MAP.get(s.get("color_range"), s.get("color_range", "Unspecified"))

                    v_bitrate = int(s.get("bit_rate", 0))
                    v_bitrate_str = f"{round(v_bitrate / 1_000_000, 2)} Mbps" if v_bitrate > 0 else "N/A"
                    nb_frames = s.get("nb_frames") or "N/A"
                    aspect = s.get("display_aspect_ratio") or f"{w}:{h}" if (w and h) else "N/A"

                    detailed["video"] = {
                        "codec": cname.upper(),
                        "codec_long": clong,
                        "profile": s.get("profile", "N/A"),
                        "resolution": f"{w} × {h}" if (w and h) else "N/A",
                        "fps": fps_str,
                        "bit_depth": bit_depth,
                        "chroma": chroma,
                        "color_space": cspace,
                        "color_transfer": ctransfer,
                        "color_primaries": cprimaries,
                        "color_range": crange,
                        "bitrate": v_bitrate_str,
                        "nb_frames": nb_frames,
                        "aspect": aspect
                    }
                elif stype == "audio":
                    s_rate = int(s.get("sample_rate", 0))
                    s_rate_str = f"{round(s_rate / 1000, 1)} kHz" if s_rate > 0 else "N/A"
                    chans = s.get("channels", 0)
                    ch_layout = s.get("channel_layout") or (f"{chans} Ch" if chans else "N/A")
                    a_bitrate = int(s.get("bit_rate", 0))
                    a_bitrate_str = f"{round(a_bitrate / 1000, 0)} kbps" if a_bitrate > 0 else "N/A"

                    detailed["audio_streams"].append({
                        "codec": cname.upper(),
                        "codec_long": clong,
                        "profile": s.get("profile", "N/A"),
                        "sample_rate": s_rate_str,
                        "channels": f"{ch_layout} ({chans}.0)" if chans else "N/A",
                        "sample_fmt": s.get("sample_fmt", "N/A"),
                        "bitrate": a_bitrate_str
                    })
    except Exception:
        pass

    return detailed

def format_size(bytes_val: int) -> str:
    """Formats bytes into human readable KB, MB, GB."""
    if bytes_val < 1024:
        return f"{bytes_val} B"
    elif bytes_val < 1024 * 1024:
        return f"{bytes_val / 1024:.1f} KB"
    elif bytes_val < 1024 * 1024 * 1024:
        return f"{bytes_val / (1024 * 1024):.1f} MB"
    else:
        return f"{bytes_val / (1024 * 1024 * 1024):.2f} GB"

def format_duration(seconds: float) -> str:
    """Formats seconds into MM:SS or HH:MM:SS."""
    sec = int(seconds)
    hrs = sec // 3600
    mins = (sec % 3600) // 60
    secs = sec % 60
    if hrs > 0:
        return f"{hrs:02d}:{mins:02d}:{secs:02d}"
    return f"{mins:02d}:{secs:02d}"

def calculate_estimated_output(duration_sec: float, mode: str, profile_or_preset: str, codec: str = "dnxhr", resolution: str = "original", crf_override: int = None, source_bitrate_mbps: float = 0.0) -> dict:
    if duration_sec <= 0:
        return {"est_bytes": 0, "est_str": "~0 MB", "bitrate_mbps": 0.0}

    target_key = profile_or_preset.lower()

    if mode == "video":
        if codec == "av1":
            fallback_source_mbps = 10.0
            src_mbps = source_bitrate_mbps if source_bitrate_mbps > 0 else fallback_source_mbps
            av1_ratios = {"lb": 0.40, "sq": 0.70, "hq": 1.10, "hqx": 1.60, "444": 2.20}
            ratio = av1_ratios.get(target_key, 0.70)
            bitrate_mbps = round(src_mbps * ratio, 1)
        else:
            dnxhr_bitrates = {"lb": 100.0, "sq": 220.0, "hq": 440.0, "hqx": 660.0, "444": 880.0}
            bitrate_mbps = dnxhr_bitrates.get(target_key, 220.0)
    elif mode == "export":
        export_bitrates = {
            "youtube": 18.0, "youtube4k": 45.0, "h265": 12.0, "h2654k": 25.0,
            "nvenc": 18.0, "nvenc265": 12.0, "prores": 220.0, "webm": 8.0,
            "archive": 35.0, "av1": 6.0, "av14k": 12.0,
            "h264_amf": 16.0, "hevc_amf": 10.0, "h264_qsv": 16.0, "hevc_qsv": 10.0,
            "h264_vaapi": 18.0, "hevc_vaapi": 12.0,
            "av1_nvenc": 8.0, "av1_amf": 8.0, "av1_qsv": 8.0, "av1_vaapi": 8.0
        }
        bitrate_mbps = export_bitrates.get(target_key, 18.0)
        res = resolution.lower() if resolution else "original"
        if res == "4k": bitrate_mbps *= 2.5
        elif res == "1440p": bitrate_mbps *= 1.7
        elif res == "720p": bitrate_mbps *= 0.5
        elif res == "480p": bitrate_mbps *= 0.25

        if crf_override is not None and target_key in ("youtube", "youtube4k", "h265", "h2654k", "av1", "av14k", "webm", "archive"):
            default_crf_map = {"youtube": 18, "youtube4k": 20, "h265": 22, "h2654k": 24, "av1": 30, "av14k": 32, "webm": 30, "archive": 15}
            default_crf = default_crf_map.get(target_key, 18)
            diff = default_crf - crf_override
            bitrate_mbps *= (1.08 ** diff)
    else:
        audio_bitrates = {"wav": 2.3, "flac": 1.1, "alac": 1.2, "mp3": 0.32}
        bitrate_mbps = audio_bitrates.get(target_key, 2.3)

    bitrate_mbps = round(bitrate_mbps, 1)
    bytes_per_sec = (bitrate_mbps * 1_000_000) / 8.0
    est_bytes = int(duration_sec * bytes_per_sec)

    return {
        "est_bytes": est_bytes,
        "est_str": f"~{format_size(est_bytes)}",
        "bitrate_mbps": bitrate_mbps
    }
