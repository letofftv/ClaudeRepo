#!/usr/bin/env python3
"""Design tokens from a small JSON spec: light and dark themes with checked contrast.

    python3 tokens.py spec.json --out tokens.css          # write CSS, print the contrast report
    python3 tokens.py spec.json --json resolved.json      # also dump every resolved color
    python3 tokens.py --example > spec.json               # starter spec

Colors are built in OKLCH (perceptual lightness), mapped into the sRGB gamut
and tuned until every text/background pair passes WCAG 2: body text >= 4.5:1,
large text and UI marks >= 3:1. Status and chart colors default to a validated
palette (the dataviz method's reference instance); status colors are for dots,
icons and fills — their readable text variants are generated separately.
Standard library only. Exit code 1 if a contrast check fails.
"""
import argparse
import json
import math
import sys

EXAMPLE = {
    "name": "Мой интерфейс",
    "accent_hue": 255,
    "accent_chroma": 0.16,
    "neutral_hue": 85,
    "neutral_chroma": 0.006,
    "radius": 10,
    "density": "comfortable",
}
SERIES_LIGHT = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6", "#e34948"]
SERIES_DARK = ["#3987e5", "#d95926", "#199e70", "#c98500", "#d55181", "#008300", "#9085e9", "#e66767"]
STATUS = {"ok": "#0ca30c", "warn": "#fab219", "serious": "#ec835a", "bad": "#d03b3b"}
FONT = 'system-ui, -apple-system, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif'
MONO = 'ui-monospace, SFMono-Regular, Menlo, Consolas, "Liberation Mono", monospace'


# --- color math (OKLab by Björn Ottosson, WCAG 2 relative luminance) -------------------
def oklch_to_linear(L, C, h):
    a, b = C * math.cos(math.radians(h)), C * math.sin(math.radians(h))
    l_ = L + 0.3963377774 * a + 0.2158037573 * b
    m_ = L - 0.1055613458 * a - 0.0638541728 * b
    s_ = L - 0.0894841775 * a - 1.2914855480 * b
    l, m, s = l_ ** 3, m_ ** 3, s_ ** 3
    return (4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s,
            -1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s,
            -0.0041960863 * l - 0.7034186147 * m + 1.7076147010 * s)


def in_gamut(rgb, eps=1e-4):
    return all(-eps <= c <= 1 + eps for c in rgb)


def encode(c):
    c = min(1.0, max(0.0, c))
    return 12.92 * c if c <= 0.0031308 else 1.055 * c ** (1 / 2.4) - 0.055


def oklch(L, C, h):
    """OKLCH -> hex, lowering chroma until the color fits sRGB."""
    rgb = oklch_to_linear(L, C, h)
    if not in_gamut(rgb):
        lo, hi = 0.0, C
        for _ in range(24):
            mid = (lo + hi) / 2
            if in_gamut(oklch_to_linear(L, mid, h)):
                lo = mid
            else:
                hi = mid
        rgb = oklch_to_linear(L, lo, h)
    return "#" + "".join(f"{round(encode(c) * 255):02x}" for c in rgb)


def hex_to_linear(hx):
    hx = hx.lstrip("#")
    out = []
    for i in (0, 2, 4):
        c = int(hx[i:i + 2], 16) / 255
        out.append(c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4)
    return out


def hex_to_oklch(hx):
    r, g, b = hex_to_linear(hx)
    l = 0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b
    m = 0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b
    s = 0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b
    l_, m_, s_ = (math.copysign(abs(v) ** (1 / 3), v) for v in (l, m, s))
    L = 0.2104542553 * l_ + 0.7936177850 * m_ - 0.0040720468 * s_
    a = 1.9779984951 * l_ - 2.4285922050 * m_ + 0.4505937099 * s_
    bb = 0.0259040371 * l_ + 0.7827717662 * m_ - 0.8086757660 * s_
    return L, math.hypot(a, bb), math.degrees(math.atan2(bb, a)) % 360


