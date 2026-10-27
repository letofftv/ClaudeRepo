"""Tool registry: load whitelisted tools and turn validated params into argv.

A tool is a command template (a list of arguments, never a shell string).
Placeholders like {input} are replaced inside single arguments only, so a
parameter can never become extra arguments or shell syntax.
"""
import json
import re
import shutil
from pathlib import Path

SAFE_NAME = re.compile(r"[^A-Za-z0-9._-]+")
PLACEHOLDER = re.compile(r"{([A-Za-z_][A-Za-z0-9_]*)}")


class ParamError(ValueError):
    pass


def safe_filename(name):
    """Keep a plain file name: no directories, no leading dots or dashes."""
    base = Path(str(name)).name
    base = SAFE_NAME.sub("_", base).lstrip(".-_") or "file"
    return base[:120]


def load_tools(main_file, local_file=None):
    """Load the registry; a local file may add tools, override them or set vars."""
    with open(main_file, encoding="utf-8") as f:
        data = json.load(f)
    tools = {t["id"]: t for t in data.get("tools", [])}
    variables = dict(data.get("vars", {}))
    if local_file and Path(local_file).exists():
        with open(local_file, encoding="utf-8") as f:
            local = json.load(f)
        variables.update(local.get("vars", {}))
        for t in local.get("tools", []):
            base = tools.get(t["id"], {})
            merged = dict(base)
            merged.update(t)
            tools[t["id"]] = merged
        for tid in local.get("disable", []):
            tools.pop(tid, None)
    return list(tools.values()), variables


def tool_status(tool, variables):
    """Return (available, reason) — missing binaries or unset variables."""
    if tool.get("enabled") is False:
        return False, "выключен в настройках"
    missing = [b for b in tool.get("requires", []) if not shutil.which(b)]
    if missing:
        return False, "нет на сервере: " + ", ".join(missing)
    param_names = {p["name"] for p in tool.get("params", [])}
    builtins = {"repo", "out", "job", "python"}
    for arg in tool.get("command", []):
        for name in PLACEHOLDER.findall(arg):
            if name in param_names or name in builtins:
                continue
            if not variables.get(name):
                return False, "не задана переменная: " + name
    return True, ""


def public_tool(tool, variables):
    available, reason = tool_status(tool, variables)
    return {
        "id": tool["id"],
        "title": tool.get("title", tool["id"]),
        "group": tool.get("group", "other"),
        "description": tool.get("description", ""),
        "params": tool.get("params", []),
        "available": available,
        "reason": reason,
        "timeout": tool.get("timeout", 3600),
    }


def _validate_param(spec, value, workdir):
    ptype = spec.get("type", "string")
    name = spec["name"]
    if ptype == "number":
        try:
            num = float(value)
        except (TypeError, ValueError):
            raise ParamError(f"{name}: нужно число")
        if "min" in spec and num < spec["min"] or "max" in spec and num > spec["max"]:
            raise ParamError(f"{name}: вне диапазона {spec.get('min')}…{spec.get('max')}")
        return str(int(num)) if num == int(num) and spec.get("integer") else str(num)
    if ptype == "choice":
        if value not in spec.get("choices", []):
            raise ParamError(f"{name}: допустимо {spec.get('choices')}")
        return str(value)
    if ptype == "file":
        rel = str(value).strip().lstrip("/")
        if not rel or rel.startswith("-"):
            raise ParamError(f"{name}: укажите файл")
        root = Path(workdir).resolve()
        path = (root / rel).resolve()
        if root not in path.parents or not path.is_file():
            raise ParamError(f"{name}: файл не найден в рабочей папке")
        # paths placed inside an ffmpeg filter string must not carry filter syntax
        if spec.get("filter_safe") and not re.fullmatch(r"[A-Za-z0-9._/-]+", str(path)):
            raise ParamError(f"{name}: в пути допустимы только латиница, цифры и . _ - /")
        return str(path)
    if ptype == "text":
        text = str(value)
        if len(text) > spec.get("max_length", 20000):
            raise ParamError(f"{name}: слишком длинный текст")
        return text
    # string
    text = str(value)
    if text.startswith("-"):
        raise ParamError(f"{name}: значение не может начинаться с «-»")
    if len(text) > spec.get("max_length", 500):
        raise ParamError(f"{name}: слишком длинное значение")
    pattern = spec.get("pattern")
    if pattern and not re.fullmatch(pattern, text):
        raise ParamError(f"{name}: не подходит под шаблон {pattern}")
    return text


def build_argv(tool, params, variables, workdir, job_dir, repo_root, python_exe):
    """Validate params and build argv. Text params are written to files."""
    values = {}
    for spec in tool.get("params", []):
        name = spec["name"]
        raw = params.get(name, spec.get("default"))
        if raw is None or raw == "":
            if spec.get("required"):
                raise ParamError(f"{name}: обязательный параметр")
            raw = spec.get("default", "")
        if raw == "" and not spec.get("required"):
            values[name] = ""
            continue
        val = _validate_param(spec, raw, workdir)
        if spec.get("type") == "text":
            text_path = Path(job_dir) / f"{safe_filename(name)}.txt"
            text_path.write_text(val, encoding="utf-8")
            val = str(text_path)
        values[name] = val
    subst = dict(variables)
    subst.update(values)
    subst.update({
        "repo": str(repo_root),
        "out": str(Path(job_dir) / "out"),
        "job": str(job_dir),
        "python": python_exe,
    })
    argv = []
    for arg in tool["command"]:
        names = PLACEHOLDER.findall(arg)
        # an argument made only of an empty optional placeholder is dropped
        if names and all(subst.get(n, "") == "" for n in names) and PLACEHOLDER.sub("", arg) == "":
            continue
        argv.append(PLACEHOLDER.sub(lambda m: str(subst.get(m.group(1), "")), arg))
    return argv
