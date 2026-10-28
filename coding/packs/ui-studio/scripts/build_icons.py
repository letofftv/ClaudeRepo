#!/usr/bin/env python3
"""Build an SVG sprite from Lucide icons (lucide-static package).

    npm pack lucide-static && tar -xzf lucide-static-*.tgz      # gives ./package
    python3 build_icons.py --from package --out ../kit/icons.svg house server cpu ...
    python3 build_icons.py --from package --out ../kit/icons.svg --add gpu    # keep existing, add more

Each icon becomes <symbol id="NAME">; use it as
<svg class="icon"><use href="kit/icons.svg#NAME"></use></svg>. Stroke, fill and
width come from CSS (.icon in components.css), so icons follow currentColor.
Lucide is ISC-licensed: the license text goes next to the sprite.
"""
import argparse
import re
import shutil
import sys
from pathlib import Path

INNER = re.compile(r"<svg[^>]*>(.*)</svg>", re.S)


def read_symbols(sprite):
    if not sprite.exists():
        return {}
    text = sprite.read_text(encoding="utf-8")
    return dict(re.findall(r'<symbol id="([^"]+)" viewBox="0 0 24 24">(.*?)</symbol>', text, re.S))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("names", nargs="*", help="Lucide icon names (file names without .svg)")
    ap.add_argument("--from", dest="source", required=True, help="unpacked lucide-static package folder")
    ap.add_argument("--out", required=True, help="sprite file to write")
    ap.add_argument("--add", nargs="*", default=[], help="names to add while keeping existing symbols")
    args = ap.parse_args(argv)

    icons_dir = Path(args.source) / "icons"
    out = Path(args.out)
    symbols = read_symbols(out) if args.add else {}
    missing = []
    for name in [*args.names, *args.add]:
        svg = icons_dir / f"{name}.svg"
        if not svg.exists():
            missing.append(name)
            continue
        inner = INNER.search(svg.read_text(encoding="utf-8")).group(1)
        symbols[name] = " ".join(line.strip() for line in inner.strip().splitlines())
    if missing:
        print("нет таких иконок: " + ", ".join(missing), file=sys.stderr)
    body = "\n".join(f'  <symbol id="{n}" viewBox="0 0 24 24">{symbols[n]}</symbol>' for n in sorted(symbols))
    out.write_text('<svg xmlns="http://www.w3.org/2000/svg">\n'
                   "  <!-- Lucide icons (ISC), see icons.LICENSE -->\n" + body + "\n</svg>\n", encoding="utf-8")
    license_src = Path(args.source) / "LICENSE"
    if license_src.exists():
        shutil.copy(license_src, out.with_name("icons.LICENSE"))
    print(f"{out}: {len(symbols)} иконок")
    return 1 if missing else 0


if __name__ == "__main__":
    sys.exit(main())
