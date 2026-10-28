"""deploy/update.sh against a throwaway origin: update, rollback, skip, guard.

    cd app && python3 -m unittest tests.test_update -v
"""
import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

APP = Path(__file__).resolve().parents[1]
UPDATE_SH = APP / "deploy" / "update.sh"
GIT_ENV = {"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@example.com",
           "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@example.com"}
PASSING = "import unittest\n\nclass T(unittest.TestCase):\n    def test_ok(self):\n        pass\n"
FAILING = "import unittest\n\nclass T(unittest.TestCase):\n    def test_bad(self):\n        self.fail('broken')\n"


@unittest.skipUnless(shutil.which("git") and shutil.which("flock"), "git and flock needed")
class UpdateScriptTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="hubupdate-"))
        self.env = dict(os.environ, **GIT_ENV)
        self.origin = self.tmp / "origin"
        (self.origin / "app" / "deploy").mkdir(parents=True)
        (self.origin / "app" / "tests").mkdir()
        shutil.copy(UPDATE_SH, self.origin / "app" / "deploy" / "update.sh")
        self.write_test(PASSING)
        self.git(self.origin, "init", "-q", "-b", "main")
        self.commit("first")
        self.server = self.tmp / "server"
        subprocess.run(["git", "clone", "-q", str(self.origin), str(self.server)], check=True, env=self.env)
        self.work = self.tmp / "work"
        self.marker = self.tmp / "restarted"

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def git(self, repo, *args):
        return subprocess.run(["git", "-C", str(repo), *args], check=True, env=self.env,
                              capture_output=True, text=True).stdout.strip()

    def write_test(self, body):
        (self.origin / "app" / "tests" / "test_x.py").write_text(body)

    def commit(self, message):
        self.git(self.origin, "add", "-A")
        self.git(self.origin, "commit", "-q", "-m", message)
        return self.git(self.origin, "rev-parse", "HEAD")

    def run_update(self, *args):
        env = dict(self.env, HUB_WORKDIR=str(self.work), HUB_RESTART_CMD=f"touch {self.marker}")
        proc = subprocess.run(["bash", str(self.server / "app" / "deploy" / "update.sh"), *args],
                              env=env, capture_output=True, text=True, timeout=120)
        status = json.loads((self.work / "update-status.json").read_text())
        return proc.returncode, status

    def head(self):
        return self.git(self.server, "rev-parse", "HEAD")

    def test_up_to_date(self):
        code, status = self.run_update()
        self.assertEqual((code, status["result"]), (0, "up-to-date"))
        self.assertFalse(self.marker.exists())

    def test_update_then_restart(self):
        (self.origin / "app" / "new.txt").write_text("feature")
        new = self.commit("Add a feature")
        code, status = self.run_update()
        self.assertEqual((code, status["result"]), (0, "updated"), status)
        self.assertEqual(self.head(), new)
        self.assertIn("Add a feature", status["message"])
        self.assertTrue(self.marker.exists())

    def test_failing_tests_roll_back_and_skip(self):
        old = self.head()
        self.write_test(FAILING)
        bad = self.commit("Break tests")
        code, status = self.run_update()
        self.assertEqual((code, status["result"]), (1, "tests-failed"))
        self.assertEqual(self.head(), old)
        self.assertEqual(status["failed_commit"], bad)
        self.assertFalse(self.marker.exists())
        code, status = self.run_update()  # same commit is not retried
        self.assertEqual(code, 0)
        self.assertEqual(self.head(), old)
        self.write_test(PASSING)
        good = self.commit("Fix tests")
        code, status = self.run_update()
        self.assertEqual((code, status["result"]), (0, "updated"))
        self.assertEqual(self.head(), good)
        self.assertEqual(status["failed_commit"], "")

    def test_local_changes_stop_update(self):
        (self.server / "app" / "tests" / "test_x.py").write_text(PASSING + "# local edit\n")
        code, status = self.run_update()
        self.assertEqual((code, status["result"]), (1, "local-changes"))
        self.assertFalse(self.marker.exists())


if __name__ == "__main__":
    unittest.main()
