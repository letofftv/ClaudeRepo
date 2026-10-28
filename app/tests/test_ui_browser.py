"""The real interface in Chromium: every section, phone and desktop, light and dark.

    cd app && python3 -m unittest tests.test_ui_browser -v

Runs ui-studio's ui_check.mjs against a live test hub and fails on any FAIL
(horizontal scroll, JS/CSP errors, contrast, tap targets, unnamed controls).
Skipped when node or Playwright is missing — e.g. on the server, where the
static checks in test_ui_static.py still guard the update. HUB_SKIP_BROWSER=1
skips it on purpose.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import unittest
from pathlib import Path

APP = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(APP))
CHECK = APP.parent / "coding" / "packs" / "ui-studio" / "scripts" / "ui_check.mjs"

from hub.config import load_settings  # noqa: E402
from hub.server import make_server  # noqa: E402


def playwright_available():
    if os.environ.get("HUB_SKIP_BROWSER") or not shutil.which("node"):
        return False
    probe = ("const {createRequire}=require('module');const r=createRequire(process.cwd()+'/');"
             "try{r('playwright');process.exit(0)}catch(e){try{const g=require('child_process').execSync('npm root -g').toString().trim();"
             "r(g+'/playwright');process.exit(0)}catch(e2){process.exit(1)}}")
    return subprocess.run(["node", "-e", probe], capture_output=True, timeout=60).returncode == 0


@unittest.skipUnless(playwright_available(), "node + Playwright not available")
class BrowserAuditTest(unittest.TestCase):
    def test_every_section_passes_ui_check(self):
        with tempfile.TemporaryDirectory() as tmp:
            os.environ.pop("HUB_TOKEN", None)
            settings = load_settings(overrides={"bind": "127.0.0.1", "port": 0, "workdir": str(Path(tmp) / "work"),
                                                "token": "ui-test", "metrics_interval": 1,
                                                "services": [{"name": "Пульт", "tcp": "127.0.0.1:1", "timeout": 0.3}]})
            (Path(tmp) / "work").mkdir()
            server, hub = make_server(settings)
            threading.Thread(target=server.serve_forever, daemon=True).start()
            try:
                url = f"http://127.0.0.1:{server.server_address[1]}/"
                out = Path(tmp) / "report"
                proc = subprocess.run(["node", str(CHECK), "--url", url,
                                       "--routes", "#/,#/server,#/run,#/run?tab=files,#/jobs,#/library,#/library?tab=resources,#/settings",
                                       "--storage-json", "hub-token=ui-test", "--out", str(out), "--settle", "1800"],
                                      capture_output=True, text=True, timeout=600)
                report = json.loads((out / "report.json").read_text()) if (out / "report.json").exists() else []
                fails = [f"{r['route']} {r['viewport']}/{r['theme']}: [{f['check']}] {f['msg']}" for r in report for f in r["fails"]]
                self.assertEqual(proc.returncode, 0, "\n".join(fails[:30]) or proc.stdout[-2000:] + proc.stderr[-2000:])
                self.assertGreaterEqual(len(report), 32)
            finally:
                server.shutdown()
                server.server_close()
                hub.close()
                hub.jobs.pool.shutdown(wait=False, cancel_futures=True)


if __name__ == "__main__":
    unittest.main()
