"""Tool registry: load whitelisted tools and turn validated params into argv.

A tool is a command template (a list of arguments, never a shell string).
Placeholders like {input} are replaced inside single arguments only, so a
parameter can never become extra arguments or shell syntax.

A tool may also carry a "gpu" block — a faster variant for the video card.
The job runner tries it first and falls back to the plain command (CPU) when
it fails; the "device" parameter (auto / gpu / cpu) is added automatically.
"""
import json
import os
import re
import shutil
from pathlib import Path

SAFE_NAME = re.compile(r"[^A-Za-z0-9._-]+")
PLACEHOLDER = re.compile(r"{([A-Za-z_][A-Za-z0-9_]*)}")
BUILTINS = ("repo", "out", "job", "python", "workdir")
DEVICE_PARAM = {
    "name": "device", "type": "choice", "label": "Где считать", "choices": ["auto", "gpu", "cpu"], "default": "auto",
    "labels": {"auto": "Видеокарта, при сбое — процессор", "gpu": "Только видеокарта", "cpu": "Только процессор"},
}


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
    for tool in tools.values():
        if tool.get("gpu") and not any(p.get("name") == "device" for p in tool.get("params", [])):
            tool["params"] = [*tool.get("params", []), dict(DEVICE_PARAM)]
    return list(tools.values()), variables


def tool_status(tool, variables):
    """Return (available, reason) — missing binaries or unset variables."""
    if tool.get("enabled") is False:
        return False, "выключен в настройках"
    missing = [b for b in tool.get("requires", []) if not shutil.which(b)]
    if missing:
        return False, "нет на сервере: " + ", ".join(missing)
    param_names = {p["name"] for p in tool.get("params", [])}
    for arg in [*tool.get("command", []), *(tool.get("gpu") or {}).get("command", [])]:
        for name in PLACEHOLDER.findall(arg):
            if name in param_names or name in BUILTINS:
                continue
            if not variables.get(name):
                return False, "не задана переменная: " + name
    return True, ""


def gpu_status(tool):
    """(available, reason) of the tool's GPU variant; (False, "") when it has none."""
    gpu = tool.get("gpu")
    if not gpu:
        return False, ""
    missing = [b for b in gpu.get("requires", ["nvidia-smi"]) if not shutil.which(b)]
    return (False, "нет на сервере: " + ", ".join(missing)) if missing else (True, "")


def public_tool(tool, variables):
    available, reason = tool_status(tool, variables)
    info = {
        "id": tool["id"],
        "title": tool.get("title", tool["id"]),
        "group": tool.get("group", "other"),
        "description": tool.get("description", ""),
        "params": tool.get("params", []),
        "available": available,
        "reason": reason,
        "timeout": tool.get("timeout", 3600),
    }
    if tool.get("gpu"):
        gpu_ok, gpu_reason = gpu_status(tool)
        info["gpu"] = {"available": gpu_ok, "reason": gpu_reason}
    return info


def _find_file(root, rel):
    """A path inside the work folder; a bare name means a file uploaded to inputs/."""
    if "/" in rel:
        return (root / rel).resolve()
    for name in dict.fromkeys([rel, safe_filename(rel)]):
        path = (root / "inputs" / name).resolve()
        if path.is_file():
            return path
    return (root / "inputs" / rel).resolve()


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
        path = _find_file(root, rel)
        if root not in path.parents or not path.is_file():
            hint = f"inputs/{rel}" if "/" not in rel else rel
            raise ParamError(f"{name}: файл не найден в рабочей папке ({hint})")
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


def _expand_vars(variables, builtins):
    """Variables may use ~ and built-ins: "{workdir}/models" is a valid value."""
    out = {}
    for key, value in variables.items():
        value = str(value)
        if value.startswith("~"):
            value = os.path.expanduser(value)
        out[key] = PLACEHOLDER.sub(lambda m: builtins.get(m.group(1), m.group(0)), value)
    return out


def _render(command, subst):
    argv = []
    for arg in command:
        names = PLACEHOLDER.findall(arg)
        # an argument made only of an empty optional placeholder is dropped
        if names and all(subst.get(n, "") == "" for n in names) and PLACEHOLDER.sub("", arg) == "":
            continue
        argv.append(PLACEHOLDER.sub(lambda m: str(subst.get(m.group(1), "")), arg))
    return argv


def _render_env(env, subst):
    return {str(k): PLACEHOLDER.sub(lambda m: str(subst.get(m.group(1), "")), str(v)) for k, v in (env or {}).items()}


def build_runs(tool, params, variables, workdir, job_dir, repo_root, python_exe):
    """Validate params and build the commands to try, in order.

    Returns [{"device", "argv", "env"}]: the GPU variant first when it exists,
    is available and allowed by the "device" param, then the plain command.
    Text params are written to files in the job folder.
    """
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
    builtins = {
        "repo": str(repo_root),
        "out": str(Path(job_dir) / "out"),
        "job": str(job_dir),
        "python": python_exe,
        "workdir": str(Path(workdir).resolve()),
    }
    subst = _expand_vars(variables, builtins)
    subst.update(values)
    subst.update(builtins)

    gpu = tool.get("gpu")
    if not gpu:
        return [{"device": "", "argv": _render(tool["command"], subst), "env": {}}]
    cpu = {"device": "cpu", "argv": _render(tool["command"], subst), "env": _render_env(gpu.get("cpu_env"), subst)}
    device = values.get("device") or "auto"
    if device == "cpu":
        return [cpu]
    ok, reason = gpu_status(tool)
    if not ok:
        if device == "gpu":
            raise ParamError("видеокарта недоступна: " + reason)
        return [cpu]
    run = {"device": "gpu", "argv": _render(gpu.get("command", tool["command"]), subst),
           "env": _render_env(gpu.get("env"), subst)}
    return [run] if device == "gpu" else [run, cpu]


def build_argv(tool, params, variables, workdir, job_dir, repo_root, python_exe):
    """The plain (CPU) command for these params."""
    return build_runs(tool, params, variables, workdir, job_dir, repo_root, python_exe)[-1]["argv"]
