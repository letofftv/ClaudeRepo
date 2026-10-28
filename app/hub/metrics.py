"""Live server metrics: a sampler thread with history, services and alerts.

Everything comes from /proc, /sys, nvidia-smi, docker and systemctl — no
third-party packages. One sample every `metrics_interval` seconds (5 by
default). The last hour is kept at full resolution and the last 24 hours as
one-minute averages; the minute history is saved to <workdir>/metrics/ so a
restart (the updater restarts the hub) does not wipe the charts.

Process names come from /proc/<pid>/comm only, never from command lines,
which can carry tokens.
"""
import json
import os
import platform
import re
import shutil
import socket
import subprocess
import threading
import time
import urllib.error
import urllib.request
from collections import deque
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

CLK_TCK = os.sysconf("SC_CLK_TCK") if hasattr(os, "sysconf") else 100
PAGE_SIZE = os.sysconf("SC_PAGE_SIZE") if hasattr(os, "sysconf") else 4096
SKIP_IFACES = ("lo", "veth", "br-", "docker", "virbr", "vnet", "cni", "flannel")
WHOLE_DISK = re.compile(r"^(sd[a-z]+|vd[a-z]+|xvd[a-z]+|hd[a-z]+|nvme\d+n\d+|mmcblk\d+)$")
REAL_FS = {"ext2", "ext3", "ext4", "xfs", "btrfs", "zfs", "ntfs", "ntfs3", "fuseblk", "exfat", "vfat", "9p", "drvfs"}
SKIP_MOUNTS = ("/boot", "/snap", "/var/lib/docker", "/usr/lib/wsl", "/mnt/wsl", "/mnt/wslg", "/init", "/proc", "/sys")
GPU_FIELDS = ["index", "name", "utilization.gpu", "utilization.memory", "memory.used", "memory.total",
              "temperature.gpu", "power.draw", "power.limit", "fan.speed", "clocks.sm", "clocks.max.sm",
              "pstate", "driver_version"]
HISTORY_KEYS = ["cpu", "mem", "swap", "gpu", "vram", "gpu_temp", "rx", "tx", "dr", "dw", "load"]
RANGES = {"15m": ("fine", 900), "1h": ("fine", 3600), "6h": ("minute", 6 * 3600), "24h": ("minute", 24 * 3600)}

# Starting points from Node Exporter Full, Glances and Gatus defaults, tuned for a GPU render box.
DEFAULT_THRESHOLDS = {
    "disk_warn_pct": 10, "disk_crit_pct": 5,      # free space: whichever of % and GB trips first
    "disk_warn_gb": 30, "disk_crit_gb": 10,
    "mem_warn_pct": 20, "mem_crit_pct": 10,       # MemAvailable of the total
    "swap_warn_pct": 25, "swap_crit_pct": 60,
    "cpu_warn_pct": 90, "cpu_window_s": 300,      # sustained load; only info while a hub job runs
    "gpu_temp_warn": 80, "gpu_temp_crit": 87,
    "vram_warn_pct": 90, "vram_crit_pct": 97,
    "service_down_after": 3,                      # failed checks in a row before "down"
}


# --- raw readers -----------------------------------------------------------------
def _read(path):
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            return f.read()
    except OSError:
        return ""


def cpu_times():
    """[(name, total, idle)] for the whole CPU and each core."""
    rows = []
    for line in _read("/proc/stat").splitlines():
        if not line.startswith("cpu"):
            break
        parts = line.split()
        vals = [int(v) for v in parts[1:9]]
        idle = vals[3] + (vals[4] if len(vals) > 4 else 0)
        rows.append((parts[0], sum(vals), idle))
    return rows


def meminfo():
    info = {}
    for line in _read("/proc/meminfo").splitlines():
        key, _, rest = line.partition(":")
        try:
            info[key] = int(rest.split()[0]) * 1024
        except (IndexError, ValueError):
            continue
    return info


def net_bytes():
    """{iface: (rx, tx)} without loopback and container plumbing."""
    out = {}
    for line in _read("/proc/net/dev").splitlines()[2:]:
        name, _, rest = line.partition(":")
        name = name.strip()
        if not name or name.startswith(SKIP_IFACES):
            continue
        fields = rest.split()
        if len(fields) >= 9:
            out[name] = (int(fields[0]), int(fields[8]))
    return out


