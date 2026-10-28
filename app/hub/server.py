"""HTTP server: JSON API (token required) + static UI. Standard library only."""
import argparse
import hashlib
import hmac
import json
import mimetypes
import sys
import time
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlencode, urlparse

from . import __version__
from .catalog import build_catalog
from .config import APP_DIR, load_settings
from .jobs import JobManager
from .sysinfo import repo_info, update_status
from .sysinfo import status as sys_status
from .tools import ParamError, load_tools, public_tool, safe_filename

STATIC_DIR = APP_DIR / "static"
CHUNK = 1024 * 1024
LINK_TTL = 15 * 60  # seconds a signed download link stays valid
INLINE_TYPES = ("image/", "audio/", "video/", "text/plain")


class Hub:
    """Shared state for all requests."""

    def __init__(self, settings):
        self.settings = settings
        tools, variables = load_tools(settings.tools_file, settings.tools_local_file)
        self.tools = tools
        self.variables = variables
        self.jobs = JobManager(settings, tools, variables)
        self._catalog = None
        self._catalog_time = 0

    def catalog(self, refresh=False):
        if refresh or self._catalog is None or time.time() - self._catalog_time > 300:
            self._catalog = build_catalog(self.settings.repo_root)
            self._catalog_time = time.time()
        return self._catalog

    def read_json_file(self, path, fallback):
        try:
            with open(path, encoding="utf-8") as f:
                return json.load(f)
        except (OSError, ValueError):
            return fallback


