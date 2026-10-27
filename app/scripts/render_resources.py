#!/usr/bin/env python3
"""Render app/data/free-resources.json into common/free-resources.md.

The JSON is the single source (the hub UI and the MCP bridge read it);
the Markdown page is for reading on GitHub. Run after editing the JSON:

    python3 app/scripts/render_resources.py
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "app" / "data" / "free-resources.json"
DEST = ROOT / "common" / "free-resources.md"
RU = {"yes": "да", "vpn": "VPN", "no": "нет", "unknown": "?"}
KIND = {"local": "локально", "service": "сервис", "stock": "сток"}


def cell(text):
    return str(text or "").replace("|", "\\|").replace("\n", " ").strip()


def render(data):
    cats = data["categories"]
    items = data["items"]
    out = [
        "# Бесплатные ресурсы для контента",
        "",
        f"Сгенерировано из [`app/data/free-resources.json`](../app/data/free-resources.json) "
        f"({data['updated']}) скриптом `app/scripts/render_resources.py` — правки вносить в JSON. "
        "Тот же список — во вкладке «Ресурсы» пульта и в MCP-инструменте `hub_resources`.",
        "",
        data["note"],
        "",
        "Колонка «Из России»: **да** — есть подтверждение, что работает без VPN; **VPN** — сервис сам "
        "закрыл доступ или его блокируют; **нет** — официально недоступно; **?** — сообщений о "
        "блокировке не найдено, но и подтверждения нет. «НК» — бесплатный уровень только для "
        "некоммерческого использования (пересмотреть, если ролики начнут монетизироваться).",
        "",
        "## Лучшее по категориям",
        "",
    ]
    for pick in data.get("picks", []):
        out.append(f"- **{cats[pick['category']]}.** {pick['text']}")
    out.append("")
    for key, title in cats.items():
        group = [i for i in items if i["category"] == key]
        if not group:
            continue
        out += [f"## {title}", "", "| Ресурс | Бесплатно и лицензия | Из России | Заметки |", "|---|---|---|---|"]
        for i in sorted(group, key=lambda i: (i.get("skip", False), i["name"].lower())):
            terms = "; ".join(t for t in (i.get("free"), i.get("license")) if t)
            if i.get("attribution") and i["attribution"] not in terms:
                terms += f"; указание автора: {i['attribution']}"
            flags = [KIND.get(i.get("kind"), "")]
            if i.get("commercial") is False:
                flags.append("НК")
            if i.get("skip"):
                flags.append("не подходит")
            name = f"[{cell(i['name'])}]({i['url']})"
            out.append(f"| {name} ({', '.join(f for f in flags if f)}) | {cell(terms)} | "
                       f"{RU.get(i.get('ru_access'), '?')} | {cell(i.get('notes'))} |")
        out.append("")
    out += ["## Источники", "",
            "У каждой записи в JSON есть поле `source` со ссылками и пометкой, как проверено: "
            "[page] — страница прочитана, [search] — по выдаче поиска, [memory] — по памяти модели. "
            "Перед тем как опираться на цифру лимита, проверить её в самом сервисе.", ""]
    return "\n".join(out)


def main():
    data = json.loads(SRC.read_text(encoding="utf-8"))
    DEST.write_text(render(data), encoding="utf-8")
    print(f"{DEST.relative_to(ROOT)}: {len(data['items'])} ресурсов")
    return 0


if __name__ == "__main__":
    sys.exit(main())
