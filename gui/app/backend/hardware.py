import os
import subprocess
import glob

def detect_hybrid_gpu() -> dict:
    """Detect if this is a hybrid GPU system and which vendors."""
    cards = glob.glob("/sys/class/drm/card*/device/vendor")
    vendors = []
    for v in cards:
        try:
            with open(v) as f:
                vid = f.read().strip().lower()
            if "10de" in vid:
                vendors.append("nvidia")
            elif "1002" in vid:
                vendors.append("amd")
            elif "8086" in vid:
                vendors.append("intel")
        except:
            pass

    unique_vendors = set(vendors)
    is_hybrid = len(unique_vendors) > 1
    discrete = "nvidia" if "nvidia" in vendors else ("amd" if "amd" in vendors else None)
    integrated = "intel" if "intel" in vendors else ("amd" if "amd" in vendors and is_hybrid else None)

    return {
        "is_hybrid": is_hybrid,
        "discrete_vendor": discrete,
        "integrated_vendor": integrated,
        "card_vendors": vendors,
    }

def detect_lib_dir() -> str:
    """Find the correct system library directory for this distro."""
    candidates = [
        "/usr/lib/x86_64-linux-gnu",   # Debian/Ubuntu
        "/usr/lib/aarch64-linux-gnu",  # Debian/Ubuntu ARM
        "/usr/lib64",                  # Fedora/RHEL/openSUSE
        "/usr/lib",                    # Arch
    ]
    for path in candidates:
        if os.path.isdir(path) and os.path.exists(os.path.join(path, "libglib-2.0.so.0")):
            return path
    return "/usr/lib"  # fallback

def detect_hw_encoders() -> dict:
    """Check which hardware encoders are available in the system ffmpeg."""
    try:
        encoders = subprocess.run(["ffmpeg", "-hide_banner", "-encoders"],
                                  capture_output=True, text=True, timeout=5)
        text = encoders.stdout + encoders.stderr
    except Exception:
        text = ""

    return {
        "h264_nvenc": "h264_nvenc" in text,    # NVIDIA
        "hevc_nvenc": "hevc_nvenc" in text,    # NVIDIA
        "h264_amf": "h264_amf" in text,        # AMD
        "hevc_amf": "hevc_amf" in text,        # AMD
        "h264_qsv": "h264_qsv" in text,        # Intel QSV
        "hevc_qsv": "hevc_qsv" in text,        # Intel QSV
        "h264_vaapi": "h264_vaapi" in text,    # AMD/Intel VAAPI
        "hevc_vaapi": "hevc_vaapi" in text,    # AMD/Intel VAAPI
        "av1_nvenc": "av1_nvenc" in text,     # NVIDIA AV1
        "av1_amf": "av1_amf" in text,         # AMD AV1
        "av1_qsv": "av1_qsv" in text,         # Intel AV1
        "av1_vaapi": "av1_vaapi" in text,     # AMD/Intel VAAPI AV1
    }

def detect_gpu() -> dict:
    """Detect GPU vendor, model, VRAM, driver. Vendor-neutral."""
    # Try nvidia-smi first (high-fidelity for NVIDIA)
    try:
        out = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,memory.total,memory.used,driver_version", "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=3
        )
        if out.returncode == 0 and out.stdout.strip():
            parts = [p.strip() for p in out.stdout.split(",")]
            if len(parts) >= 4:
                hybrid_info = detect_hybrid_gpu()
                return {
                    "vendor": "nvidia",
                    "model": parts[0],
                    "vram_total": f"{parts[1]} MB",
                    "vram_used": f"{parts[2]} MB",
                    "driver": parts[3],
                    "available": True,
                    "is_hybrid": hybrid_info["is_hybrid"],
                    "discrete_vendor": hybrid_info["discrete_vendor"],
                    "integrated_vendor": hybrid_info["integrated_vendor"],
                    "gpu_name": parts[0],  # for backward compatibility
                }
    except Exception:
        pass

    # Try lspci (universal)
    try:
        lspci_out = subprocess.run(["lspci"], capture_output=True, text=True, timeout=3)
        if lspci_out.returncode == 0:
            gpu_lines = []
            for line in lspci_out.stdout.splitlines():
                if any(x in line.lower() for x in ["vga compatible controller", "3d controller", "display controller"]):
                    gpu_lines.append(line)

            if gpu_lines:
                selected_line = gpu_lines[0]
                for line in gpu_lines:
                    if "nvidia" in line.lower() or "amd" in line.lower() or "ati " in line.lower():
                        selected_line = line
                        break

                model = selected_line
                if ":" in selected_line:
                    model = selected_line.split(":", 2)[-1].strip()

                vendor = "unknown"
                model_lower = model.lower()
                if "nvidia" in model_lower:
                    vendor = "nvidia"
                elif "amd" in model_lower or "ati" in model_lower or "radeon" in model_lower:
                    vendor = "amd"
                elif "intel" in model_lower or "graphics" in model_lower:
                    vendor = "intel"

                vram_total = "N/A"
                vram_paths = glob.glob("/sys/class/drm/card*/device/mem_info_vram_total")
                if vram_paths:
                    try:
                        with open(vram_paths[0]) as f:
                            bytes_val = int(f.read().strip())
                            vram_total = f"{bytes_val // 1024 // 1024} MB"
                    except:
                        pass

                hybrid_info = detect_hybrid_gpu()
                return {
                    "vendor": vendor,
                    "model": model,
                    "vram_total": vram_total,
                    "vram_used": "N/A",
                    "driver": "N/A",
                    "available": True,
                    "is_hybrid": hybrid_info["is_hybrid"],
                    "discrete_vendor": hybrid_info["discrete_vendor"],
                    "integrated_vendor": hybrid_info["integrated_vendor"],
                    "gpu_name": model,
                }
    except Exception:
        pass

    # Fallback to no detection
    hybrid_info = detect_hybrid_gpu()
    return {
        "vendor": "unknown",
        "model": "Software / Integrated",
        "vram_total": "N/A",
        "vram_used": "N/A",
        "driver": "N/A",
        "available": False,
        "is_hybrid": hybrid_info["is_hybrid"],
        "discrete_vendor": hybrid_info["discrete_vendor"],
        "integrated_vendor": hybrid_info["integrated_vendor"],
        "gpu_name": "Software / Integrated",
    }