class Handler(BaseHTTPRequestHandler):
    server_version = "HomeHub/" + __version__
    hub = None  # set by make_server

    # --- helpers -----------------------------------------------------------
    def log_message(self, fmt, *args):  # quieter log without tokens or bodies
        sys.stderr.write("%s %s\n" % (self.command, self.path.split("?")[0]))

    def _headers(self, code, ctype, length=None, extra=None):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Cache-Control", "no-store")
        if length is not None:
            self.send_header("Content-Length", str(length))
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()

    def _json(self, data, code=200):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self._headers(code, "application/json; charset=utf-8", len(body))
        self.wfile.write(body)

    def _error(self, code, message):
        self._json({"error": message}, code)

    def _authorized(self):
        header = self.headers.get("Authorization", "")
        token = header[7:] if header.startswith("Bearer ") else ""
        return hmac.compare_digest(token.encode(), self.hub.settings.token.encode())

    def _body_json(self):
        length = int(self.headers.get("Content-Length") or 0)
        if length > 1024 * 1024:
            raise ValueError("слишком большой запрос")
        raw = self.rfile.read(length) if length else b"{}"
        return json.loads(raw.decode("utf-8") or "{}")

    def _workdir_path(self, rel):
        root = Path(self.hub.settings.workdir).resolve()
        path = (root / unquote(rel).lstrip("/")).resolve()
        if root not in path.parents:
            return None
        return path

    def _sign(self, rel, exp):
        msg = f"{rel}\n{exp}".encode("utf-8")
        return hmac.new(self.hub.settings.token.encode(), msg, hashlib.sha256).hexdigest()

    def _list_files(self, scope):
        root = Path(self.hub.settings.workdir)
        found = [p for p in (root / "inputs").iterdir() if p.is_file() and not p.name.endswith(".part")]
        if scope == "all":
            found += [p for p in (root / "jobs").glob("*/out/**/*") if p.is_file()]
        found.sort(key=lambda p: p.stat().st_mtime, reverse=True)
        return [{"name": p.name, "size": p.stat().st_size, "mtime": p.stat().st_mtime,
                 "path": str(p.relative_to(root))} for p in found[:500]]

    def _send_file(self, target, inline=False):
        """Stream a file; supports a single byte Range so video can seek."""
        ctype = mimetypes.guess_type(str(target))[0] or "application/octet-stream"
        inline = inline and ctype.startswith(INLINE_TYPES)
        size = target.stat().st_size
        start, end = 0, size - 1
        code = 200
        rng = self.headers.get("Range", "")
        if rng.startswith("bytes=") and "," not in rng and size:
            first, _, last = rng[6:].partition("-")
            try:
                if first:
                    start = int(first)
                    end = min(int(last), size - 1) if last else size - 1
                else:
                    start = max(size - int(last), 0)
                if start > end or start >= size:
                    raise ValueError
                code = 206
            except ValueError:
                self._headers(416, "text/plain", 0, {"Content-Range": f"bytes */{size}"})
                return
        disposition = "inline" if inline else "attachment"
        extra = {
            "Accept-Ranges": "bytes",
            "Content-Disposition": f"{disposition}; filename=\"{safe_filename(target.name)}\"",
            "Content-Security-Policy": "sandbox",
        }
        if code == 206:
            extra["Content-Range"] = f"bytes {start}-{end}/{size}"
        # anything that is not plain media goes out as an opaque download
        sent_type = ctype if ctype.startswith(INLINE_TYPES) else "application/octet-stream"
        self._headers(code, sent_type, end - start + 1, extra)
        if self.command == "HEAD":
            return
        with open(target, "rb") as f:
            f.seek(start)
            remaining = end - start + 1
            while remaining > 0:
                chunk = f.read(min(CHUNK, remaining))
                if not chunk:
                    break
                try:
                    self.wfile.write(chunk)
                except (BrokenPipeError, ConnectionResetError):
                    return
                remaining -= len(chunk)

    # --- static ------------------------------------------------------------
    def _static(self, rel):
        rel = rel or "index.html"
        path = (STATIC_DIR / rel).resolve()
        if STATIC_DIR.resolve() not in path.parents or not path.is_file():
            return self._error(404, "не найдено")
        data = path.read_bytes()
        ctype = mimetypes.guess_type(str(path))[0] or "application/octet-stream"
        if ctype.startswith("text/") or ctype in ("application/javascript",):
            ctype += "; charset=utf-8"
        self._headers(200, ctype, len(data), {
            "Content-Security-Policy": "default-src 'self'; img-src 'self' blob: data:; "
                                       "media-src 'self' blob:; style-src 'self'; script-src 'self'",
            "Referrer-Policy": "no-referrer",
        })
        self.wfile.write(data)

    # --- routing -----------------------------------------------------------
    def do_GET(self):
        url = urlparse(self.path)
        path, query = url.path, parse_qs(url.query)
        if path == "/healthz":
            return self._json({"ok": True, "version": __version__})
        if path == "/dl":  # signed link: lets <video>/<a download> work without headers
            rel = query.get("path", [""])[0]
            exp = query.get("exp", ["0"])[0]
            sig = query.get("sig", [""])[0]
            if not exp.isdigit() or int(exp) < time.time() or \
                    not hmac.compare_digest(sig, self._sign(rel, int(exp))):
                return self._error(403, "ссылка устарела или неверна")
            target = self._workdir_path(rel)
            if not target or not target.is_file():
                return self._error(404, "файл не найден")
            return self._send_file(target, inline="inline" in query)
        if not path.startswith("/api/"):
            return self._static(path.lstrip("/").removeprefix("static/") if path != "/" else "")
        if not self._authorized():
            return self._error(401, "нужен токен")
        hub = self.hub
        if path == "/api/status":
            info = sys_status(hub.settings.workdir)
            tools = [public_tool(t, hub.variables) for t in hub.tools]
            info["tools_total"] = len(tools)
            info["tools_available"] = sum(t["available"] for t in tools)
            info["jobs"] = hub.jobs.list(limit=10)
            info["version"] = __version__
            info["repo"] = repo_info(hub.settings.repo_root)
            info["update"] = update_status(hub.settings.workdir)
            return self._json(info)
        if path == "/api/tools":
            return self._json([public_tool(t, hub.variables) for t in hub.tools])
        if path == "/api/jobs":
            return self._json(hub.jobs.list())
        if path.startswith("/api/jobs/"):
            job = hub.jobs.get(path.split("/")[3])
            return self._json(job) if job else self._error(404, "нет такой задачи")
        if path == "/api/files":
            return self._json(self._list_files(query.get("scope", ["inputs"])[0]))
        if path == "/api/download":
            target = self._workdir_path(query.get("path", [""])[0])
            if not target or not target.is_file():
                return self._error(404, "файл не найден")
            return self._send_file(target)
        if path == "/api/link":
            rel = query.get("path", [""])[0]
            target = self._workdir_path(rel)
            if not target or not target.is_file():
                return self._error(404, "файл не найден")
            exp = int(time.time()) + LINK_TTL
            link = f"/dl?{urlencode({'path': rel, 'exp': exp, 'sig': self._sign(rel, exp)})}"
            return self._json({"url": link, "inline_url": link + "&inline=1", "expires": exp})
        if path == "/api/catalog":
            return self._json(hub.catalog(refresh="refresh" in query))
        if path == "/api/resources":
            return self._json(hub.read_json_file(hub.settings.resources_file, {"items": []}))
        if path == "/api/starter-sets":
            return self._json(hub.read_json_file(hub.settings.starter_sets_file, {"sets": []}))
        return self._error(404, "не найдено")

    def do_POST(self):
        path = urlparse(self.path).path
        if not path.startswith("/api/") or not self._authorized():
            return self._error(401, "нужен токен")
        try:
            body = self._body_json()
        except (ValueError, json.JSONDecodeError) as exc:
            return self._error(400, f"неверный JSON: {exc}")
        if path == "/api/jobs":
            try:
                job = self.hub.jobs.submit(body.get("tool", ""), body.get("params") or {})
            except KeyError:
                return self._error(404, "нет такого инструмента")
            except ParamError as exc:
                return self._error(400, str(exc))
            except RuntimeError as exc:
                return self._error(409, str(exc))
            return self._json(job, 201)
        if path.startswith("/api/jobs/") and path.endswith("/cancel"):
            ok = self.hub.jobs.cancel(path.split("/")[3])
            return self._json({"cancelled": ok})
        return self._error(404, "не найдено")

    def do_PUT(self):
        path = urlparse(self.path).path
        if not path.startswith("/api/files/") or not self._authorized():
            return self._error(401, "нужен токен")
        name = safe_filename(unquote(path[len("/api/files/"):]))
        length = int(self.headers.get("Content-Length") or 0)
        limit = self.hub.settings.max_upload_mb * 1024 * 1024
        if length <= 0 or length > limit:
            return self._error(413, "пустой или слишком большой файл")
        dest = Path(self.hub.settings.workdir) / "inputs" / name
        tmp = dest.with_suffix(dest.suffix + ".part")
        remaining = length
        with open(tmp, "wb") as f:
            while remaining > 0:
                chunk = self.rfile.read(min(CHUNK, remaining))
                if not chunk:
                    break
                f.write(chunk)
                remaining -= len(chunk)
        if remaining:
            tmp.unlink(missing_ok=True)
            return self._error(400, "загрузка оборвалась")
        tmp.replace(dest)
        return self._json({"name": name, "path": f"inputs/{name}", "size": length}, 201)

    def do_DELETE(self):
        path = urlparse(self.path).path
        if not path.startswith("/api/files/") or not self._authorized():
            return self._error(401, "нужен токен")
        target = Path(self.hub.settings.workdir) / "inputs" / safe_filename(unquote(path[len("/api/files/"):]))
        if not target.is_file():
            return self._error(404, "файл не найден")
        target.unlink()
        return self._json({"deleted": target.name})


def make_server(settings):
    hub = Hub(settings)
    handler = type("BoundHandler", (Handler,), {"hub": hub})
    server = ThreadingHTTPServer((settings.bind, settings.port), handler)
    server.daemon_threads = True
    return server, hub


def main(argv=None):
    ap = argparse.ArgumentParser(description="Домашний пульт: API и интерфейс для инструментов сервера")
    ap.add_argument("--config", help="JSON с настройками (см. config/hub.example.json)")
    ap.add_argument("--bind")
    ap.add_argument("--port", type=int)
    ap.add_argument("--workdir")
    args = ap.parse_args(argv)
    settings = load_settings(args.config, {"bind": args.bind, "port": args.port, "workdir": args.workdir})
    server, hub = make_server(settings)
    print(f"Пульт запущен: http://{settings.bind}:{settings.port}/  (рабочая папка {settings.workdir})")
    if settings.token_generated:
        print(f"HUB_TOKEN не задан — временный токен на этот запуск: {settings.token}")
    avail = sum(public_tool(t, hub.variables)["available"] for t in hub.tools)
    print(f"Инструментов доступно: {avail} из {len(hub.tools)}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
