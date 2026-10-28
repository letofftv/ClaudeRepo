#!/usr/bin/env python3
"""Start or update a no-build web UI on the ui-studio kit.

    python3 scaffold.py new ./my-panel --title "Моя панель"      # new project: shell, router, tokens
    python3 scaffold.py sync ./my-panel/kit                       # refresh kit files in a project
    python3 scaffold.py check ./my-panel/kit                      # exit 1 if the copy drifted from the kit

The kit is copied (vendored), not linked: a project keeps working on its own
and updates only when you run `sync`. tokens.css is per project — generate it
from the project's tokens.json with tokens.py, sync never touches it.
"""
import argparse
import filecmp
import json
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
KIT = HERE.parent / "kit"
KIT_FILES = ["base.css", "components.css", "ui.js", "charts.js", "icons.svg", "icons.LICENSE",
             "vendor/uplot/uPlot.iife.min.js", "vendor/uplot/uPlot.min.css", "vendor/uplot/LICENSE",
             "vendor/uplot/VERSION", "VERSION"]

INDEX = """<!doctype html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>{title}</title>
<link rel="stylesheet" href="tokens.css">
<link rel="stylesheet" href="kit/base.css">
<link rel="stylesheet" href="kit/components.css">
<link rel="stylesheet" href="kit/vendor/uplot/uPlot.min.css">
<link rel="stylesheet" href="app.css">
<script src="kit/vendor/uplot/uPlot.iife.min.js" defer></script>
<script type="module" src="app.js"></script>
</head>
<body>
<div class="app">
  <nav class="app-nav" aria-label="Разделы" id="nav"></nav>
  <div class="app-body">
    <header class="app-header"><h1 id="page-title">{title}</h1><span class="spacer"></span><span id="header-extra"></span></header>
    <main class="app-main" id="main" tabindex="-1"></main>
  </div>
</div>
</body>
</html>
"""

APP_JS = """// {title}: app shell on the ui-studio kit. Pages are functions that fill #main.
import {{ $, el, icon, mount, createRouter, initTheme, fmt }} from "./kit/ui.js";
import {{ sparkline }} from "./kit/charts.js";

initTheme();

const PAGES = [
  {{ path: "/", title: "Обзор", icon: "house", render: overview }},
  {{ path: "/settings", title: "Настройки", icon: "settings", render: settings }},
];

function overview() {{
  const values = Array.from({{ length: 30 }}, (_, i) => 40 + 20 * Math.sin(i / 4));
  return [
    el("div", {{ class: "page-head" }}, el("h2", {{}}, "Обзор"), el("span", {{ class: "meta" }}, "обновлено ", fmt.ago(Date.now() / 1000))),
    el("div", {{ class: "grid-auto-sm" }},
      el("div", {{ class: "tile" }}, el("div", {{ class: "tile-label" }}, icon("activity", {{ cls: "sm" }}), "Показатель"),
        el("div", {{ class: "tile-value" }}, "42", el("small", {{}}, "%")), el("div", {{ class: "tile-sub" }}, "за 15 минут"),
        el("div", {{ class: "tile-spark" }}, sparkline(values, {{ max: 100 }})))),
  ];
}}

function settings() {{
  return [el("div", {{ class: "page-head" }}, el("h2", {{}}, "Настройки")),
    el("div", {{ class: "card" }}, el("p", {{ class: "secondary" }}, "Здесь будут настройки."))];
}}

function renderNav(current) {{
  mount($("#nav"), el("div", {{ class: "app-brand" }}, "{title}"),
    PAGES.map((p) => el("a", {{ class: "nav-item", href: "#" + p.path, "aria-current": p.path === current ? "page" : null }},
      icon(p.icon), el("span", {{}}, p.title))));
}}

const router = createRouter(PAGES.map((p) => [p.path, () => {{
  renderNav(p.path);
  $("#page-title").textContent = p.title;
  document.title = `${{p.title}} · {title}`;
  mount($("#main"), p.render());
  $("#main").focus({{ preventScroll: true }});
}}]));
router.run();
"""

APP_CSS = """/* Project styles. Prefer kit classes and tokens; add only what is specific here. */
"""


def copy_kit(dest):
    dest = Path(dest)
    for rel in KIT_FILES:
        src = KIT / rel
        target = dest / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, target)
    return dest


def drift(dest):
    dest = Path(dest)
    changed = []
    for rel in KIT_FILES:
        target = dest / rel
        if not target.exists() or not filecmp.cmp(KIT / rel, target, shallow=False):
            changed.append(rel)
    return changed


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p_new = sub.add_parser("new", help="создать проект")
    p_new.add_argument("dir")
    p_new.add_argument("--title", default="Новый интерфейс")
    p_new.add_argument("--tokens", help="спецификация токенов (по умолчанию templates/tokens.json)")
    p_sync = sub.add_parser("sync", help="обновить копию набора")
    p_sync.add_argument("kit_dir")
    p_check = sub.add_parser("check", help="сравнить копию набора с оригиналом")
    p_check.add_argument("kit_dir")
    args = ap.parse_args(argv)

    if args.cmd == "new":
        root = Path(args.dir)
        if root.exists() and any(root.iterdir()):
            print(f"{root} не пустая — выберите другую папку", file=sys.stderr)
            return 1
        root.mkdir(parents=True, exist_ok=True)
        copy_kit(root / "kit")
        spec = json.loads(Path(args.tokens or HERE.parent / "templates" / "tokens.json").read_text(encoding="utf-8"))
        spec["name"] = args.title
        (root / "tokens.json").write_text(json.dumps(spec, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        subprocess.run([sys.executable, str(HERE / "tokens.py"), str(root / "tokens.json"), "--out",
                        str(root / "tokens.css"), "--quiet"], check=False)
        (root / "index.html").write_text(INDEX.format(title=args.title), encoding="utf-8")
        (root / "app.js").write_text(APP_JS.format(title=args.title.replace('"', "'")), encoding="utf-8")
        (root / "app.css").write_text(APP_CSS, encoding="utf-8")
        print(f"Готово: {root}. Открыть: python3 -m http.server -d {root} 8000 → http://127.0.0.1:8000/")
        return 0
    if args.cmd == "sync":
        dest = copy_kit(args.kit_dir)
        print(f"Набор обновлён: {dest} ({(KIT / 'VERSION').read_text(encoding='utf-8').strip()})")
        return 0
    changed = drift(args.kit_dir)
    if changed:
        print("Копия набора отличается: " + ", ".join(changed) + " — запустите scaffold.py sync", file=sys.stderr)
        return 1
    print("Копия набора совпадает с оригиналом")
    return 0


if __name__ == "__main__":
    sys.exit(main())
