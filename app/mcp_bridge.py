#!/usr/bin/env python3
"""MCP server (stdio) that lets Claude Code drive the home hub.

Runs on the Mac next to Claude Code and talks to the hub over HTTP:

    claude mcp add home --env HUB_URL=http://<server>:8787 --env HUB_TOKEN=<token> \
        -- python3 /path/to/ClaudeRepo/app/mcp_bridge.py

Standard library only. Protocol: JSON-RPC 2.0, one message per line.
"""
import base64
import json
import mimetypes
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

PROTOCOL = "2025-06-18"
HUB_URL = os.environ.get("HUB_URL", "http://127.0.0.1:8787").rstrip("/")
HUB_TOKEN = os.environ.get("HUB_TOKEN", "")
DOWNLOAD_DIR = Path(os.path.expanduser(os.environ.get("HUB_DOWNLOAD_DIR", "~/Downloads/hub")))
VIEW_LIMIT = 4 * 1024 * 1024  # bytes of an image or text the model may receive at once


class HubError(Exception):
    pass


def request(method, path, body=None, raw=None, timeout=60, headers=None):
    hdrs = {"Authorization": "Bearer " + HUB_TOKEN}
    hdrs.update(headers or {})
    data = None
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        hdrs["Content-Type"] = "application/json"
    elif raw is not None:
        data = raw
    req = urllib.request.Request(HUB_URL + path, data=data, headers=hdrs, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read(), resp.headers
    except urllib.error.HTTPError as exc:
        try:
            msg = json.loads(exc.read().decode("utf-8")).get("error", exc.reason)
        except ValueError:
            msg = exc.reason
        raise HubError(f"пульт ответил {exc.code}: {msg}")
    except (urllib.error.URLError, OSError) as exc:
        raise HubError(f"пульт недоступен по {HUB_URL}: {exc}")


def api(method, path, body=None, timeout=60):
    data, _ = request(method, path, body=body, timeout=timeout)
    return json.loads(data.decode("utf-8"))


def q(value):
    return urllib.parse.quote(str(value), safe="")


# --- tools ---------------------------------------------------------------------
def _gb(n):
    return f"{(n or 0) / 1024 ** 3:.1f}".replace(".", ",") + " ГБ"


def _n(v, digits=1):
    if v is None:
        return "—"
    return f"{v:.{digits}f}".replace(".", ",") if isinstance(v, (int, float)) else str(v)


def summarize_metrics(m):
    """One paragraph a model can act on: verdict, alerts, key numbers, GPU readiness."""
    if not m.get("time"):
        return "Пульт только что запущен — данные о сервере появятся через несколько секунд."
    verdict = {"ok": "всё в порядке", "warn": "есть замечания", "crit": "есть проблемы"}.get(m.get("status"), "нет данных")
    age = max(0, round(m.get("now", time.time()) - (m.get("time") or 0)))
    lines = [f"Сервер {m.get('host', '')}: {verdict} (данные {age} с назад){' · WSL2' if m.get('wsl') else ''}"]
    alerts = [a for a in m.get("alerts", []) if a["level"] != "info"]
    if alerts:
        lines.append("Тревоги: " + "; ".join(f"[{a['level']}] {a['title']}" for a in alerts))
    cpu, mem, swap = m.get("cpu") or {}, m.get("memory") or {}, m.get("swap") or {}
    load = cpu.get("load") or [None]
    lines.append(f"Процессор {_n(cpu.get('percent'), 0)} % ({m.get('cpu_count')} потоков, нагрузка {_n(load[0], 2)}) · "
                 f"память {_gb(mem.get('used'))} из {_gb(mem.get('total'))} ({_n(mem.get('pct'), 0)} %)"
                 + (f" · подкачка {_n(swap.get('pct'), 0)} %" if swap.get("total") else ""))
    for g in m.get("gpus", []):
        free = (g.get("mem_total_mb") or 0) - (g.get("mem_used_mb") or 0)
        power = f", питание {_n(g.get('power_w'), 0)} Вт" if g.get("power_w") is not None else ""
        lines.append(f"Видеокарта {g.get('name')}: загрузка {_n(g.get('util'), 0)} %, видеопамять {_n(g.get('mem_used_mb'), 0)} из "
                     f"{_n(g.get('mem_total_mb'), 0)} МБ (свободно {free:.0f} МБ), {_n(g.get('temp_c'), 0)} °C{power}")
    if not m.get("gpus"):
        lines.append("Видеокарта не видна: " + (m.get("gpu_error") or "nvidia-smi не найден"))
    disks = m.get("disks") or []
    if disks:
        lines.append("Диски: " + " · ".join(f"{d['path']}{' (рабочая папка)' if d.get('workdir') else ''} свободно "
                                            f"{_gb(d['free'])} ({_n(d['free_pct'], 0)} %)" for d in disks))
    jobs = m.get("jobs") or {}
    lines.append(f"Задачи пульта: идёт {jobs.get('running', 0)}, в очереди {jobs.get('queued', 0)}")
    services = m.get("services") or []
    if services:
        lines.append("Службы: " + "; ".join(f"{s['name']} — {'ок' if s['ok'] else s.get('state') or 'нет ответа'}" for s in services))
    docker = m.get("docker")
    if docker:
        lines.append("Контейнеры: " + ", ".join(f"{c['name']} ({c['state']})" for c in docker[:12]))
    top = m.get("top_cpu") or []
    if top:
        lines.append("Больше всего процессора: " + ", ".join(f"{p['name']} {_n(p['cpu'])} %" for p in top[:3]))
    update = m.get("update") or {}
    lines.append(f"Пульт {m.get('version')}{' · ' + m['repo']['commit'] if (m.get('repo') or {}).get('commit') else ''}"
                 + (f" · обновление: {update.get('result')}" if update else ""))
    return "\n".join(lines)


def t_status(args):
    m = api("GET", "/api/metrics")
    if args.get("detail"):
        return json.dumps(m, ensure_ascii=False, indent=1)
    return summarize_metrics(m)


def t_tools(args):
    tools = api("GET", "/api/tools")
    if args.get("available_only", True):
        tools = [t for t in tools if t["available"]]
    lines = []
    for t in tools:
        params = ", ".join(
            f"{p['name']}:{p.get('type', 'string')}" + ("*" if p.get("required") else "")
            + (f"={p['default']}" if p.get("default") not in (None, "") else "")
            + (f" {p['choices']}" if p.get("choices") else "")
            for p in t["params"])
        state = "" if t["available"] else f"  [недоступен: {t['reason']}]"
        lines.append(f"- {t['id']} ({t['group']}): {t['title']}. {t['description']}\n  параметры: {params or 'нет'}{state}")
    return ("Параметры file — путь внутри рабочей папки пульта (inputs/… или jobs/<id>/out/…; голое имя — файл из inputs/); "
            "* — обязательный. device у инструментов с видеокартой: auto — видеокарта, при сбое процессор; gpu; cpu.\n"
            + "\n".join(lines))


def _job_text(job):
    files = "\n".join(f"  {f['path']} ({f['size']} байт)" for f in job.get("files", [])) or "  нет"
    parts = [f"Задача {job['id']} — {job['title']}: {job['state']}"]
    if job.get("error"):
        parts.append("Ошибка: " + job["error"])
    if job.get("returncode") is not None:
        parts.append(f"Код возврата: {job['returncode']}")
    if job.get("device") in ("gpu", "cpu"):
        fell_back = job["device"] == "cpu" and any(r.get("device") == "gpu" for r in job.get("runs") or [])
        parts.append("Считалось: " + ("на видеокарте" if job["device"] == "gpu" else "на процессоре")
                     + (" (видеокарта не справилась)" if fell_back else ""))
    parts.append("Файлы:\n" + files)
    if job.get("log"):
        parts.append("Хвост лога:\n" + job["log"][-3000:])
    return "\n".join(parts)


def t_run(args):
    job = api("POST", "/api/jobs", {"tool": args["tool"], "params": args.get("params") or {}})
    wait = min(float(args.get("wait_seconds", 120)), 3000)
    deadline = time.time() + wait
    while time.time() < deadline:
        job = api("GET", f"/api/jobs/{q(job['id'])}")
        if job["state"] not in ("queued", "running"):
            return _job_text(job)
        time.sleep(1.5)
    job = api("GET", f"/api/jobs/{q(job['id'])}")
    return _job_text(job) + "\n(задача ещё идёт — проверьте позже через hub_job)"


def t_job(args):
    if args.get("cancel"):
        api("POST", f"/api/jobs/{q(args['job_id'])}/cancel")
    return _job_text(api("GET", f"/api/jobs/{q(args['job_id'])}"))


def t_jobs(_args):
    jobs = api("GET", "/api/jobs")
    return "\n".join(f"{j['id']}  {j['state']:<9}  {j['title']}" for j in jobs[:30]) or "задач нет"


def t_files(args):
    files = api("GET", "/api/files?scope=" + ("all" if args.get("include_results", True) else "inputs"))
    return "\n".join(f"{f['path']}  ({f['size']} байт)" for f in files[:200]) or "файлов нет"


def t_upload(args):
    src = Path(os.path.expanduser(args["local_path"]))
    if not src.is_file():
        raise HubError(f"нет файла {src}")
    name = args.get("name") or src.name
    with open(src, "rb") as f:  # urllib streams a file object when Content-Length is given
        req = urllib.request.Request(HUB_URL + "/api/files/" + q(name), data=f, method="PUT", headers={
            "Authorization": "Bearer " + HUB_TOKEN, "Content-Length": str(src.stat().st_size),
            "Content-Type": "application/octet-stream"})
        try:
            with urllib.request.urlopen(req, timeout=3600) as resp:
                info = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            raise HubError(f"загрузка не удалась: {exc.code} {exc.reason}")
        except (urllib.error.URLError, OSError) as exc:
            raise HubError(f"пульт недоступен: {exc}")
    return f"Загружено: {info['path']} ({info['size']} байт). Используйте этот путь в параметрах file."


def t_download(args):
    rel = args["path"]
    dest_dir = Path(os.path.expanduser(args.get("dest_dir") or DOWNLOAD_DIR))
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / Path(rel).name
    req = urllib.request.Request(HUB_URL + "/api/download?path=" + q(rel),
                                 headers={"Authorization": "Bearer " + HUB_TOKEN})
    try:
        with urllib.request.urlopen(req, timeout=3600) as resp, open(dest, "wb") as out:
            while True:
                chunk = resp.read(1024 * 1024)
                if not chunk:
                    break
                out.write(chunk)
    except urllib.error.HTTPError as exc:
        raise HubError(f"скачивание не удалось: {exc.code} {exc.reason}")
    except (urllib.error.URLError, OSError) as exc:
        raise HubError(f"пульт недоступен: {exc}")
    return f"Сохранено: {dest} ({dest.stat().st_size} байт)"


def t_view(args):
    rel = args["path"]
    data, headers = request("GET", "/api/download?path=" + q(rel), timeout=300,
                            headers={"Range": f"bytes=0-{VIEW_LIMIT - 1}"})
    ctype = mimetypes.guess_type(rel)[0] or ""
    if ctype in ("image/png", "image/jpeg", "image/gif", "image/webp"):
        if len(data) >= VIEW_LIMIT:
            raise HubError("картинка больше 4 МБ — уменьшите её инструментом или скачайте")
        return [{"type": "image", "data": base64.b64encode(data).decode("ascii"), "mimeType": ctype},
                {"type": "text", "text": rel}]
    text = data.decode("utf-8", errors="replace")
    limit = int(args.get("max_chars", 20000))
    return text[:limit] + ("\n…(обрезано)" if len(text) > limit else "")


def t_catalog(args):
    cat = api("GET", "/api/catalog")
    query = (args.get("query") or "").lower()
    items = [i for i in cat["items"]
             if (not args.get("direction") or i["direction"] == args["direction"])
             and (not args.get("status") or i["status"] == args["status"])
             and (not query or query in (i["name"] + " " + i["summary"] + " " + i["install"]).lower())]
    out = []
    for i in items[: int(args.get("limit", 40))]:
        line = f"- {i['name']} [{i['direction']}, {i['status'] or 'без статуса'}] {i['summary']}"
        if i["url"]:
            line += f"\n  {i['url']}"
        if i["card"]:
            line += f"\n  карточка: {i['card']}"
        if i["install"]:
            line += "\n  установка: " + i["install"].replace("\n", " && ")[:400]
        out.append(line)
    return f"Найдено {len(items)} из {len(cat['items'])}\n" + "\n".join(out)


def t_resources(args):
    data = api("GET", "/api/resources")
    query = (args.get("query") or "").lower()
    items = [i for i in data.get("items", [])
             if (not args.get("category") or i.get("category") == args["category"])
             and (not args.get("ru_only") or i.get("ru_access") == "yes")
             and (not query or query in json.dumps(i, ensure_ascii=False).lower())]
    cats = data.get("categories", {})
    lines = ["Категории: " + ", ".join(f"{k} ({v})" for k, v in cats.items())]
    if not query:
        lines += [f"Лучшее — {cats.get(p['category'], p['category'])}: {p['text']}"
                  for p in data.get("picks", []) if not args.get("category") or p["category"] == args["category"]]
    for i in sorted(items, key=lambda i: i.get("skip", False))[: int(args.get("limit", 40))]:
        flags = [f"доступ из РФ: {i.get('ru_access', '?')}"]
        if i.get("commercial") is False:
            flags.append("только некоммерчески")
        if i.get("skip"):
            flags.append("НЕ ПОДХОДИТ")
        lines.append(f"- {i['name']} [{i.get('category')}; {'; '.join(flags)}] {i.get('free', '')} "
                     f"Лицензия: {i.get('license', '?')}. {i.get('notes', '')} {i.get('url', '')}")
    return "\n".join(lines)


def _schema(props=None, required=None):
    return {"type": "object", "properties": props or {}, "required": required or []}


TOOLS = [
    ("hub_status", "Живое состояние домашнего сервера одним абзацем: итог и тревоги, процессор, память, видеокарта "
     "(свободная видеопамять, температура), диски, службы и контейнеры, задачи. Смотреть перед тяжёлой задачей на видеокарте. "
     "detail=true — полный JSON.",
     _schema({"detail": {"type": "boolean", "default": False}}), t_status),
    ("hub_tools", "Список инструментов пульта (ffmpeg, замеры громкости, озвучка, Whisper, апскейл, картинки) с параметрами.",
     _schema({"available_only": {"type": "boolean", "default": True}}), t_tools),
    ("hub_run", "Запустить инструмент на сервере и подождать результат. params — объект {имя: значение}; файлы — пути из hub_files или hub_upload.",
     _schema({"tool": {"type": "string"}, "params": {"type": "object"},
              "wait_seconds": {"type": "number", "default": 120}}, ["tool"]), t_run),
    ("hub_job", "Статус задачи, хвост лога и файлы результата; cancel=true отменяет задачу.",
     _schema({"job_id": {"type": "string"}, "cancel": {"type": "boolean"}}, ["job_id"]), t_job),
    ("hub_jobs", "Последние задачи пульта.", _schema(), t_jobs),
    ("hub_files", "Файлы в рабочей папке сервера: загруженные (inputs/) и результаты задач (jobs/…/out/).",
     _schema({"include_results": {"type": "boolean", "default": True}}), t_files),
    ("hub_upload", "Загрузить локальный файл с этого компьютера на сервер (в inputs/).",
     _schema({"local_path": {"type": "string"}, "name": {"type": "string"}}, ["local_path"]), t_upload),
    ("hub_download", "Скачать файл с сервера на этот компьютер (по умолчанию в ~/Downloads/hub).",
     _schema({"path": {"type": "string"}, "dest_dir": {"type": "string"}}, ["path"]), t_download),
    ("hub_view", "Посмотреть файл с сервера: картинку (кадр, контактный лист) или текст (лог, субтитры, отчёт).",
     _schema({"path": {"type": "string"}, "max_chars": {"type": "integer", "default": 20000}}, ["path"]), t_view),
    ("hub_catalog", "Поиск по каталогу находок ClaudeRepo: навыки, плагины, MCP, репозитории со статусами и командами установки.",
     _schema({"query": {"type": "string"}, "direction": {"type": "string",
              "enum": ["video", "animation", "audio", "coding", "productivity", "business", "common"]},
              "status": {"type": "string"}, "limit": {"type": "integer", "default": 40}}), t_catalog),
    ("hub_resources", "Бесплатные ресурсы для контента: ИИ-генерация (картинки, видео, голос, музыка) и стоки с лицензиями и доступностью из России.",
     _schema({"query": {"type": "string"}, "category": {"type": "string"}, "ru_only": {"type": "boolean"},
              "limit": {"type": "integer", "default": 40}}), t_resources),
]
HANDLERS = {name: fn for name, _, _, fn in TOOLS}


# --- JSON-RPC loop -------------------------------------------------------------
def reply(msg_id, result=None, error=None):
    msg = {"jsonrpc": "2.0", "id": msg_id}
    if error:
        msg["error"] = error
    else:
        msg["result"] = result
    sys.stdout.write(json.dumps(msg, ensure_ascii=False) + "\n")
    sys.stdout.flush()


def handle(msg):
    method, msg_id, params = msg.get("method"), msg.get("id"), msg.get("params") or {}
    if msg_id is None:  # notification (initialized, cancelled…) — nothing to answer
        return
    if method == "initialize":
        reply(msg_id, {
            "protocolVersion": params.get("protocolVersion", PROTOCOL),
            "capabilities": {"tools": {}},
            "serverInfo": {"name": "home-hub", "version": "0.1.0"},
            "instructions": "Инструменты домашнего сервера. Файлы сначала загрузить hub_upload, "
                            "потом передать путь inputs/<имя> в hub_run; результат смотреть hub_view или скачать hub_download.",
        })
    elif method == "ping":
        reply(msg_id, {})
    elif method == "tools/list":
        reply(msg_id, {"tools": [{"name": n, "description": d, "inputSchema": s} for n, d, s, _ in TOOLS]})
    elif method == "tools/call":
        fn = HANDLERS.get(params.get("name"))
        if not fn:
            return reply(msg_id, error={"code": -32602, "message": "unknown tool"})
        try:
            out = fn(params.get("arguments") or {})
            content = out if isinstance(out, list) else [{"type": "text", "text": out}]
            reply(msg_id, {"content": content, "isError": False})
        except (HubError, KeyError, ValueError, TypeError) as exc:
            reply(msg_id, {"content": [{"type": "text", "text": f"Ошибка: {exc}"}], "isError": True})
    else:
        reply(msg_id, error={"code": -32601, "message": f"method not found: {method}"})


def main():
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except ValueError:
            reply(None, error={"code": -32700, "message": "parse error"})
            continue
        handle(msg)


if __name__ == "__main__":
    main()
