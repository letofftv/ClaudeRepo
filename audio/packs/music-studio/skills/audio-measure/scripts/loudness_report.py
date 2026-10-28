#!/usr/bin/env python3
"""Loudness report for audio files using only ffmpeg (EBU R128 / BS.1770).

Usage:
  loudness_report.py FILE [FILE ...] [--target -14] [--tp -1] [--role mix|beat|master] [--json] [--json-out PATH]

Prints integrated loudness (LUFS), loudness range (LU), true peak (dBTP),
max short-term loudness and PLR, then plain-language verdicts in Russian.
Requires ffmpeg on PATH. No Python packages needed.
"""
import argparse
import json
import re
import subprocess
import sys

NUM = r"(-?\d+(?:\.\d+)?|-inf|inf)"


def to_float(s):
    if s in ("-inf", "inf"):
        return float(s)
    return float(s)


def measure(path):
    cmd = [
        "ffmpeg", "-hide_banner", "-nostats", "-i", path,
        "-af", "ebur128=peak=true:framelog=info",
        "-f", "null", "-",
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    err = proc.stderr
    if proc.returncode != 0 or "Summary:" not in err:
        raise RuntimeError(f"ffmpeg failed on {path}:\n{err[-800:]}")

    summary = err[err.rfind("Summary:"):]
    integrated = re.search(r"I:\s+" + NUM + r" LUFS", summary)
    lra = re.search(r"LRA:\s+" + NUM + r" LU", summary)
    peak = re.search(r"Peak:\s+" + NUM + r" dBFS", summary)

    # Per-frame lines look like: "... M: -20.1 S: -19.8     I: -19.5 LUFS ..."
    shorts = [to_float(m) for m in re.findall(r"\bS:\s*" + NUM, err[: err.rfind("Summary:")])]
    shorts = [s for s in shorts if s > -70]

    result = {
        "file": path,
        "integrated_lufs": to_float(integrated.group(1)) if integrated else None,
        "lra_lu": to_float(lra.group(1)) if lra else None,
        "true_peak_dbtp": to_float(peak.group(1)) if peak else None,
        "max_short_term_lufs": max(shorts) if shorts else None,
    }
    i, tp = result["integrated_lufs"], result["true_peak_dbtp"]
    result["plr_db"] = round(tp - i, 1) if i is not None and tp is not None else None
    return result


def verdicts(r, target, tp_limit, role):
    out = []
    i, tp, plr, lra = r["integrated_lufs"], r["true_peak_dbtp"], r["plr_db"], r["lra_lu"]
    if i is None:
        return ["Не удалось измерить громкость."]

    if role == "beat":
        # Engineers' consensus: drop a mastered beat by 6–10 dB; aim near −19 LUFS, capped at that range.
        gain = round(-19.0 - i, 1)
        if gain < 0:
            drop = min(abs(gain), 10.0)
            note = " (ограничено 10 дБ — дальше решать на слух)" if abs(gain) > 10 else ""
            out.append(
                f"Минусовка громкая ({i} LUFS). Стартовая точка: опустить её на {drop} дБ{note}, "
                "чтобы оставить запас под вокал и мастер; для пережатых минусовок обычно 6–10 дБ. "
                "Это ориентир, а не правило."
            )
        else:
            out.append(f"Минусовка уже тихая ({i} LUFS) — опускать не нужно.")
        if plr is not None and plr < 8:
            out.append(f"PLR {plr} дБ — минусовка уже сильно сжата лимитером; не дожимайте её ещё раз на мастере.")
        return out

    diff = round(i - target, 1)
    if role == "master":
        if diff > 0.5:
            out.append(f"Громче цели {target} LUFS на {diff} дБ — площадка убавит; лишнее сжатие потеряно зря.")
        elif diff < -1.5:
            out.append(f"Тише цели {target} LUFS на {abs(diff)} дБ — часть площадок не прибавит громкость.")
        else:
            out.append(f"Громкость в пределах цели {target} LUFS.")
        if tp is not None and tp > tp_limit:
            out.append(f"True peak {tp} dBTP выше {tp_limit} — риск искажений после кодирования в AAC/Ogg.")
        if i > -14 and tp is not None and tp > -2:
            out.append("Для мастера громче −14 LUFS Spotify советует true peak не выше −2 dBTP.")
    else:  # mix before mastering
        if tp is not None and tp > -3:
            out.append(f"Пик {tp} dBTP — мало запаса для мастеринга; лучше пики около −6 dBFS.")
        else:
            out.append("Запас по пикам для мастеринга есть.")

    if plr is not None:
        if plr < 7:
            out.append(f"PLR {plr} дБ — очень плотно, динамика задавлена (ориентир для поп/рэпа ~8–12 дБ).")
        elif plr > 16:
            out.append(f"PLR {plr} дБ — много динамики; для стриминга это нормально, если так задумано.")
    if lra is not None and lra < 3 and role == "master":
        out.append(f"LRA {lra} LU — почти нет разницы между тихими и громкими частями.")
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("files", nargs="+")
    ap.add_argument("--target", type=float, default=-14.0, help="целевая интегральная громкость, LUFS")
    ap.add_argument("--tp", type=float, default=-1.0, help="предел true peak, dBTP")
    ap.add_argument("--role", choices=["mix", "beat", "master"], default="master")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--json-out", help="также записать результат в JSON-файл (для пульта и других программ)")
    args = ap.parse_args()

    results = []
    for f in args.files:
        try:
            r = measure(f)
        except RuntimeError as e:
            print(e, file=sys.stderr)
            return 1
        r["verdicts"] = verdicts(r, args.target, args.tp, args.role)
        r.update({"role": args.role, "target_lufs": args.target, "tp_limit_dbtp": args.tp})
        results.append(r)

    if args.json_out:
        with open(args.json_out, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)

    if args.json:
        print(json.dumps(results, ensure_ascii=False, indent=2))
        return 0

    for r in results:
        print(f"== {r['file']}")
        print(f"  Интегральная громкость: {r['integrated_lufs']} LUFS")
        print(f"  Макс. кратковременная:  {r['max_short_term_lufs']} LUFS")
        print(f"  Диапазон (LRA):         {r['lra_lu']} LU")
        print(f"  True peak:              {r['true_peak_dbtp']} dBTP")
        print(f"  PLR (пик − громкость):  {r['plr_db']} дБ")
        for v in r["verdicts"]:
            print(f"  • {v}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