def disk_bytes():
    """(read, written) bytes summed over whole disks."""
    read = written = 0
    for line in _read("/proc/diskstats").splitlines():
        parts = line.split()
        if len(parts) >= 10 and WHOLE_DISK.match(parts[2]):
            read += int(parts[5]) * 512
            written += int(parts[9]) * 512
    return read, written


def process_ticks():
    """{pid: (comm, cpu_ticks, rss_bytes)} from /proc/<pid>/stat."""
    procs = {}
    try:
        pids = [p for p in os.listdir("/proc") if p.isdigit()]
    except OSError:
        return procs
    for pid in pids:
        raw = _read(f"/proc/{pid}/stat")
        if not raw:
            continue
        lpar, rpar = raw.find("("), raw.rfind(")")
        if lpar < 0 or rpar < 0:
            continue
        rest = raw[rpar + 2:].split()
        try:
            procs[int(pid)] = (raw[lpar + 1:rpar], int(rest[11]) + int(rest[12]), int(rest[21]) * PAGE_SIZE)
        except (IndexError, ValueError):
            continue
    return procs


def cpu_temperature():
    """Package temperature from hwmon (coretemp/k10temp); None in WSL and VMs."""
    temps = []
    for hw in Path("/sys/class/hwmon").glob("hwmon*"):
        if _read(hw / "name").strip() not in ("coretemp", "k10temp", "zenpower", "cpu_thermal"):
            continue
        for sensor in hw.glob("temp*_input"):
            try:
                temps.append(int(_read(sensor).strip()) / 1000)
            except ValueError:
                continue
    return round(max(temps), 1) if temps else None


def _num(value):
    value = value.strip()
    if not value or value.startswith("[") or value in ("N/A", "Not Supported"):
        return None
    try:
        return float(value)
    except ValueError:
        return value


def parse_nvidia_smi(text):
    gpus = []
    for line in text.strip().splitlines():
        parts = [p.strip() for p in line.split(",")]
        if len(parts) != len(GPU_FIELDS):
            continue
        row = dict(zip(GPU_FIELDS, parts))
        gpu = {
            "index": row["index"], "name": row["name"], "driver": row["driver_version"], "pstate": row["pstate"],
            "util": _num(row["utilization.gpu"]), "mem_util": _num(row["utilization.memory"]),
            "mem_used_mb": _num(row["memory.used"]), "mem_total_mb": _num(row["memory.total"]),
            "temp_c": _num(row["temperature.gpu"]), "power_w": _num(row["power.draw"]),
            "power_limit_w": _num(row["power.limit"]), "fan_pct": _num(row["fan.speed"]),
            "clock_mhz": _num(row["clocks.sm"]), "clock_max_mhz": _num(row["clocks.max.sm"]),
        }
        used, total = gpu["mem_used_mb"], gpu["mem_total_mb"]
        gpu["mem_pct"] = round(used / total * 100, 1) if isinstance(used, float) and total else None
        gpus.append(gpu)
    return gpus


def nvidia(exe):
    try:
        out = subprocess.run([exe, "--query-gpu=" + ",".join(GPU_FIELDS), "--format=csv,noheader,nounits"],
                             capture_output=True, text=True, timeout=5)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return [], f"nvidia-smi не ответил: {exc}"
    if out.returncode != 0:
        return [], (out.stderr or out.stdout).strip()[:200] or "nvidia-smi вернул ошибку"
    return parse_nvidia_smi(out.stdout), None


def parse_nvidia_processes(text):
    """Compute processes on the card. In WSL nvidia-smi gives the pid with "[Not Found]" and no
    memory; the pid is the same inside WSL, so the name comes from /proc/<pid>/comm."""
    procs = []
    for line in text.strip().splitlines():
        parts = [p.strip() for p in line.split(",")]
        if len(parts) < 3 or not parts[0].isdigit():
            continue
        pid = int(parts[0])
        name = os.path.basename(",".join(parts[1:-1]))
        if not name or name.startswith("["):
            name = _read(f"/proc/{pid}/comm").strip() or f"pid {pid}"
        procs.append({"pid": pid, "name": name, "mem_mb": _num(parts[-1])})
    return procs


def nvidia_processes(exe):
    try:
        out = subprocess.run([exe, "--query-compute-apps=pid,process_name,used_memory",
                              "--format=csv,noheader,nounits"], capture_output=True, text=True, timeout=5)
    except (OSError, subprocess.TimeoutExpired):
        return []
    return parse_nvidia_processes(out.stdout)


