"""Server status: CPU, memory, disk, GPU (nvidia-smi), uptime."""
import os
import platform
import shutil
import subprocess
import time


def _meminfo():
    try:
        with open("/proc/meminfo", encoding="utf-8") as f:
            info = {}
            for line in f:
                key, _, rest = line.partition(":")
                info[key] = int(rest.split()[0]) * 1024
        return {"total": info.get("MemTotal"), "available": info.get("MemAvailable")}
    except (OSError, ValueError, IndexError):
        return {"total": None, "available": None}


def _uptime():
    try:
        with open("/proc/uptime", encoding="utf-8") as f:
            return float(f.read().split()[0])
    except (OSError, ValueError):
        return None


def _gpus():
    exe = shutil.which("nvidia-smi")
    if not exe:
        return []
    fields = "name,memory.used,memory.total,utilization.gpu,temperature.gpu,driver_version"
    try:
        out = subprocess.run([exe, f"--query-gpu={fields}", "--format=csv,noheader,nounits"],
                             capture_output=True, text=True, timeout=5).stdout
    except (OSError, subprocess.TimeoutExpired):
        return []
    gpus = []
    for line in out.strip().splitlines():
        parts = [p.strip() for p in line.split(",")]
        if len(parts) == 6:
            gpus.append({"name": parts[0], "mem_used_mb": parts[1], "mem_total_mb": parts[2],
                         "util_percent": parts[3], "temp_c": parts[4], "driver": parts[5]})
    return gpus


def status(workdir):
    try:
        load = os.getloadavg()
    except (OSError, AttributeError):
        load = None
    disk = shutil.disk_usage(workdir)
    return {
        "time": time.time(),
        "host": platform.node(),
        "system": f"{platform.system()} {platform.release()}",
        "python": platform.python_version(),
        "cpu_count": os.cpu_count(),
        "load": load,
        "memory": _meminfo(),
        "disk": {"total": disk.total, "free": disk.free, "path": workdir},
        "uptime_s": _uptime(),
        "gpus": _gpus(),
        "ffmpeg": bool(shutil.which("ffmpeg")),
    }