def luminance(hx):
    r, g, b = hex_to_linear(hx)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(a, b):
    la, lb = sorted((luminance(a), luminance(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def fit_lightness(start, C, h, against, need, direction):
    """Move L from `start` (direction -1 darker, +1 lighter) until contrast >= need on all backgrounds."""
    L = start
    for _ in range(200):
        hx = oklch(L, C, h)
        if all(contrast(hx, bg) >= need for bg in against):
            return hx, L
        L += 0.005 * direction
        if not 0 <= L <= 1:
            break
    return oklch(min(1, max(0, L)), C, h), L


# --- theme construction -----------------------------------------------------------------
def add_status_soft(t, spec, mode):
    """Soft status backgrounds (alerts, badges) — needed before text colors are fitted."""
    for key, hx in dict(STATUS, **(spec.get("status") or {})).items():
        _, C, h = hex_to_oklch(hx)
        t[f"{key}-soft"] = oklch(0.95, min(C, 0.05), h) if mode == "light" else oklch(0.27, min(C, 0.06), h)


def build_theme(spec, mode):
    nh, nc = spec.get("neutral_hue", 85), spec.get("neutral_chroma", 0.006)
    ah, ac = spec.get("accent_hue", 255), spec.get("accent_chroma", 0.16)
    t = {}
    if mode == "light":
        plan = {"bg": 0.975, "surface": 0.997, "surface-2": 0.955, "surface-3": 0.925,
                "border": 0.885, "border-strong": 0.80, "grid": 0.915, "axis": 0.82}
        for k, L in plan.items():
            t[k] = oklch(L, nc, nh)
        t["accent-soft"] = oklch(0.95, min(ac, 0.035), ah)
        add_status_soft(t, spec, mode)
        backs = [t[k] for k in ("surface", "bg", "surface-2", "accent-soft", "ok-soft", "warn-soft", "serious-soft", "bad-soft")]
        t["text"] = oklch(0.21, nc, nh)
        t["text-2"], _ = fit_lightness(0.45, nc, nh, backs, 7.0, -1)
        t["muted"], _ = fit_lightness(0.56, nc, nh, backs, 4.6, -1)
        t["accent-text"] = "#ffffff"
        t["accent"], acc_L = fit_lightness(0.58, ac, ah, [t["surface"], t["bg"], t["accent-text"]], 4.5, -1)
        t["accent-hover"] = oklch(acc_L - 0.05, ac, ah)
        t["focus"] = oklch(min(0.65, acc_L + 0.08), ac, ah)
        t["shadow"] = "0 1px 2px rgba(20, 20, 18, 0.06), 0 6px 20px rgba(20, 20, 18, 0.07)"
        t["overlay"] = "rgba(20, 20, 18, 0.45)"
    else:
        plan = {"bg": 0.155, "surface": 0.195, "surface-2": 0.235, "surface-3": 0.28,
                "border": 0.30, "border-strong": 0.40, "grid": 0.265, "axis": 0.36}
        for k, L in plan.items():
            t[k] = oklch(L, nc, nh)
        t["accent-soft"] = oklch(0.30, min(ac, 0.06), ah)
        add_status_soft(t, spec, mode)
        backs = [t[k] for k in ("surface", "bg", "surface-2", "accent-soft", "ok-soft", "warn-soft", "serious-soft", "bad-soft")]
        t["text"] = oklch(0.95, nc, nh)
        t["text-2"], _ = fit_lightness(0.80, nc, nh, backs, 7.0, +1)
        t["muted"], _ = fit_lightness(0.66, nc, nh, backs, 4.6, +1)
        t["accent-text"] = oklch(0.18, nc, nh)
        t["accent"], acc_L = fit_lightness(0.70, ac, ah, [t["surface"], t["bg"], t["accent-text"]], 4.5, +1)
        t["accent-hover"] = oklch(min(0.92, acc_L + 0.05), ac, ah)
        t["focus"] = oklch(min(0.85, acc_L + 0.05), ac, ah)
        t["shadow"] = "0 1px 2px rgba(0, 0, 0, 0.4)"
        t["overlay"] = "rgba(0, 0, 0, 0.6)"
    # status: the fixed dots/fills + readable text on surfaces and on its own soft background
    for key, hx in dict(STATUS, **(spec.get("status") or {})).items():
        _, C, h = hex_to_oklch(hx)
        t[key] = hx
        backs = [t["surface"], t["surface-2"], t[f"{key}-soft"]]
        if mode == "light":
            t[f"{key}-text"], _ = fit_lightness(0.50, min(C, 0.16), h, backs, 4.5, -1)
        else:
            t[f"{key}-text"], _ = fit_lightness(0.74, min(C, 0.14), h, backs, 4.5, +1)
    series = spec.get("series" if mode == "light" else "series_dark") or (
        SERIES_LIGHT if mode == "light" else SERIES_DARK)
    for i, hx in enumerate(series, 1):
        t[f"series-{i}"] = hx
    return t


def checks(t, mode):
    """(label, ratio, need) for every pair the UI relies on."""
    pairs = [
        ("текст на поверхности", "text", "surface", 4.5), ("текст на фоне", "text", "bg", 4.5),
        ("вторичный текст на поверхности", "text-2", "surface", 4.5),
        ("приглушённый текст на поверхности", "muted", "surface", 4.5),
        ("приглушённый текст на фоне", "muted", "bg", 4.5),
        ("приглушённый текст на surface-2", "muted", "surface-2", 4.5),
        ("приглушённый текст на мягком акценте", "muted", "accent-soft", 4.5),
        ("текст на акценте (кнопка)", "accent-text", "accent", 4.5),
        ("акцент как ссылка", "accent", "surface", 4.5),
        ("текст на мягком акценте", "text", "accent-soft", 4.5),
        ("рамка поля ввода", "border-strong", "surface", 1.5),
        ("фокус-рамка", "focus", "surface", 3.0),
    ]
    for key in STATUS:
        pairs.append((f"текст статуса {key}", f"{key}-text", "surface", 4.5))
        pairs.append((f"текст на мягком фоне {key}", "text", f"{key}-soft", 4.5))
        pairs.append((f"приглушённый на мягком фоне {key}", "muted", f"{key}-soft", 4.5))
        pairs.append((f"текст статуса {key} на своём фоне", f"{key}-text", f"{key}-soft", 4.5))
    out = [(label, contrast(t[a], t[b]), need, False) for label, a, b, need in pairs]
    for i in range(1, 9):
        key = f"series-{i}"
        if key in t:  # chart marks below 3:1 are legal only with direct labels or a table view
            out.append((f"серия {i} на поверхности (метка графика)", contrast(t[key], t["surface"]), 3.0, True))
    return out


def scale_tokens(spec):
    r = float(spec.get("radius", 10))
    compact = spec.get("density") == "compact"
    return {
        "font": spec.get("font_family") or FONT, "mono": MONO,
        "fs-1": "12px", "fs-2": "13px", "fs-3": "14px" if compact else "15px", "fs-4": "17px",
        "fs-5": "20px", "fs-6": "24px", "fs-7": "32px", "fs-hero": "48px",
        "lh": "1.45", "lh-tight": "1.2",
        **{f"s-{i}": f"{v}px" for i, v in enumerate([4, 8, 12, 16, 20, 24, 32, 40, 56], 1)},
        "r-1": f"{max(2, round(r * 0.5))}px", "r-2": f"{round(r)}px", "r-3": f"{round(r * 1.6)}px",
        "r-full": "999px", "tap": "44px", "row": "40px" if compact else "48px",
        "header-h": "56px", "bottom-h": "64px", "sidebar-w": "232px", "content-max": "1240px",
        "dur-1": "120ms", "dur-2": "200ms", "ease": "cubic-bezier(.2, .7, .2, 1)",
    }


def css_block(selector, tokens, scheme=None, indent="  "):
    lines = [f"{selector} {{"]
    if scheme:
        lines.append(f"{indent}color-scheme: {scheme};")
    lines += [f"{indent}--{k}: {v};" for k, v in tokens.items()]
    lines.append("}")
    return "\n".join(lines)


def render_css(spec, light, dark):
    head = (f"/* Design tokens: {spec.get('name', 'ui')} — generated by ui-studio/scripts/tokens.py.\n"
            "   Edit the JSON spec and regenerate instead of editing this file. */")
    dark_media = css_block(':root:where(:not([data-theme="light"]))', dark, "dark").replace("\n", "\n  ")
    return "\n\n".join([
        head,
        css_block(":root", {**scale_tokens(spec), **light}, "light"),
        "@media (prefers-color-scheme: dark) {\n  " + dark_media + "\n}",
        css_block(':root[data-theme="dark"]', dark, "dark"),
    ]) + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("spec", nargs="?")
    ap.add_argument("--out", help="CSS file to write (default: print to stdout)")
    ap.add_argument("--json", help="also write resolved colors as JSON")
    ap.add_argument("--example", action="store_true", help="print a starter spec")
    ap.add_argument("--quiet", action="store_true", help="only print failures")
    args = ap.parse_args(argv)
    if args.example:
        print(json.dumps(EXAMPLE, ensure_ascii=False, indent=2))
        return 0
    if not args.spec:
        ap.error("нужен файл спецификации (или --example)")
    with open(args.spec, encoding="utf-8") as f:
        spec = json.load(f)
    light, dark = build_theme(spec, "light"), build_theme(spec, "dark")
    css = render_css(spec, light, dark)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(css)
    else:
        sys.stdout.write(css)
    if args.json:
        with open(args.json, "w", encoding="utf-8") as f:
            json.dump({"light": light, "dark": dark}, f, ensure_ascii=False, indent=2)
    failed = warned = 0
    report = sys.stderr if not args.out else sys.stdout
    for mode, theme in (("светлая", light), ("тёмная", dark)):
        rows = checks(theme, mode)
        failed += sum(1 for r in rows if r[1] < r[2] and not r[3])
        warned += sum(1 for r in rows if r[1] < r[2] and r[3])
        if not args.quiet:
            print(f"\n{mode} тема:", file=report)
        for label, ratio, need, soft in rows:
            if ratio < need or not args.quiet:
                mark = "ok  " if ratio >= need else ("WARN" if soft else "FAIL")
                print(f"  {mark} {label:42} {ratio:5.2f}:1 (нужно {need}:1)", file=report)
    if warned:
        print(f"\nWARN: {warned} цвет(а) графиков ниже 3:1 — у таких серий обязательны подписи значений "
              "или таблица (правило «relief» из метода dataviz).", file=report)
    if failed:
        print(f"\nКонтраст не прошёл в {failed} парах — поправьте спецификацию.", file=report)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