def mount_points(extra):
    """Real file systems worth showing: /, Windows drives in WSL, /mnt and /media disks."""
    found = ["/"]
    for line in _read("/proc/mounts").splitlines():
        parts = line.split()
        if len(parts) < 3:
            continue
        point, fstype = parts[1].replace("\\040", " "), parts[2]
        if fstype not in REAL_FS or point.startswith(SKIP_MOUNTS):
            continue
        if point.startswith(("/mnt/", "/media/", "/srv", "/data", "/home")):
            found.append(point)
    return list(dict.fromkeys([*found, *extra]))


def disk_usage(paths, workdir=None):
    """Usage per file system (one row per device); the one holding the work folder is marked."""
    try:
        work_dev = os.stat(workdir).st_dev if workdir else None
    except OSError:
        work_dev = None
    seen, disks = set(), []
    for path in paths:
        try:
            st = os.stat(path)
            usage = shutil.disk_usage(path)
        except OSError:
            continue
        if st.st_dev in seen or usage.total == 0:
            continue
        seen.add(st.st_dev)
        disks.append({"path": path, "total": usage.total, "free": usage.free, "used": usage.total - usage.free,
                      "free_pct": round(usage.free / usage.total * 100, 1), "workdir": st.st_dev == work_dev})
    return disks[:10]


def is_wsl():
    return "microsoft" in _read("/proc/sys/kernel/osrelease").lower()


# --- services ----------------------------------------------------------------------
_NO_PROXY = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def check_service(spec, proc_names=()):
    """One configured check: tcp / http / systemd / docker / process."""
    name = spec.get("name") or next((str(spec[k]) for k in ("tcp", "http", "systemd", "docker", "process")
                                     if k in spec), "служба")
    result = {"name": name, "ok": False, "state": "", "latency_ms": None, "kind": ""}
    start = time.monotonic()
    try:
        if "tcp" in spec:
            result["kind"] = "tcp"
            host, _, port = str(spec["tcp"]).rpartition(":")
            with socket.create_connection((host or "127.0.0.1", int(port)), timeout=spec.get("timeout", 2)):
                pass
            result.update(ok=True, state="порт открыт")
        elif "http" in spec:
            result["kind"] = "http"
            with _NO_PROXY.open(spec["http"], timeout=spec.get("timeout", 3)) as resp:
                result.update(ok=resp.status < 500, state=f"HTTP {resp.status}")
        elif "systemd" in spec:
            result["kind"] = "systemd"
            cmd = ["systemctl"] + (["--user"] if spec.get("user") else []) + ["is-active", spec["systemd"]]
            out = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
            state = out.stdout.strip() or out.stderr.strip()[:80]
            result.update(ok=state == "active", state=state)
        elif "docker" in spec:
            result["kind"] = "docker"
            out = subprocess.run(["docker", "inspect", "-f", "{{.State.Status}}|{{if .State.Health}}"
                                  "{{.State.Health.Status}}{{end}}", spec["docker"]],
                                 capture_output=True, text=True, timeout=6)
            status, _, health = out.stdout.strip().partition("|")
            result.update(ok=status == "running" and health != "unhealthy",
                          state=(status or out.stderr.strip()[:80]) + (f", {health}" if health else ""))
        elif "process" in spec:
            result["kind"] = "process"
            want = spec["process"]
            alive = any(n == want or n.startswith(want) for n in proc_names)
            result.update(ok=alive, state="запущен" if alive else "не найден")
        else:
            result["state"] = "неизвестный тип проверки"
    except urllib.error.HTTPError as exc:
        result.update(ok=exc.code < 500, state=f"HTTP {exc.code}")
    except (OSError, ValueError, subprocess.TimeoutExpired, urllib.error.URLError) as exc:
        result["state"] = _plain_error(getattr(exc, "reason", exc))
    if result["ok"] and result["kind"] in ("tcp", "http"):
        result["latency_ms"] = round((time.monotonic() - start) * 1000, 1)
    return result


