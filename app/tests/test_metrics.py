"""Server panel: parsers, alert rules, service checks and the sampler.

    cd app && python3 -m unittest tests.test_metrics -v
"""
import json
import os
import socket
import sys
import tempfile
import threading
import time
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

APP = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(APP))

from hub import metrics  # noqa: E402
from hub.config import Settings  # noqa: E402
from hub.jobs import JobManager  # noqa: E402

SMI = ("0, NVIDIA GeForce GTX 1050 Ti, 37, 12, 3712, 4096, 71, 52.30, 75.00, [N/A], 1607, 1911, P2, 580.95\n"
       "garbage line\n")


class Ok(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200 if self.path == "/ok" else 503)
        self.end_headers()

    def log_message(self, *args):
        pass


class ParserTest(unittest.TestCase):
    def test_nvidia_smi(self):
        gpus = metrics.parse_nvidia_smi(SMI)
        self.assertEqual(len(gpus), 1)
        g = gpus[0]
        self.assertEqual(g["name"], "NVIDIA GeForce GTX 1050 Ti")
        self.assertEqual(g["util"], 37.0)
        self.assertEqual(g["mem_pct"], round(3712 / 4096 * 100, 1))
        self.assertIsNone(g["fan_pct"])
        self.assertEqual(g["temp_c"], 71.0)
        self.assertEqual(g["driver"], "580.95")

    def test_proc_readers(self):
        self.assertTrue(metrics.cpu_times()[0][0] == "cpu")
        self.assertIn("MemTotal", metrics.meminfo())
        procs = metrics.process_ticks()
        self.assertIn(os.getpid(), procs)
        comm, ticks, rss = procs[os.getpid()]
        self.assertGreater(rss, 0)
        self.assertIn("/", metrics.mount_points([]))

    def test_disk_usage_marks_workdir(self):
        with tempfile.TemporaryDirectory() as tmp:
            disks = metrics.disk_usage(["/", tmp], tmp)
            self.assertTrue(any(d["workdir"] for d in disks))
            self.assertEqual(len({d["path"] for d in disks}), len(disks))


class AlertTest(unittest.TestCase):
    TH = metrics.DEFAULT_THRESHOLDS

    def snap(self, **kw):
        base = {"disks": [], "memory": {"total": 16 * 2 ** 30, "available": 8 * 2 ** 30},
                "swap": {"total": 0, "pct": None}, "gpus": [], "services": []}
        base.update(kw)
        return base

    def levels(self, alerts):
        return {key: level for key, level, _ in alerts}

    def test_quiet_when_healthy(self):
        self.assertEqual(metrics.evaluate_alerts(self.snap(), self.TH), [])

    def test_disk_thresholds(self):
        gbyte = 2 ** 30
        disks = [{"path": "/big", "total": 1000 * gbyte, "free": 300 * gbyte, "free_pct": 30.0},
                 {"path": "/warn", "total": 1000 * gbyte, "free": 15 * gbyte, "free_pct": 1.5 + 6},
                 {"path": "/crit", "total": 100 * gbyte, "free": 3 * gbyte, "free_pct": 3.0}]
        levels = self.levels(metrics.evaluate_alerts(self.snap(disks=disks), self.TH))
        self.assertNotIn("disk:/big", levels)
        self.assertEqual(levels["disk:/warn"], "warn")
        self.assertEqual(levels["disk:/crit"], "crit")

    def test_memory_gpu_services_update_jobs(self):
        gpu = {"index": "0", "temp_c": 90.0, "mem_pct": 95.0, "mem_used_mb": 3891.0, "mem_total_mb": 4096.0}
        snap = self.snap(memory={"total": 100, "available": 4}, swap={"total": 10, "pct": 40.0},
                         gpus=[gpu], services=[{"name": "Postgres", "ok": False, "state": "refused"},
                                               {"name": "Redis", "ok": False, "state": "timeout"}])
        alerts = metrics.evaluate_alerts(snap, self.TH, cpu_avg=97.0,
                                         update={"result": "tests-failed", "message": "x"},
                                         failed_jobs=[{"id": "j1", "title": "Замер"}],
                                         svc_fails={"Postgres": 3, "Redis": 1}, oom_recent=True)
        levels = self.levels(alerts)
        self.assertEqual(levels["mem"], "crit")
        self.assertEqual(levels["swap"], "warn")
        self.assertEqual(levels["svc:Redis"], "warn")   # one miss is not "down" yet
        self.assertEqual(levels["oom"], "crit")
        self.assertEqual(levels["cpu"], "warn")
        self.assertEqual(levels["gpu_temp:0"], "crit")
        self.assertEqual(levels["vram:0"], "warn")
        self.assertEqual(levels["svc:Postgres"], "crit")
        self.assertEqual(levels["update"], "warn")
        self.assertEqual(levels["job:j1"], "info")
        self.assertTrue(all(isinstance(text, str) and text for _, _, text in alerts))
        busy = self.levels(metrics.evaluate_alerts(self.snap(), self.TH, cpu_avg=97.0, jobs_running=1))
        self.assertEqual(busy["cpu"], "info")  # a running hub job explains the load


