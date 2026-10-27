#!/usr/bin/env python3
"""Compare a mix against a reference track: loudness, tonal balance, stereo width.

Usage:
  mix_compare.py MIX REFERENCE [--json]

Tonal balance: each file is split into 6 bands and each band's RMS is taken
relative to the file's own full-band RMS, so the comparison is level-independent
(like level-matched A/B). Differences of more than ~2 dB in a band are hints for
EQ, not commands. Stereo: side-to-mid level ratio (lower = narrower, more mono).
Requires ffmpeg on PATH. No Python packages needed.
"""
import argparse
import json
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from loudness_report import measure  # noqa: E402

BANDS = [
    ("саб 20–60 Гц", 20, 60),
    ("низ 60–200 Гц", 60, 200),
    ("низкая середина 200–800 Гц", 200, 800),
    ("середина 0,8–3 кГц", 800, 3000),
    ("присутствие 3–8 кГц", 3000, 8000),
    ("воздух 8–20 кГц", 8000, 20000),
]

HINTS = {
    0: ("больше саба, чем у референса — проверьте гул и бочку", "меньше саба — низ может звучать слабо"),
    1: ("больше низа — возможна каша в басе/бочке", "меньше низа — микс может звучать тонко"),
    2: ("больше низкой середины — «бубнение», грязь (часто 200–400 Гц)", "меньше низкой середины — может не хватать тела"),
    3: ("больше середины — «в лоб», гнусавость (~1 кГц)", "меньше середины — вокал и инструменты могут провалиться"),
    4: ("больше присутствия — резкость, сибилянты (с/ш/щ/ч)", "меньше присутствия — вокал может быть неразборчив"),
    5: ("больше воздуха — шипение, сибилянты", "меньше воздуха — микс может звучать глухо"),
}


def rms_db(path, af):
    cmd = ["ffmpeg", "-hide_banner", "-nostats", "-i", path, "-af", af + ",volumedetect", "-f", "null", "-"]
    err = subprocess.run(cmd, capture_output=True, text=True).stderr
    m = re.search(r"mean_volume:\s*(-?\d+(?:\.\d+)?|-inf) dB", err)
    if not m:
        raise RuntimeError(f"ffmpeg volumedetect failed on {path}:\n{err[-600:]}")
    return float(m.group(1))


def profile(path):
    full = rms_db(path, "aformat=channel_layouts=stereo")
    bands = []
    for _, lo, hi in BANDS:
        af = f"aformat=channel_layouts=stereo,highpass=f={lo},highpass=f={lo},lowpass=f={hi},lowpass=f={hi}"
        bands.append(round(rms_db(path, af) - full, 1))
    mid = rms_db(path, "aformat=channel_layouts=stereo,pan=mono|c0=0.5*c0+0.5*c1")
    side = rms_db(path, "aformat=channel_layouts=stereo,pan=mono|c0=0.5*c0-0.5*c1")
    return {"bands_rel_db": bands, "side_to_mid_db": round(side - mid, 1)}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("mix")
    ap.add_argument("reference")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    try:
        m_loud, r_loud = measure(args.mix), measure(args.reference)
        m_prof, r_prof = profile(args.mix), profile(args.reference)
    except RuntimeError as e:
        print(e, file=sys.stderr)
        return 1

    diffs = [round(a - b, 1) for a, b in zip(m_prof["bands_rel_db"], r_prof["bands_rel_db"])]
    hints = []
    for idx, d in enumerate(diffs):
        if d >= 2:
            hints.append(f"{BANDS[idx][0]}: +{d} дБ — {HINTS[idx][0]}")
        elif d <= -2:
            hints.append(f"{BANDS[idx][0]}: {d} дБ — {HINTS[idx][1]}")
    width = round(m_prof["side_to_mid_db"] - r_prof["side_to_mid_db"], 1)
    if width >= 3:
        hints.append(f"Стерео шире референса на {width} дБ — проверьте совместимость с моно.")
    elif width <= -3:
        hints.append(f"Стерео уже референса на {abs(width)} дБ — микс может звучать узко.")
    if m_loud["integrated_lufs"] is not None and r_loud["integrated_lufs"] is not None:
        ld = round(m_loud["integrated_lufs"] - r_loud["integrated_lufs"], 1)
        hints.insert(0, f"Громкость микса относительно референса: {ld:+} дБ (сравнивайте на слух только после выравнивания).")

    result = {"mix": m_loud, "reference": r_loud, "mix_profile": m_prof,
              "reference_profile": r_prof, "band_diff_db": diffs, "hints": hints}
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0

    print(f"Микс:      {args.mix}")
    print(f"Референс:  {args.reference}\n")
    print(f"{'':30} {'микс':>8} {'референс':>9}")
    for key, label, unit in [("integrated_lufs", "Громкость", "LUFS"), ("true_peak_dbtp", "True peak", "dBTP"),
                             ("lra_lu", "LRA", "LU"), ("plr_db", "PLR", "дБ")]:
        print(f"{label + ', ' + unit:30} {str(m_loud[key]):>8} {str(r_loud[key]):>9}")
    print("\nТональный баланс (полоса относительно всего сигнала, дБ):")
    for (name, _, _), a, b, d in zip(BANDS, m_prof["bands_rel_db"], r_prof["bands_rel_db"], diffs):
        print(f"  {name:28} {a:>8} {b:>9}   разница {d:+}")
    print(f"  {'стерео: сторона/середина':28} {m_prof['side_to_mid_db']:>8} {r_prof['side_to_mid_db']:>9}")
    print("\nПодсказки (ориентиры, проверять на слух):")
    for h in hints or ["Заметных расхождений с референсом нет."]:
        print(f"  • {h}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
