"""End-to-end tests: real HTTP server on a free port, real ffmpeg jobs.

    cd app && python3 -m unittest discover -s tests -v
"""
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.request
import wave
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

APP = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(APP))

from hub.config import extend_path, load_settings  # noqa: E402
from hub.server import make_server  # noqa: E402
from hub.tools import ParamError, build_argv, build_runs, load_tools  # noqa: E402

HAS_FFMPEG = bool(shutil.which("ffmpeg"))
TOKEN = "test-token-123"


def make_wav_bytes(seconds=0.5, rate=16000):
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(b"\x10\x00" * int(rate * seconds))
    return buf.getvalue()


class MockTTS(BaseHTTPRequestHandler):
    """Fake OpenAI-compatible speech endpoint: returns 0.5 s of WAV per request."""
    requests = []

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        MockTTS.requests.append({"path": self.path, "body": body, "auth": self.headers.get("Authorization")})
        data = make_wav_bytes()
        self.send_response(200)
        self.send_header("Content-Type", "audio/wav")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *args):
        pass


class HubTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp(prefix="hubtest-"))
        cls.tts = HTTPServer(("127.0.0.1", 0), MockTTS)
        threading.Thread(target=cls.tts.serve_forever, daemon=True).start()
        local = {
            "vars": {"tts_url": f"http://127.0.0.1:{cls.tts.server_port}/v1"},
            "tools": [
                {"id": "sleeper", "title": "sleep", "command": ["sleep", "30"], "params": [], "timeout": 60},
                {"id": "needs_missing", "title": "x", "command": ["definitely-missing-binary-xyz"],
                 "requires": ["definitely-missing-binary-xyz"], "params": []},
                {"id": "echo_args", "title": "echo", "command": ["echo", "A={a}", "{opt}", "B={b}"],
                 "params": [{"name": "a", "type": "string", "required": True},
                            {"name": "opt", "type": "string"},
                            {"name": "b", "type": "string", "default": "x y;z"}]},
                {"id": "show_file", "title": "cat", "command": ["cat", "{f}"],
                 "params": [{"name": "f", "type": "file", "required": True, "accept": ["text"]}]},
                # "GPU" that always fails and a CPU run that reports the env it got
                {"id": "gpu_fallback", "title": "gpu", "params": [],
                 "command": ["{python}", "-c", "import os; print('CPU', repr(os.environ.get('CUDA_VISIBLE_DEVICES', 'unset')))"],
                 "gpu": {"requires": ["python3"], "cpu_env": {"CUDA_VISIBLE_DEVICES": ""},
                         "command": ["{python}", "-c", "import sys; print('GPU try'); sys.exit(3)"]}},
                {"id": "gpu_missing", "title": "no gpu", "params": [], "command": ["echo", "cpu only"],
                 "gpu": {"requires": ["definitely-missing-binary-xyz"], "command": ["echo", "never"]}},
            ],
        }
        local_file = cls.tmp / "tools.local.json"
        local_file.write_text(json.dumps(local), encoding="utf-8")
        os.environ.pop("HUB_TOKEN", None)
        cls.settings = load_settings(overrides={
            "bind": "127.0.0.1", "port": 0, "workdir": str(cls.tmp / "work"),
            "tools_local_file": str(local_file), "token": TOKEN,
        })
        (cls.tmp / "work").mkdir()
        cls.server, cls.hub = make_server(cls.settings)
        cls.port = cls.server.server_address[1]
        cls.base = f"http://127.0.0.1:{cls.port}"
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        if HAS_FFMPEG:
            cls.wav = cls.tmp / "tone.wav"
            subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "lavfi", "-i",
                            "sine=frequency=440:duration=4", "-ar", "48000", str(cls.wav)], check=True)
            cls.video = cls.tmp / "clip.mp4"
            subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
                            "-f", "lavfi", "-i", "testsrc=size=320x240:rate=24:duration=3",
                            "-f", "lavfi", "-i", "sine=frequency=330:duration=3",
                            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest",
                            str(cls.video)], check=True)

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.tts.shutdown()
        cls.tts.server_close()
        cls.hub.close()
        cls.hub.jobs.pool.shutdown(wait=False, cancel_futures=True)
        shutil.rmtree(cls.tmp, ignore_errors=True)

    # --- helpers -------------------------------------------------------------
    def call(self, method, path, body=None, raw=None, token=TOKEN, headers=None):
        hdrs = dict(headers or {})
        if token is not None:
            hdrs["Authorization"] = "Bearer " + token
        data = None
        if body is not None:
            data = json.dumps(body).encode()
            hdrs["Content-Type"] = "application/json"
        elif raw is not None:
            data = raw
        req = urllib.request.Request(self.base + path, data=data, headers=hdrs, method=method)
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return resp.status, resp.read(), resp.headers
        except urllib.error.HTTPError as exc:
            return exc.code, exc.read(), exc.headers

    def json_call(self, method, path, body=None, **kw):
        code, data, _ = self.call(method, path, body=body, **kw)
        return code, json.loads(data.decode() or "null")

    def upload(self, local, name=None):
        code, data, _ = self.call("PUT", "/api/files/" + urllib.request.quote(name or local.name),
                                  raw=Path(local).read_bytes())
        self.assertEqual(code, 201, data)
        return json.loads(data)

    def run_job(self, tool, params, timeout=90):
        code, job = self.json_call("POST", "/api/jobs", {"tool": tool, "params": params})
        self.assertEqual(code, 201, job)
        deadline = time.time() + timeout
        while time.time() < deadline:
            _, job = self.json_call("GET", "/api/jobs/" + job["id"])
            if job["state"] not in ("queued", "running"):
                return job
            time.sleep(0.3)
        self.fail(f"job {tool} did not finish")

    # --- auth & static -------------------------------------------------------
    def test_health_without_token(self):
        code, data = self.json_call("GET", "/healthz", token=None)
        self.assertEqual(code, 200)
        self.assertTrue(data["ok"])

    def test_auth_required(self):
        self.assertEqual(self.call("GET", "/api/status", token=None)[0], 401)
        self.assertEqual(self.call("GET", "/api/status", token="wrong")[0], 401)
        self.assertEqual(self.call("POST", "/api/jobs", body={"tool": "trim"}, token="wrong")[0], 401)
        self.assertEqual(self.call("PUT", "/api/files/x.txt", raw=b"x", token=None)[0], 401)
        code, status = self.json_call("GET", "/api/status")
        self.assertEqual(code, 200)
        self.assertGreaterEqual(status["tools_total"], 20)
        self.assertIn("disk", status)

    def test_status_shows_version_and_update(self):
        status = self.json_call("GET", "/api/status")[1]
        self.assertRegex(status["version"], r"^\d+\.\d+\.\d+$")
        if shutil.which("git"):
            self.assertRegex(status["repo"].get("commit", ""), r"^[0-9a-f]{7,}$")
        self.assertIsNone(status["update"])
        path = Path(self.settings.workdir) / "update-status.json"
        path.write_text(json.dumps({"time": 1, "result": "tests-failed", "message": "x"}))
        try:
            self.assertEqual(self.json_call("GET", "/api/status")[1]["update"]["result"], "tests-failed")
        finally:
            path.unlink()

    def test_static_and_traversal(self):
        code, data, headers = self.call("GET", "/", token=None)
        self.assertEqual(code, 200)
        self.assertIn(b"<title>", data)
        self.assertIn("default-src 'self'", headers["Content-Security-Policy"])
        self.assertIn("frame-ancestors 'none'", headers["Content-Security-Policy"])
        code, _, headers = self.call("GET", "/static/js/main.js", token=None)
        self.assertEqual(code, 200)
        self.assertTrue(headers["Content-Type"].startswith("text/javascript"))  # pinned for ES modules
        self.assertEqual(self.call("GET", "/static/js/main.js", token=None,
                                   headers={"If-Modified-Since": headers["Last-Modified"]})[0], 304)
        self.assertEqual(self.call("GET", "/static/../hub/config.py", token=None)[0], 404)
        self.assertEqual(self.call("GET", "/static/%2e%2e/hub/config.py", token=None)[0], 404)

    def test_metrics_history_and_ui_config(self):
        deadline = time.time() + 15
        while time.time() < deadline:
            code, m = self.json_call("GET", "/api/metrics")
            if m.get("time"):
                break
            time.sleep(0.3)
        self.assertEqual(code, 200)
        self.assertIn(m["status"], ("ok", "warn", "crit"))
        for key in ("cpu", "memory", "disks", "net", "alerts", "services", "top_cpu", "jobs", "version"):
            self.assertIn(key, m)
        self.assertTrue(any(d["workdir"] for d in m["disks"]))
        code, hist = self.json_call("GET", "/api/metrics/history?range=15m")
        self.assertEqual(code, 200)
        self.assertEqual(len(hist["series"]["t"]), len(hist["series"]["cpu"]))
        code, ui = self.json_call("GET", "/api/ui")
        self.assertEqual(code, 200)
        self.assertEqual(ui["version"], m["version"])
        self.assertEqual(self.call("GET", "/api/metrics", token=None)[0], 401)

    def test_delete_and_cleanup_jobs(self):
        code, job = self.json_call("POST", "/api/jobs", {"tool": "echo_args", "params": {"a": "x"}})
        self.assertEqual(code, 201)
        for _ in range(50):
            if self.json_call("GET", "/api/jobs/" + job["id"])[1]["state"] == "done":
                break
            time.sleep(0.1)
        self.assertGreater(self.json_call("GET", "/api/jobs/usage")[1]["files"], 0)
        self.assertEqual(self.json_call("DELETE", "/api/jobs/" + job["id"])[0], 200)
        self.assertEqual(self.json_call("GET", "/api/jobs/" + job["id"])[0], 404)
        self.assertEqual(self.json_call("DELETE", "/api/jobs/" + job["id"])[0], 404)
        self.assertEqual(self.json_call("POST", "/api/jobs/cleanup", {"older_than_days": 0})[0], 400)
        code, res = self.json_call("POST", "/api/jobs/cleanup", {"older_than_days": 30})
        self.assertEqual(code, 200)
        self.assertEqual(res["deleted"], 0)  # nothing that old

    # --- files ---------------------------------------------------------------
    def test_upload_sanitizes_name(self):
        src = self.tmp / "note.txt"
        src.write_text("привет")
        info = self.upload(src, name="../../evil name.sh")
        self.assertEqual(info["path"], "inputs/evil_name.sh")
        self.assertTrue((Path(self.settings.workdir) / "inputs" / "evil_name.sh").exists())
        self.assertFalse((self.tmp / "evil name.sh").exists())
        code, files = self.json_call("GET", "/api/files")
        self.assertIn("inputs/evil_name.sh", [f["path"] for f in files])
        self.assertEqual(self.call("DELETE", "/api/files/evil_name.sh")[0], 200)

    def test_download_outside_workdir_refused(self):
        self.assertEqual(self.call("GET", "/api/download?path=../tools.local.json")[0], 404)
        self.assertEqual(self.call("GET", "/api/download?path=/etc/passwd")[0], 404)
        self.assertEqual(self.call("GET", "/api/link?path=../../etc/passwd")[0], 404)

    # --- params & argv -------------------------------------------------------
    def test_build_argv_keeps_values_in_one_argument(self):
        tool = self.hub.jobs.tools["echo_args"]
        job_dir = self.tmp / "argv"
        job_dir.mkdir(exist_ok=True)
        argv = build_argv(tool, {"a": "1 2 && rm"}, {}, self.settings.workdir, job_dir, "/r", "py")
        self.assertEqual(argv, ["echo", "A=1 2 && rm", "B=x y;z"])  # empty optional {opt} dropped
        with self.assertRaises(ParamError):
            build_argv(tool, {"a": "--evil"}, {}, self.settings.workdir, job_dir, "/r", "py")
        with self.assertRaises(ParamError):
            build_argv(tool, {}, {}, self.settings.workdir, job_dir, "/r", "py")

    def test_bare_file_name_means_inputs(self):
        note = self.tmp / "note one.txt"
        note.write_text("bare name works", encoding="utf-8")
        self.assertEqual(self.upload(note)["path"], "inputs/note_one.txt")
        for name in ("note_one.txt", "note one.txt", "inputs/note_one.txt"):
            with self.subTest(name=name):
                job = self.run_job("show_file", {"f": name})
                self.assertEqual(job["state"], "done", job["log"])
                self.assertIn("bare name works", job["log"])
        code, err = self.json_call("POST", "/api/jobs", {"tool": "show_file", "params": {"f": "nope.txt"}})
        self.assertEqual(code, 400)
        self.assertIn("inputs/nope.txt", err["error"])
        for bad in ("..", ".", "../note one.txt"):  # the last one exists, but outside the work folder
            self.assertEqual(self.json_call("POST", "/api/jobs", {"tool": "show_file", "params": {"f": bad}})[0], 400)

    def test_gpu_variant_falls_back_to_cpu(self):
        _, tools = self.json_call("GET", "/api/tools")
        tool = next(t for t in tools if t["id"] == "gpu_fallback")
        self.assertEqual(tool["gpu"], {"available": True, "reason": ""})
        device = [p for p in tool["params"] if p["name"] == "device"]
        self.assertEqual(len(device), 1)
        self.assertEqual(device[0]["default"], "auto")
        self.assertEqual(set(device[0]["labels"]), {"auto", "gpu", "cpu"})

        job = self.run_job("gpu_fallback", {})
        self.assertEqual(job["state"], "done", job["log"])
        self.assertEqual(job["runs"], [{"device": "gpu", "returncode": 3}, {"device": "cpu", "returncode": 0}])
        self.assertEqual(job["device"], "cpu")
        log = job["log"]
        self.assertLess(log.index("GPU try"), log.index("Видеокарта не справилась (код 3)"))
        self.assertIn("CPU ''", log)  # cpu_env hides the card from the CPU run
        _, jobs = self.json_call("GET", "/api/jobs")
        self.assertEqual(next(j for j in jobs if j["id"] == job["id"])["device"], "cpu")

        job = self.run_job("gpu_fallback", {"device": "gpu"})
        self.assertEqual(job["state"], "failed")
        self.assertEqual(job["runs"], [{"device": "gpu", "returncode": 3}])
        self.assertNotIn("CPU", job["log"])

        job = self.run_job("gpu_fallback", {"device": "cpu"})
        self.assertEqual(job["state"], "done", job["log"])
        self.assertEqual(job["runs"], [{"device": "cpu", "returncode": 0}])
        self.assertNotIn("GPU try", job["log"])

        code, err = self.json_call("POST", "/api/jobs", {"tool": "gpu_missing", "params": {"device": "gpu"}})
        self.assertEqual(code, 400)
        self.assertIn("видеокарта недоступна", err["error"])
        job = self.run_job("gpu_missing", {})
        self.assertEqual((job["state"], job["runs"]), ("done", [{"device": "cpu", "returncode": 0}]))
        self.assertIn("cpu only", job["log"])
        code, _ = self.json_call("POST", "/api/jobs", {"tool": "gpu_fallback", "params": {"device": "tpu"}})
        self.assertEqual(code, 400)

    def test_variables_expand_home_and_workdir(self):
        tool = {"id": "v", "command": ["echo", "{models}", "{home}", "{workdir}"], "params": []}
        job_dir = self.tmp / "vars"
        job_dir.mkdir(exist_ok=True)
        runs = build_runs(tool, {}, {"models": "{workdir}/models/x", "home": "~/voices"},
                          self.settings.workdir, job_dir, "/r", "py")
        work = str(Path(self.settings.workdir).resolve())
        self.assertEqual(runs, [{"device": "", "env": {}, "argv": ["echo", work + "/models/x",
                                                                    os.path.expanduser("~/voices"), work]}])

    def test_job_param_errors(self):
        self.assertEqual(self.json_call("POST", "/api/jobs", {"tool": "nope"})[0], 404)
        code, err = self.json_call("POST", "/api/jobs", {"tool": "loudness_report",
                                                         "params": {"input": "../../etc/passwd"}})
        self.assertEqual(code, 400, err)
        code, err = self.json_call("POST", "/api/jobs", {"tool": "loudness_report",
                                                         "params": {"input": "/etc/passwd"}})
        self.assertEqual(code, 400, err)
        code, err = self.json_call("POST", "/api/jobs", {"tool": "trim",
                                                         "params": {"input": "x", "end": "-1"}})
        self.assertEqual(code, 400, err)
        code, err = self.json_call("POST", "/api/jobs", {"tool": "contact_sheet",
                                                         "params": {"input": "x", "cols": 99}})
        self.assertEqual(code, 400, err)
        self.assertEqual(self.json_call("POST", "/api/jobs", {"tool": "needs_missing"})[0], 409)

    def test_cancel(self):
        code, job = self.json_call("POST", "/api/jobs", {"tool": "sleeper"})
        self.assertEqual(code, 201)
        time.sleep(0.5)
        self.assertTrue(self.json_call("POST", f"/api/jobs/{job['id']}/cancel")[1]["cancelled"])
        for _ in range(50):
            _, info = self.json_call("GET", "/api/jobs/" + job["id"])
            if info["finished"]:
                break
            time.sleep(0.1)
        self.assertEqual(info["state"], "cancelled")

    # --- real tools ----------------------------------------------------------
    @unittest.skipUnless(HAS_FFMPEG, "ffmpeg not installed")
    def test_loudness_report(self):
        info = self.upload(self.wav)
        job = self.run_job("loudness_report", {"input": info["path"], "role": "master"})
        self.assertEqual(job["state"], "done", job["log"])
        self.assertIn("LUFS", job["log"])
        report = job["report"][0]  # --json-out → the UI renders numbers, not the log
        self.assertIsNotNone(report["integrated_lufs"])
        self.assertEqual(report["role"], "master")

    @unittest.skipUnless(HAS_FFMPEG, "ffmpeg not installed")
    def test_transcode_and_download(self):
        info = self.upload(self.video)
        job = self.run_job("transcode_x264", {"input": info["path"], "crf": 28})
        self.assertEqual(job["state"], "done", job["log"])
        out = job["files"][0]["path"]
        self.assertTrue(out.endswith("video.mp4"))
        code, data, headers = self.call("GET", "/api/download?path=" + out, headers={"Range": "bytes=0-99"})
        self.assertEqual(code, 206)
        self.assertEqual(len(data), 100)
        self.assertIn("sandbox", headers["Content-Security-Policy"])
        # signed link works without a token, a tampered one does not
        _, link = self.json_call("GET", "/api/link?path=" + out)
        code, data, headers = self.call("GET", link["inline_url"], token=None)
        self.assertEqual(code, 200)
        self.assertEqual(headers["Content-Type"], "video/mp4")
        self.assertTrue(headers["Content-Disposition"].startswith("inline"))
        self.assertEqual(self.call("GET", link["url"].replace("sig=", "sig=0"), token=None)[0], 403)

    @unittest.skipUnless(HAS_FFMPEG, "ffmpeg not installed")
    def test_contact_sheet_and_vertical(self):
        info = self.upload(self.video)
        job = self.run_job("contact_sheet", {"input": info["path"], "every": 1, "cols": 2, "rows": 2})
        self.assertEqual(job["state"], "done", job["log"])
        self.assertEqual(job["files"][0]["name"], "sheet.jpg")
        job = self.run_job("vertical_9x16", {"input": info["path"], "crf": 30})
        self.assertEqual(job["state"], "done", job["log"])
        probe = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                                "stream=width,height", "-of", "csv=p=0",
                                str(Path(self.settings.workdir) / job["files"][0]["path"])],
                               capture_output=True, text=True).stdout.strip()
        self.assertEqual(probe, "1080,1920")

    @unittest.skipUnless(HAS_FFMPEG, "ffmpeg not installed")
    def test_every_ffmpeg_tool(self):
        wav = self.upload(self.wav, name="all.wav")["path"]
        mp4 = self.upload(self.video, name="all.mp4")["path"]
        srt = self.tmp / "subs.srt"
        srt.write_text("1\n00:00:00,000 --> 00:00:02,000\nПривет, мир\n", encoding="utf-8")
        subs = self.upload(srt)["path"]
        cases = {
            "mix_compare": ({"mix": wav, "reference": wav}, None),
            "loudnorm": ({"input": wav, "target": -16}, "normalized.wav"),
            "to_wav48": ({"input": mp4}, "audio.wav"),
            "to_wav16_mono": ({"input": wav}, "speech16k.wav"),
            "silence_detect": ({"input": wav}, None),
            "thumbnail": ({"input": mp4, "at": 1}, "frame.jpg"),
            "trim": ({"input": mp4, "start": "0.5", "end": "2"}, "fragment.mov"),
            "gif_preview": ({"input": mp4, "duration": 1, "width": 160}, "preview.gif"),
            "burn_subtitles": ({"input": mp4, "subs": subs}, "subtitled.mp4"),
        }
        for tool, (params, expected) in cases.items():
            with self.subTest(tool=tool):
                job = self.run_job(tool, params)
                self.assertEqual(job["state"], "done", job["log"][-1500:])
                if expected:
                    self.assertIn(expected, [f["name"] for f in job["files"]])

    def test_tts_tool_with_mock_server(self):
        MockTTS.requests.clear()
        text = ("Первое предложение. " * 30 + "\n\n") * 3  # long text → several requests
        job = self.run_job("tts", {"text": text, "voice": "aidar"})
        self.assertEqual(job["state"], "done", job["log"])
        self.assertGreater(len(MockTTS.requests), 1)
        self.assertEqual(MockTTS.requests[0]["path"], "/v1/audio/speech")
        self.assertEqual(MockTTS.requests[0]["body"]["voice"], "aidar")
        wav_path = Path(self.settings.workdir) / job["files"][0]["path"]
        with wave.open(str(wav_path)) as w:
            self.assertGreater(w.getnframes(), 16000 * 0.5 * len(MockTTS.requests))

    # --- data ----------------------------------------------------------------
    def test_catalog(self):
        code, cat = self.json_call("GET", "/api/catalog")
        self.assertEqual(code, 200)
        self.assertGreater(len(cat["items"]), 50)
        names = " ".join(i["name"].lower() for i in cat["items"])
        self.assertIn("superpowers", names)
        self.assertIn("music-studio", [p["name"] for p in cat["packs"]])
        self.assertEqual(set(cat["directions"]),
                         {"video", "animation", "audio", "coding", "productivity", "business", "common"})

    def test_resources_and_sets(self):
        code, res = self.json_call("GET", "/api/resources")
        self.assertEqual(code, 200)
        self.assertGreater(len(res["items"]), 20)
        for item in res["items"]:
            self.assertIn(item["category"], res["categories"], item["name"])
            self.assertTrue(item["url"].startswith("https://"), item["name"])
        code, sets = self.json_call("GET", "/api/starter-sets")
        self.assertEqual(code, 200)
        self.assertGreaterEqual(len(sets["sets"]), 5)

    # --- MCP bridge ----------------------------------------------------------
    def test_mcp_bridge(self):
        env = dict(os.environ, HUB_URL=self.base, HUB_TOKEN=TOKEN, HUB_DOWNLOAD_DIR=str(self.tmp / "dl"))
        proc = subprocess.Popen([sys.executable, str(APP / "mcp_bridge.py")], stdin=subprocess.PIPE,
                                stdout=subprocess.PIPE, text=True, env=env)
        counter = iter(range(1, 100))

        def rpc(method, params=None):
            msg_id = next(counter)
            proc.stdin.write(json.dumps({"jsonrpc": "2.0", "id": msg_id, "method": method,
                                         "params": params or {}}) + "\n")
            proc.stdin.flush()
            reply = json.loads(proc.stdout.readline())
            self.assertEqual(reply["id"], msg_id)
            return reply

        def tool(name, **args):
            result = rpc("tools/call", {"name": name, "arguments": args})["result"]
            return result

        try:
            init = rpc("initialize", {"protocolVersion": "2025-06-18", "capabilities": {},
                                      "clientInfo": {"name": "test", "version": "0"}})
            self.assertEqual(init["result"]["protocolVersion"], "2025-06-18")
            proc.stdin.write(json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized"}) + "\n")
            names = [t["name"] for t in rpc("tools/list")["result"]["tools"]]
            self.assertIn("hub_run", names)
            self.assertEqual(rpc("nope")["error"]["code"], -32601)
            for _ in range(60):  # the sampler needs a moment after start
                if self.json_call("GET", "/api/metrics")[1].get("time"):
                    break
                time.sleep(0.25)
            status = tool("hub_status")
            self.assertFalse(status["isError"])
            self.assertIn("Сервер", status["content"][0]["text"])
            self.assertIn("Диски:", status["content"][0]["text"])
            detail = json.loads(tool("hub_status", detail=True)["content"][0]["text"])
            self.assertIn("disks", detail)
            self.assertIn("loudness_report", tool("hub_tools")["content"][0]["text"])
            self.assertIn("Найдено", tool("hub_catalog", query="ffmpeg")["content"][0]["text"])
            note = self.tmp / "bridge-note.txt"
            note.write_text("строка для проверки")
            up = tool("hub_upload", local_path=str(note))
            self.assertIn("inputs/bridge-note.txt", up["content"][0]["text"])
            view = tool("hub_view", path="inputs/bridge-note.txt")
            self.assertEqual(view["content"][0]["text"], "строка для проверки")
            down = tool("hub_download", path="inputs/bridge-note.txt")
            self.assertTrue((self.tmp / "dl" / "bridge-note.txt").exists(), down)
            bad = tool("hub_run", tool="loudness_report", params={"input": "../x"})
            self.assertTrue(bad["isError"])
            if HAS_FFMPEG:
                self.upload(self.wav, name="bridge.wav")
                run = tool("hub_run", tool="loudness_report", params={"input": "inputs/bridge.wav"},
                           wait_seconds=60)
                self.assertIn(": done", run["content"][0]["text"])
                self.upload(self.video, name="bridge.mp4")
                run = tool("hub_run", tool="thumbnail", params={"input": "inputs/bridge.mp4", "at": 1})
                frame = [l.strip().split(" ")[0] for l in run["content"][0]["text"].splitlines()
                         if l.strip().endswith("байт)")][0]
                img = tool("hub_view", path=frame)
                self.assertEqual(img["content"][0]["type"], "image")
                self.assertEqual(img["content"][0]["mimeType"], "image/jpeg")
        finally:
            proc.stdin.close()
            proc.wait(timeout=10)


class ExtendPathTest(unittest.TestCase):
    def test_adds_existing_folders_once(self):
        saved = os.environ.get("PATH", "")
        try:
            with tempfile.TemporaryDirectory() as extra:
                os.environ["PATH"] = "/usr/bin"
                self.assertEqual(extend_path([extra, "/definitely/missing/dir", extra]), [extra])
                self.assertEqual(os.environ["PATH"], "/usr/bin" + os.pathsep + extra)
                self.assertEqual(extend_path([extra]), [])
        finally:
            os.environ["PATH"] = saved


class RegistryTest(unittest.TestCase):
    """The shipped tools.json: GPU variants, auto-editor flags, known placeholders."""

    @classmethod
    def setUpClass(cls):
        tools, cls.variables = load_tools(APP / "config" / "tools.json")
        cls.tools = {t["id"]: t for t in tools}

    def test_auto_editor_never_opens_a_viewer(self):
        for tid in ("auto_editor_cut", "auto_editor_premiere"):
            tool = self.tools[tid]
            for command in (tool["command"], (tool.get("gpu") or {}).get("command", ["--no-open"])):
                self.assertIn("--no-open", command, tid)

    def test_gpu_variants(self):
        gpu_tools = {tid for tid, t in self.tools.items() if t.get("gpu")}
        self.assertEqual(gpu_tools, {"vertical_9x16", "burn_subtitles", "contact_sheet", "auto_editor_cut", "stems"})
        for tid in ("vertical_9x16", "burn_subtitles", "contact_sheet"):
            command = self.tools[tid]["gpu"]["command"]
            self.assertLess(command.index("-hwaccel"), command.index("-i"), tid)
        for tid in ("vertical_9x16", "burn_subtitles"):
            command = self.tools[tid]["gpu"]["command"]
            self.assertIn("h264_nvenc", command)
            self.assertIn("-cq", command)
            self.assertNotIn("-crf", command)
        cut = self.tools["auto_editor_cut"]["gpu"]["command"]
        self.assertIn("-b:v", cut)  # without a bitrate NVENC makes the file ~3x bigger
        self.assertEqual(self.tools["stems"]["gpu"]["cpu_env"], {"CUDA_VISIBLE_DEVICES": ""})

    def test_placeholders_are_known(self):
        from hub.tools import BUILTINS, PLACEHOLDER
        for tid, tool in self.tools.items():
            names = {p["name"] for p in tool.get("params", [])} | set(BUILTINS) | set(self.variables)
            for arg in [*tool["command"], *(tool.get("gpu") or {}).get("command", [])]:
                for name in PLACEHOLDER.findall(arg):
                    self.assertIn(name, names, f"{tid}: {{{name}}}")

    def test_choice_labels_cover_choices(self):
        for tid, tool in self.tools.items():
            for p in tool.get("params", []):
                if p.get("labels"):
                    self.assertEqual(set(p["labels"]), set(p["choices"]), f"{tid}.{p['name']}")


class TtsSplitTest(unittest.TestCase):
    def test_split(self):
        sys.path.insert(0, str(APP / "tools"))
        from tts_openai import endpoint, split_text
        chunks = split_text("Раз. Два! Три?\n\nЧетыре… " + "слово " * 300, 200)
        self.assertTrue(all(len(c) <= 200 for c in chunks))
        self.assertEqual(chunks[0], "Раз. Два! Три?")
        self.assertEqual(endpoint("http://h:1"), "http://h:1/v1/audio/speech")
        self.assertEqual(endpoint("http://h:1/v1/"), "http://h:1/v1/audio/speech")


if __name__ == "__main__":
    unittest.main()