class ServiceCheckTest(unittest.TestCase):
    def test_tcp_http_process(self):
        listener = socket.socket()
        listener.bind(("127.0.0.1", 0))
        listener.listen(1)
        port = listener.getsockname()[1]
        try:
            ok = metrics.check_service({"name": "open", "tcp": f"127.0.0.1:{port}"})
            self.assertTrue(ok["ok"])
            self.assertIsNotNone(ok["latency_ms"])
        finally:
            listener.close()
        refused = metrics.check_service({"name": "closed", "tcp": f"127.0.0.1:{port}", "timeout": 1})
        self.assertFalse(refused["ok"])
        srv = HTTPServer(("127.0.0.1", 0), Ok)
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        try:
            base = f"http://127.0.0.1:{srv.server_port}"
            self.assertTrue(metrics.check_service({"http": base + "/ok"})["ok"])
            down = metrics.check_service({"http": base + "/down"})
            self.assertFalse(down["ok"])
            self.assertEqual(down["state"], "HTTP 503")
        finally:
            srv.shutdown()
            srv.server_close()
        self.assertTrue(metrics.check_service({"process": "python"}, ["python3", "bash"])["ok"])
        self.assertFalse(metrics.check_service({"process": "farm"}, ["python3"])["ok"])
        self.assertFalse(metrics.check_service({"name": "x"})["ok"])


class SamplerTest(unittest.TestCase):
    def test_samples_history_and_persistence(self):
        with tempfile.TemporaryDirectory() as tmp:
            settings = Settings({"workdir": tmp, "metrics_interval": 0.2, "services_interval": 0.2,
                                 "alerts": {"service_down_after": 1},
                                 "services": [{"name": "nothing", "tcp": "127.0.0.1:1", "timeout": 0.5}],
                                 "max_parallel_jobs": 1, "repo_root": str(APP.parent)})
            jobs = JobManager(settings, [], {})
            sampler = metrics.Sampler(settings, jobs=jobs)
            sampler.start()
            try:
                deadline = time.time() + 10
                while time.time() < deadline and len(sampler.fine) < 3:
                    time.sleep(0.1)
                snap = sampler.current()
                self.assertGreaterEqual(len(sampler.fine), 3)
                self.assertIsNotNone(snap["cpu"]["percent"])
                self.assertEqual(snap["status"], "crit")  # the closed port is a dead service
                self.assertEqual(snap["alerts"][0]["id"], "svc:nothing")
                hist = sampler.history("15m")
                self.assertEqual(len(hist["series"]["t"]), len(hist["series"]["cpu"]))
                self.assertEqual(sampler.history("bogus")["range"], "1h")
                self.assertGreaterEqual(len(sampler.history("24h")["series"]["t"]), 1)
            finally:
                sampler.stop()
                jobs.pool.shutdown(wait=False)
            saved = json.loads((Path(tmp) / "metrics" / "history-minute.json").read_text())
            self.assertTrue(saved["minute"])
            again = metrics.Sampler(settings)
            self.assertEqual(len(again.minute), len(saved["minute"]))
            again.pool.shutdown(wait=False)


class JobProgressTest(unittest.TestCase):
    def test_progress_from_ffmpeg_log(self):
        with tempfile.TemporaryDirectory() as tmp:
            settings = Settings({"workdir": tmp, "max_parallel_jobs": 1, "repo_root": str(APP.parent)})
            jobs = JobManager(settings, [], {})
            job_dir = Path(tmp) / "jobs" / "x"
            job_dir.mkdir(parents=True)
            (job_dir / "log.txt").write_text(
                "Input #0\n  Duration: 00:01:40.00, start: 0\nframe=1 time=00:00:10.00 speed=2.0x\r"
                "frame=2 time=00:00:25.00 bitrate=1 speed=2.5x\r")
            info = jobs.progress("x")
            self.assertEqual(info["percent"], 25.0)
            self.assertEqual(info["eta_s"], 30)
            (job_dir / "log.txt").write_text("no ffmpeg here")
            self.assertIsNone(jobs.progress("x"))
            jobs.pool.shutdown(wait=False)


if __name__ == "__main__":
    unittest.main()
