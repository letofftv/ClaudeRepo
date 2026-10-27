#!/usr/bin/env python3
"""Two-pass EBU R128 loudness normalization with ffmpeg (linear gain when possible).

Usage:
  loudnorm_2pass.py INPUT OUTPUT.wav [--target -14] [--tp -1] [--lra 11]

Pass 1 measures, pass 2 applies the measured values with linear=true, so the
track is only turned up/down, not compressed. If the target is unreachable
without exceeding the true-peak limit, ffmpeg falls back to dynamic mode —
the script warns: then a proper limiter in the DAW is the better tool.
Output: WAV 24-bit at the input's sample rate. Requires ffmpeg/ffprobe.
"""
import argparse
import json
import re
import subprocess
import sys


def sample_rate(path):
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "a:0", "-show_entries", "stream=sample_rate",
         "-of", "default=nw=1:nk=1", path], capture_output=True, text=True).stdout.strip()
    return out or "48000"


def last_json(text):
    m = re.findall(r"\{[^{}]*\}", text, flags=re.S)
    if not m:
        raise RuntimeError("ffmpeg loudnorm did not print JSON:\n" + text[-800:])
    return json.loads(m[-1])


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("input")
    ap.add_argument("output")
    ap.add_argument("--target", type=float, default=-14.0)
    ap.add_argument("--tp", type=float, default=-1.0)
    ap.add_argument("--lra", type=float, default=11.0)
    args = ap.parse_args()

    base = f"loudnorm=I={args.target}:TP={args.tp}:LRA={args.lra}"
    p1 = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", args.input,
                         "-af", base + ":print_format=json", "-f", "null", "-"],
                        capture_output=True, text=True)
    try:
        m = last_json(p1.stderr)
    except (RuntimeError, json.JSONDecodeError) as e:
        print(e, file=sys.stderr)
        return 1

    af = (f"{base}:measured_I={m['input_i']}:measured_TP={m['input_tp']}:measured_LRA={m['input_lra']}"
          f":measured_thresh={m['input_thresh']}:offset={m['target_offset']}:linear=true:print_format=json")
    p2 = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-y", "-i", args.input, "-af", af,
                         "-ar", sample_rate(args.input), "-c:a", "pcm_s24le", args.output],
                        capture_output=True, text=True)
    if p2.returncode != 0:
        print(p2.stderr[-800:], file=sys.stderr)
        return 1
    r = last_json(p2.stderr)

    print(f"Было:  {m['input_i']} LUFS, true peak {m['input_tp']} dBTP")
    print(f"Стало: {r['output_i']} LUFS, true peak {r['output_tp']} dBTP -> {args.output}")
    if r.get("normalization_type") != "linear":
        print("ВНИМАНИЕ: линейная нормализация невозможна (цель не достигается без превышения true peak) —\n"
              "ffmpeg применил динамическую обработку. Лучше довести громкость лимитером в DAW,\n"
              "а этот скрипт использовать для финальной подгонки уровня.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
