"""Background job runner: one thread pool, one folder per job, logs on disk."""
import json
import subprocess
import sys
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from .tools import build_argv, tool_status

STATES = ("queued", "running", "done", "failed", "cancelled")


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
        return info

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
        return [{k: j[k] for k in ("id", "tool", "title", "state", "created", "finished", "returncode", "error")}
                for j in jobs[:limit]]
