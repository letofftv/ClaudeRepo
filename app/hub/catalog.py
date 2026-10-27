"""Catalog of finds parsed from the repository's markdown.

Sources: cards in <direction>/finds/*.md and table rows with links in
<direction>/README.md. Run as a script to print the catalog as JSON.
"""
import json
import re
import sys
from pathlib import Path

DIRECTIONS = {
    "video": "Видеомонтаж",
    "animation": "Анимация и мультипликация",
    "audio": "Аудио и мастеринг",
    "coding": "Программирование и вайбкодинг",
    "productivity": "Организация работы",
    "business": "Цифровизация бизнеса",
    "common": "Общее",
}
STATUSES = ["взять", "попробовать", "позже", "отклонено", "источник", "не нужно"]
LINK = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
FIELD = re.compile(r"^- \*\*([^*]+):\*\*\s*(.*)$")


def norm_status(text):
    low = text.lower()
    for s in STATUSES:
        if s in low:
            return s
    return ""


def _clean(text):
    text = LINK.sub(r"\1", text)
    return re.sub(r"[*`]", "", text).strip()


def parse_card(path, repo_root):
    lines = path.read_text(encoding="utf-8").splitlines()
    title = next((l[2:].strip() for l in lines if l.startswith("# ")), path.stem)
    fields = {}
    for line in lines:
        m = FIELD.match(line)
        if m:
            fields[m.group(1).strip().lower()] = m.group(2).strip()
    link = fields.get("ссылка") or fields.get("ссылки") or ""
    url_match = re.search(r"https?://[^\s,)·]+", link)
    install = ""
    text = "\n".join(lines)
    sec = re.search(r"## Как подключить\s*\n(.*?)(\n## |\Z)", text, re.S)
    if sec:
        code = re.search(r"```[a-z]*\n(.*?)```", sec.group(1), re.S)
        install = code.group(1).strip() if code else _clean(sec.group(1).strip().split("\n\n")[0])
    return {
        "name": _clean(title),
        "url": url_match.group(0) if url_match else "",
        "summary": _clean(fields.get("что это", "")),
        "status": norm_status(fields.get("статус", "")),
        "status_text": _clean(fields.get("статус", "")),
        "found": _clean(fields.get("найдено", "")),
        "card": str(path.relative_to(repo_root)),
        "install": install,
        "source": "card",
    }


def parse_index_rows(path, repo_root):
    """Table rows that carry a link — cards and external repos alike."""
    items = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.startswith("|") or line.startswith("|---") or "---|" in line:
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        links = [m for c in cells for m in LINK.finditer(c)]
        if not links:
            continue
        status_cell = next((c for c in cells if norm_status(c)), "")
        name, target = links[0].group(1), links[0].group(2)
        others = [c for c in cells if c and c != status_cell and not c.strip("# ").isdigit()
                  and LINK.search(c) is None]
        summary = max(others, key=len) if others else ""
        item = {"name": _clean(name), "summary": _clean(summary), "status": norm_status(status_cell),
                "status_text": _clean(status_cell), "source": "index", "url": "", "card": "", "install": ""}
        if target.startswith("http"):
            item["url"] = target
        else:
            card = (path.parent / target).resolve()
            if card.exists():
                item["card"] = str(card.relative_to(repo_root))
        items.append(item)
    return items


def build_catalog(repo_root):
    repo_root = Path(repo_root).resolve()
    items, seen = [], {}
    for key, title in DIRECTIONS.items():
        base = repo_root / key
        if not base.exists():
            continue
        for card in sorted((base / "finds").glob("*.md")):
            item = parse_card(card, repo_root)
            item["direction"] = key
            seen[item["card"]] = item
            items.append(item)
        readme = base / "README.md"
        if readme.exists():
            for row in parse_index_rows(readme, repo_root):
                if row["card"] and row["card"] in seen:
                    existing = seen[row["card"]]
                    if not existing["status"] and row["status"]:
                        existing["status"] = row["status"]
                    continue
                if row["card"]:
                    continue  # card from another direction, already listed there
                dedup = row["url"] or row["name"]
                if any((i["url"] or i["name"]) == dedup and i["direction"] == key for i in items):
                    continue
                row["direction"] = key
                items.append(row)
    for item in items:
        item["direction_title"] = DIRECTIONS[item["direction"]]
    packs = []
    market = repo_root / ".claude-plugin" / "marketplace.json"
    if market.exists():
        data = json.loads(market.read_text(encoding="utf-8"))
        for p in data.get("plugins", []):
            packs.append({"name": p["name"], "description": p.get("description", ""),
                          "source": p.get("source", ""),
                          "install": f"claude plugin marketplace add letofftv/ClaudeRepo\n"
                                     f"claude plugin install {p['name']}@{data.get('name', '')}"})
    return {"directions": DIRECTIONS, "statuses": STATUSES, "items": items, "packs": packs}


if __name__ == "__main__":
    root = sys.argv[1] if len(sys.argv) > 1 else Path(__file__).resolve().parents[2]
    print(json.dumps(build_catalog(root), ensure_ascii=False, indent=2))