def _plain_error(exc):
    """Network errors as the owner would say them."""
    if isinstance(exc, ConnectionRefusedError):
        return "соединение отклонено — служба не запущена"
    if isinstance(exc, (socket.timeout, TimeoutError, subprocess.TimeoutExpired)):
        return "нет ответа (таймаут)"
    if isinstance(exc, socket.gaierror):
        return "адрес не найден"
    text = str(exc)
    if "refused" in text.lower():
        return "соединение отклонено — служба не запущена"
    if "timed out" in text.lower():
        return "нет ответа (таймаут)"
    return text[:120] or exc.__class__.__name__


def docker_containers():
    """All containers with state, or None when docker is not reachable."""
    if not shutil.which("docker"):
        return None
    try:
        out = subprocess.run(["docker", "ps", "-a", "--format", "{{json .}}"],
                             capture_output=True, text=True, timeout=6)
    except (OSError, subprocess.TimeoutExpired):
        return None
    if out.returncode != 0:
        return None
    items = []
    for line in out.stdout.splitlines():
        try:
            c = json.loads(line)
        except ValueError:
            continue
        status = c.get("Status", "")
        items.append({"name": c.get("Names", ""), "image": c.get("Image", ""), "state": c.get("State", ""),
                      "status": status, "health": "unhealthy" if "unhealthy" in status else
                      ("healthy" if "healthy" in status else "")})
    items.sort(key=lambda c: (c["state"] != "running", c["name"]))
    return items


# --- alerts --------------------------------------------------------------------------
def gb(n):
    return f"{n / 1024 ** 3:.1f}".replace(".", ",")


def evaluate_alerts(snap, th, cpu_avg=None, update=None, failed_jobs=(), jobs_running=0, svc_fails=None,
                    oom_recent=False):
    """[(id, level, title)] for the current snapshot."""
    alerts = []
    svc_fails = svc_fails or {}
    for d in snap.get("disks", []):
        free_gb = d["free"] / 1024 ** 3
        text = f"Мало места на {d['path']}: свободно {gb(d['free'])} ГБ ({d['free_pct']:.0f}%)"
        if free_gb < th["disk_crit_gb"] or d["free_pct"] < th["disk_crit_pct"]:
            alerts.append((f"disk:{d['path']}", "crit", text))
        elif free_gb < th["disk_warn_gb"] or d["free_pct"] < th["disk_warn_pct"]:
            alerts.append((f"disk:{d['path']}", "warn", text))
    mem = snap.get("memory") or {}
    if mem.get("total"):
        avail_pct = mem["available"] / mem["total"] * 100
        text = f"Мало свободной памяти: {gb(mem['available'])} ГБ ({avail_pct:.0f}%)"
        if avail_pct < th["mem_crit_pct"]:
            alerts.append(("mem", "crit", text))
        elif avail_pct < th["mem_warn_pct"]:
            alerts.append(("mem", "warn", text))
    swap = snap.get("swap") or {}
    if swap.get("total") and swap.get("pct") is not None:
        if swap["pct"] >= th["swap_crit_pct"]:
            alerts.append(("swap", "crit", f"Подкачка занята на {swap['pct']:.0f}% — памяти не хватает"))
        elif swap["pct"] >= th["swap_warn_pct"]:
            alerts.append(("swap", "warn", f"Подкачка занята на {swap['pct']:.0f}%"))
    if oom_recent:
        alerts.append(("oom", "crit", "Система завершила процесс из-за нехватки памяти (OOM) за последние 10 мин"))
    if cpu_avg is not None and cpu_avg > th["cpu_warn_pct"]:
        minutes = round(th["cpu_window_s"] / 60)
        if jobs_running:
            alerts.append(("cpu", "info", f"Процессор загружен на {cpu_avg:.0f}% — идёт задача пульта"))
        else:
            alerts.append(("cpu", "warn", f"Процессор загружен на {cpu_avg:.0f}% последние {minutes} мин"))
    for g in snap.get("gpus", []):
        label = "Видеокарта" if len(snap["gpus"]) == 1 else f"Видеокарта {g['index']}"
        t = g.get("temp_c")
        if isinstance(t, float):
            if t >= th["gpu_temp_crit"]:
                alerts.append((f"gpu_temp:{g['index']}", "crit", f"{label} перегрета: {t:.0f} °C"))
            elif t >= th["gpu_temp_warn"]:
                alerts.append((f"gpu_temp:{g['index']}", "warn", f"{label} горячая: {t:.0f} °C"))
        p = g.get("mem_pct")
        if p is not None:
            text = (f"Видеопамять занята на {p:.0f}% ({g['mem_used_mb']:.0f} из {g['mem_total_mb']:.0f} МБ) — "
                    "новые задачи на видеокарте могут упасть")
            if p >= th["vram_crit_pct"]:
                alerts.append((f"vram:{g['index']}", "crit", text))
            elif p >= th["vram_warn_pct"]:
                alerts.append((f"vram:{g['index']}", "warn", text))
    if snap.get("gpu_error"):
        alerts.append(("gpu_error", "warn", "Видеокарта не отвечает: " + snap["gpu_error"]))
    for s in snap.get("services") or []:
        if s["ok"]:
            continue
        fails = svc_fails.get(s["name"], th["service_down_after"])
        level = "crit" if fails >= th["service_down_after"] else "warn"
        word = "Не отвечает" if level == "crit" else "Нет ответа от"
        alerts.append((f"svc:{s['name']}", level, f"{word}: {s['name']} ({s['state'] or 'нет ответа'})"))
    if update and update.get("result") in ("tests-failed", "error", "local-changes"):
        alerts.append(("update", "warn", "Обновление пульта остановлено: " + (update.get("message") or "")[:160]))
    for job in failed_jobs:
        alerts.append((f"job:{job['id']}", "info", f"Задача «{job['title']}» завершилась с ошибкой"))
    return alerts


