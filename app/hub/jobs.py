"""Background job runner: one thread pool, one folder per job, logs on disk."""
import json
import re
import shutil
import subprocess
import sys
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from .tools import build_argv, tool_status

STATES = ("queued", "running", "done", "failed", "cancelled")
DURATION = re.compile(r"Duration: (\d+):(\d+):(\d+(?:\.\d+)?)")
TIME = re.compile(r"time=(\d+):(\d+):(\d+(?:\.\d+)?)")
SPEED = re.compile(r"speed=\s*([\d.]+)x")


def _seconds(match):
    h, m, s = match
    return int(h) * 3600 + int(m) * 60 + float(s)


class JobManager:
    def __init__(self, settings, tools, variables):
        self.settings = settings
        self.tools = {t["id"]: t for t in tools}
        self.variables = variables
        self.root = Path(settings.workdir) / "jobs"
        self.root.mkdir(parents=True, exist_ok=True)
        (Path(settings.workdir) / "inputs").mkdir(parents=True, exist_ok=True)
        self.pool = ThreadPoolExecutor(max_workers=settings.max_parallel_jobs)
        self.lock = threading.Lock()
        self.jobs = {}
        self.procs = {}
        self._load_existing()

    def _load_existing(self):
        for meta in sorted(self.root.glob("*/job.json")):
            try:
                job = json.loads(meta.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                continue
            if job.get("state") in ("queued", "running"):
                job["state"] = "failed"
                job["error"] = "сервер перезапускался во время задачи"
            self.jobs[job["id"]] = job

    def _save(self, job):
        path = self.root / job["id"] / "job.json"
        path.write_text(json.dumps(job, ensure_ascii=False, indent=2), encoding="utf-8")

    def submit(self, tool_id, params):
        tool = self.tools.get(tool_id)
        if not tool:
            raise KeyError(tool_id)
        ok, reason = tool_status(tool, self.variables)
        if not ok:
            raise RuntimeError(reason)
        job_id = time.strftime("%Y%m%d-%H%M%S-") + uuid.uuid4().hex[:6]
        job_dir = self.root / job_id
        (job_dir / "out").mkdir(parents=True)
        argv = build_argv(tool, params or {}, self.variables, self.settings.workdir,
                          job_dir, self.settings.repo_root, sys.executable)
        job = {
            "id": job_id, "tool": tool_id, "title": tool.get("title", tool_id),
            "params": params or {}, "argv": argv, "state": "queued",
            "created": time.time(), "started": None, "finished": None,
            "returncode": None, "error": None,
        }
        with self.lock:
            self.jobs[job_id] = job
        self._save(job)
        self.pool.submit(self._run, job, tool.get("timeout", 3600))
        return job

    def _run(self, job, timeout):
        job_dir = self.root / job["id"]
        with self.lock:
            if job["state"] == "cancelled":
                return
            job["state"] = "running"
            job["started"] = time.time()
        self._save(job)
        log_path = job_dir / "log.txt"
        try:
            with open(log_path, "wb") as log:
                proc = subprocess.Popen(job["argv"], cwd=str(job_dir), stdout=log,
                                        stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL)
                with self.lock:
                    self.procs[job["id"]] = proc
                try:
                    rc = proc.wait(timeout=timeout)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait()
                    rc = None
                    job["error"] = f"превышено время ({timeout} с)"
            with self.lock:
                self.procs.pop(job["id"], None)
                job["returncode"] = rc
                if job["state"] != "cancelled":
                    job["state"] = "done" if rc == 0 else "failed"
        except OSError as exc:
            job["state"] = "failed"
            job["error"] = str(exc)
        job["finished"] = time.time()
        self._save(job)

    def cancel(self, job_id):
        with self.lock:
            job = self.jobs.get(job_id)
            if not job or job["state"] not in ("queued", "running"):
                return False
            job["state"] = "cancelled"
            proc = self.procs.get(job_id)
        if proc:
            proc.terminate()
        self._save(job)
        return True

    def get(self, job_id, log_tail=4000):
        job = self.jobs.get(job_id)
        if not job:
            return None
        info = dict(job)
        log_path = self.root / job_id / "log.txt"
        if log_path.exists():
            data = log_path.read_bytes()[-log_tail:]
            info["log"] = data.decode("utf-8", errors="replace")
        else:
            info["log"] = ""
        info["files"] = self.files(job_id)
        if job["state"] == "running":
            info["progress"] = self.progress(job_id)
        result = self.root / job_id / "out" / "report.json"
        if result.exists():
            try:
                info["report"] = json.loads(result.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                info["report"] = None
        return info

    def progress(self, job_id):
        """Best-effort percent and ETA for ffmpeg jobs, read from the log tail."""
        log_path = self.root / job_id / "log.txt"
        try:
            with open(log_path, "rb") as f:
                head = f.read(65536).decode("utf-8", errors="replace")
                f.seek(max(0, log_path.stat().st_size - 8192))
                tail = f.read().decode("utf-8", errors="replace")
        except OSError:
            return None
        durations = [_seconds(m) for m in DURATION.findall(head)]
        times = TIME.findall(tail)
        if not durations or not times or not max(durations):
            return None
        total, done = max(durations), _seconds(times[-1])
        info = {"percent": round(min(99.0, done / total * 100), 1)}
        speeds = SPEED.findall(tail)
        if speeds:
            try:
                speed = float(speeds[-1])
                if speed > 0:
                    info["eta_s"] = round(max(0.0, total - done) / speed)
            except ValueError:
                pass
        return info

    def recent_failures(self, seconds):
        cutoff = time.time() - seconds
        return [{"id": j["id"], "title": j["title"]} for j in list(self.jobs.values())
                if j["state"] == "failed" and (j.get("finished") or 0) >= cutoff]

    def delete(self, job_id):
        with self.lock:
            job = self.jobs.get(job_id)
            if not job or job["state"] in ("queued", "running"):
                return False
            self.jobs.pop(job_id)
        shutil.rmtree(self.root / job_id, ignore_errors=True)
        return True

    def cleanup(self, older_than_days):
        """Delete finished jobs older than N days; returns how many went."""
        cutoff = time.time() - older_than_days * 86400
        old = [j["id"] for j in list(self.jobs.values())
               if j["state"] not in ("queued", "running") and (j.get("finished") or j["created"]) < cutoff]
        return sum(self.delete(job_id) for job_id in old)

    def usage(self):
        total = files = 0
        for path in self.root.rglob("*"):
            if path.is_file():
                files += 1
                try:
                    total += path.stat().st_size
                except OSError:
                    pass
        return {"jobs": len(self.jobs), "files": files, "bytes": total}

    def files(self, job_id):
        out = self.root / job_id / "out"
        if not out.exists():
            return []
        return [
            {"name": str(p.relative_to(out)), "size": p.stat().st_size,
             "path": f"jobs/{job_id}/out/{p.relative_to(out)}"}
            for p in sorted(out.rglob("*")) if p.is_file()
        ]

    def list(self, limit=50):
        jobs = sorted(self.jobs.values(), key=lambda j: j["created"], reverse=True)
        out = []
        for j in jobs[:limit]:
            row = {k: j.get(k) for k in ("id", "tool", "title", "state", "created", "started", "finished",
                                         "returncode", "error")}
            if j["state"] == "running":
                row["progress"] = self.progress(j["id"])
            out.append(row)
        return out

    def counts(self):
        states = [j["state"] for j in self.jobs.values()]
        return {s: states.count(s) for s in ("queued", "running")}
