import os
import shutil
import subprocess
import json
import re
from pathlib import Path

def get_resolve_kit_dir() -> Path:
    """Returns the root directory of the resolve-kit project."""
    # Assuming this file is at gui/app/backend/system.py
    current_file = Path(__file__).resolve()
    return current_file.parents[3]

def get_bin_path(tool_name: str) -> str:
    """Gets absolute path to a resolve-kit bin script."""
    kit_dir = get_resolve_kit_dir()
    bin_script = kit_dir / "bin" / tool_name
    if bin_script.exists():
        return str(bin_script)
    # Fallback to system PATH
    sys_path = shutil.which(tool_name)
    return sys_path or tool_name

def check_gpu_info() -> dict:
    """Queries NVIDIA GPU information via nvidia-smi if available."""
    info = {"gpu_name": "Unknown GPU", "vram_total": "N/A", "vram_used": "N/A", "driver": "N/A", "available": False}
    if shutil.which("nvidia-smi"):
        try:
            res = subprocess.run(
                ["nvidia-smi", "--query-gpu=name,memory.total,memory.used,driver_version", "--format=csv,noheader,nounits"],
                capture_output=True, text=True, timeout=3
            )
            if res.returncode == 0 and res.stdout.strip():
                parts = [p.strip() for p in res.stdout.strip().split(",")]
                if len(parts) >= 4:
                    info["gpu_name"] = parts[0]
                    info["vram_total"] = f"{parts[1]} MB"
                    info["vram_used"] = f"{parts[2]} MB"
                    info["driver"] = parts[3]
                    info["available"] = True
        except Exception:
            pass
    return info

def check_opencl_info() -> dict:
    """Checks OpenCL platforms using clinfo or fallback."""
    info = {"platform": "Unknown", "available": False, "devices": []}
    if shutil.which("clinfo"):
        try:
            res = subprocess.run(["clinfo", "-l"], capture_output=True, text=True, timeout=3)
            if res.returncode == 0:
                lines = [line.strip() for line in res.stdout.strip().splitlines() if line.strip()]
                info["devices"] = lines
                info["available"] = len(lines) > 0
                info["platform"] = lines[0] if lines else "No platforms"
        except Exception:
            pass
    return info

def check_glib_mismatches() -> dict:
    """Checks for system vs DaVinci Resolve GLib library mismatches."""
    libs = ["libglib-2.0.so.0", "libgio-2.0.so.0", "libgmodule-2.0.so.0", "libgobject-2.0.so.0"]
    mismatches = []
    resolve_lib_dir = Path("/opt/resolve/libs")
    sys_lib_dir = Path("/usr/lib")

    if not resolve_lib_dir.exists():
        return {"resolve_installed": False, "count": 0, "details": []}

    for lib in libs:
        sys_target = (sys_lib_dir / lib)
        res_target = (resolve_lib_dir / lib)
        if sys_target.exists() and res_target.exists():
            try:
                sys_real = sys_target.resolve().name
                res_real = res_target.resolve().name
                if sys_real != res_real:
                    mismatches.append({"lib": lib, "system": sys_real, "resolve": res_real})
            except Exception:
                pass

    return {
        "resolve_installed": True,
        "count": len(mismatches),
        "details": mismatches
    }

def get_disk_usage(path: str = None) -> dict:
    """Gets disk usage stats for the given directory path (default: home)."""
    target = path if path and os.path.exists(path) else os.path.expanduser("~")
    total, used, free = shutil.disk_usage(target)
    gb = 1024 ** 3
    return {
        "path": target,
        "total_gb": round(total / gb, 1),
        "used_gb": round(used / gb, 1),
        "free_gb": round(free / gb, 1),
        "percent_used": round((used / total) * 100, 1)
    }

def get_config_defaults() -> dict:
    """Reads defaults and presets from config/resolve-kit.json."""
    config_path = get_resolve_kit_dir() / "config" / "resolve-kit.json"
    if config_path.exists():
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}
