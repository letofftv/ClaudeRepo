"""Settings: defaults, an optional JSON file and environment overrides."""
import json
import os
import secrets
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent.parent
REPO_ROOT = APP_DIR.parent

DEFAULTS = {
    "bind": "127.0.0.1",
    "port": 8787,
    "workdir": "~/hub-work",
    "tools_file": str(APP_DIR / "config" / "tools.json"),
    "tools_local_file": str(APP_DIR / "config" / "tools.local.json"),
    "resources_file": str(APP_DIR / "data" / "free-resources.json"),
    "starter_sets_file": str(APP_DIR / "data" / "starter-sets.json"),
    "repo_root": str(REPO_ROOT),
    "max_parallel_jobs": 2,
    "max_upload_mb": 4096,
}


class Settings(dict):
    """Plain dict with attribute access and resolved paths."""

    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError as exc:
            raise AttributeError(name) from exc


def load_settings(config_path=None, overrides=None):
    data = dict(DEFAULTS)
    if config_path:
        with open(config_path, encoding="utf-8") as f:
            data.update(json.load(f))
    env_map = {"HUB_BIND": "bind", "HUB_PORT": "port", "HUB_WORKDIR": "workdir"}
    for env, key in env_map.items():
        if os.environ.get(env):
            data[key] = os.environ[env]
    if overrides:
        data.update({k: v for k, v in overrides.items() if v is not None})

    data["port"] = int(data["port"])
    data["max_parallel_jobs"] = int(data["max_parallel_jobs"])
    data["max_upload_mb"] = int(data["max_upload_mb"])
    data["workdir"] = str(Path(os.path.expanduser(data["workdir"])).resolve())
    data["repo_root"] = str(Path(os.path.expanduser(data["repo_root"])).resolve())

    token = os.environ.get("HUB_TOKEN") or data.get("token")
    data["token_generated"] = not token
    data["token"] = token or secrets.token_urlsafe(24)
    return Settings(data)