# --- sampler -------------------------------------------------------------------------
class Sampler:
    def __init__(self, settings, jobs=None, update_reader=None):
        self.settings = settings
        self.jobs = jobs
        self.update_reader = update_reader or (lambda: None)
        self.interval = max(0.1, float(settings.get("metrics_interval", 5)))
        self.services_interval = max(self.interval, float(settings.get("services_interval", 15)))
        self.thresholds = dict(DEFAULT_THRESHOLDS, **(settings.get("alerts") or {}))
        self.services_spec = settings.get("services") or []
        self.extra_disks = [settings.workdir] + list(settings.get("disks") or [])
        hidden = {os.path.normpath(p) for p in settings.get("hide_disks") or []}
        self.fine = deque(maxlen=int(3600 / self.interval) + 2)
        self.minute = deque(maxlen=24 * 60 + 2)
        self.lock = threading.Lock()
        self.snapshot = {"time": None, "status": "unknown", "alerts": [], "warming_up": True}
        self.alert_since = {}
        self.services = []
        self.docker = None
        self.gpu_procs = []
        self.last_services = 0.0
        self.svc_fails = {}
        self.oom_count = _oom_kills()
        self.oom_at = 0.0
        self.last_save = time.time()
        self.history_file = Path(settings.workdir) / "metrics" / "history-minute.json"
        self.nvidia_exe = shutil.which("nvidia-smi")
        self.static = {"host": platform.node(), "system": f"{platform.system()} {platform.release()}",
                       "python": platform.python_version(), "cpu_count": os.cpu_count() or 1, "wsl": is_wsl(),
                       "mounts": [m for m in mount_points(self.extra_disks) if os.path.normpath(m) not in hidden]}
        self.pool = ThreadPoolExecutor(max_workers=6)
        self._stop = threading.Event()
        self._thread = None
        self._load_history()

    # history persistence keeps the 24 h chart across restarts
    def _load_history(self):
        try:
            data = json.loads(self.history_file.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return
        cutoff = time.time() - 24 * 3600
        for row in data.get("minute", []):
            if row.get("t", 0) >= cutoff:
                self.minute.append(row)

    def save_history(self):
        try:
            self.history_file.parent.mkdir(parents=True, exist_ok=True)
            tmp = self.history_file.with_suffix(".tmp")
            with self.lock:
                rows = list(self.minute)
            tmp.write_text(json.dumps({"minute": rows}), encoding="utf-8")
            tmp.replace(self.history_file)
        except OSError:
            pass

    def start(self):
        self._thread = threading.Thread(target=self._loop, name="metrics", daemon=True)
        self._thread.start()

    def stop(self):
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=5)
        self.pool.shutdown(wait=False, cancel_futures=True)
        self.save_history()

    def _raw(self):
        return {"t": time.time(), "cpu": cpu_times(), "net": net_bytes(), "disk": disk_bytes(),
                "procs": process_ticks()}

    def _loop(self):
        prev = self._raw()
        self._stop.wait(min(1.0, self.interval))
        while not self._stop.is_set():
            started = time.monotonic()
            try:
                cur = self._raw()
                self._sample(prev, cur)
                prev = cur
            except Exception as exc:  # never let one bad read kill the panel
                with self.lock:
                    self.snapshot = dict(self.snapshot, sampler_error=str(exc)[:200])
            self._stop.wait(max(0.05, self.interval - (time.monotonic() - started)))

    def _sample(self, prev, cur):
        dt = max(cur["t"] - prev["t"], 1e-6)
        ncpu = self.static["cpu_count"]
        # CPU
        usage = []
        prev_cpu = {name: (tot, idle) for name, tot, idle in prev["cpu"]}
        for name, tot, idle in cur["cpu"]:
            ptot, pidle = prev_cpu.get(name, (tot, idle))
            dtot, didle = tot - ptot, idle - pidle
            usage.append(round(max(0.0, min(100.0, (1 - didle / dtot) * 100)), 1) if dtot > 0 else 0.0)
        try:
            load = list(os.getloadavg())
        except (OSError, AttributeError):
            load = None
        # memory
        mi = meminfo()
        total, avail = mi.get("MemTotal", 0), mi.get("MemAvailable", 0)
        swap_total, swap_free = mi.get("SwapTotal", 0), mi.get("SwapFree", 0)
        memory = {"total": total, "available": avail, "used": total - avail,
                  "pct": round((total - avail) / total * 100, 1) if total else None,
                  "cached": mi.get("Cached", 0) + mi.get("Buffers", 0)}
        swap = {"total": swap_total, "used": swap_total - swap_free,
                "pct": round((swap_total - swap_free) / swap_total * 100, 1) if swap_total else None}
        # network and disk IO rates
        ifaces = []
        rx = tx = 0.0
        for name, (r, t) in cur["net"].items():
            pr, pt = prev["net"].get(name, (r, t))
            rr, tr = max(0, r - pr) / dt, max(0, t - pt) / dt
            rx, tx = rx + rr, tx + tr
            ifaces.append({"name": name, "rx_bps": round(rr), "tx_bps": round(tr)})
        ifaces.sort(key=lambda i: i["rx_bps"] + i["tx_bps"], reverse=True)
        dr = max(0, cur["disk"][0] - prev["disk"][0]) / dt
        dw = max(0, cur["disk"][1] - prev["disk"][1]) / dt
        # processes grouped by name
        groups = {}
        for pid, (comm, ticks, rss) in cur["procs"].items():
            pticks = prev["procs"].get(pid, (comm, ticks, rss))[1]
            cpu_pct = max(0, ticks - pticks) / CLK_TCK / dt / ncpu * 100
            g = groups.setdefault(comm, {"name": comm, "cpu": 0.0, "rss": 0, "count": 0})
            g["cpu"] += cpu_pct
            g["rss"] += rss
            g["count"] += 1
        procs = list(groups.values())
        for g in procs:
            g["cpu"] = round(g["cpu"], 1)
        top_cpu = sorted(procs, key=lambda g: g["cpu"], reverse=True)[:6]
        top_mem = sorted(procs, key=lambda g: g["rss"], reverse=True)[:6]
        # GPU
        gpus, gpu_error = ([], None)
        if self.nvidia_exe:
            gpus, gpu_error = nvidia(self.nvidia_exe)
        # services, containers and GPU processes on a slower cadence, in parallel
        now = time.time()
        if now - self.last_services >= self.services_interval or not self.last_services:
            self.last_services = now
            names = [g["name"] for g in procs]
            futures = [self.pool.submit(check_service, spec, names) for spec in self.services_spec]
            docker_future = self.pool.submit(docker_containers)
            gpu_future = self.pool.submit(nvidia_processes, self.nvidia_exe) if self.nvidia_exe else None
            self.services = [f.result() for f in futures]
            for svc in self.services:  # consecutive failures: one miss is "no answer", three are "down"
                self.svc_fails[svc["name"]] = 0 if svc["ok"] else self.svc_fails.get(svc["name"], 0) + 1
                svc["fails"] = self.svc_fails[svc["name"]]
            self.docker = docker_future.result()
            self.gpu_procs = gpu_future.result() if gpu_future else []
        disks = disk_usage(self.static["mounts"], self.settings.workdir)
        g0 = gpus[0] if gpus else {}
        point = {"t": round(now, 1), "cpu": usage[0] if usage else None, "mem": memory["pct"],
                 "swap": swap["pct"], "gpu": g0.get("util"), "vram": g0.get("mem_pct"),
                 "gpu_temp": g0.get("temp_c"), "rx": round(rx), "tx": round(tx), "dr": round(dr),
                 "dw": round(dw), "load": round(load[0], 2) if load else None}
        with self.lock:
            self.fine.append(point)
            self._roll_minute(point)
            window = [p["cpu"] for p in self.fine
                      if p["cpu"] is not None and p["t"] >= now - self.thresholds["cpu_window_s"]]
        covered = len(window) * self.interval >= self.thresholds["cpu_window_s"] * 0.8
        cpu_avg = sum(window) / len(window) if window and covered else None
        snap = {
            **self.static, "time": now, "interval": self.interval, "uptime_s": _uptime(),
            "cpu": {"percent": usage[0] if usage else None, "per_core": usage[1:], "load": load,
                    "temp_c": cpu_temperature(), "avg_window": round(cpu_avg, 1) if cpu_avg is not None else None},
            "memory": memory, "swap": swap, "disks": disks,
            "disk_io": {"read_bps": round(dr), "write_bps": round(dw)},
            "net": {"rx_bps": round(rx), "tx_bps": round(tx), "ifaces": ifaces[:6]},
            "gpus": gpus, "gpu_error": gpu_error, "gpu_procs": self.gpu_procs,
            "top_cpu": top_cpu, "top_mem": top_mem, "processes": len(cur["procs"]),
            "services": self.services, "docker": self.docker,
        }
        oom = _oom_kills()
        if oom > self.oom_count:
            self.oom_at = now
        self.oom_count = oom
        update = self.update_reader()
        failed = self.jobs.recent_failures(3600) if self.jobs else []
        running = self.jobs.counts().get("running", 0) if self.jobs else 0
        raw_alerts = evaluate_alerts(snap, self.thresholds, cpu_avg, update, failed, running, self.svc_fails,
                                     now - self.oom_at < 600)
        alerts = []
        active = set()
        for key, level, title in raw_alerts:
            active.add(key)
            since = self.alert_since.setdefault(key, now)
            alerts.append({"id": key, "level": level, "title": title, "since": since})
        for key in list(self.alert_since):
            if key not in active:
                del self.alert_since[key]
        order = {"crit": 0, "warn": 1, "info": 2}
        alerts.sort(key=lambda a: (order[a["level"]], a["since"]))
        levels = {a["level"] for a in alerts}
        snap["alerts"] = alerts
        snap["status"] = "crit" if "crit" in levels else "warn" if "warn" in levels else "ok"
        with self.lock:
            self.snapshot = snap
        if now - self.last_save > 300:
            self.last_save = now
            self.save_history()

    def _roll_minute(self, point):
        """Average full-resolution points into one row per minute."""
        minute = int(point["t"] // 60) * 60
        if self.minute and self.minute[-1].get("_m") == minute:
            row = self.minute[-1]
            n = row["_n"]
            for key in HISTORY_KEYS:
                v = point.get(key)
                if v is None:
                    continue
                old = row.get(key)
                row[key] = round(v if old is None else (old * n + v) / (n + 1), 2)
            row["_n"] = n + 1
        else:
            row = {key: point.get(key) for key in HISTORY_KEYS}
            row.update({"t": minute + 30, "_m": minute, "_n": 1})
            self.minute.append(row)

    def current(self):
        with self.lock:
            return self.snapshot

    def history(self, range_key):
        source, span = RANGES.get(range_key, RANGES["1h"])
        cutoff = time.time() - span
        with self.lock:
            rows = [r for r in (self.fine if source == "fine" else self.minute) if r["t"] >= cutoff]
        series = {"t": [r["t"] for r in rows]}
        for key in HISTORY_KEYS:
            series[key] = [r.get(key) for r in rows]
        step = self.interval if source == "fine" else 60
        return {"range": range_key if range_key in RANGES else "1h", "step": step, "series": series}


def _oom_kills():
    for line in _read("/proc/vmstat").splitlines():
        if line.startswith("oom_kill "):
            try:
                return int(line.split()[1])
            except (IndexError, ValueError):
                return 0
    return 0


def _uptime():
    try:
        return float(_read("/proc/uptime").split()[0])
    except (IndexError, ValueError):
        return None
