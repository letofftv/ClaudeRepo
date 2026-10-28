#!/usr/bin/env python3
"""Run a speech recognizer, then make SRT and VTT subtitles from its JSON.

Any Whisper engine fits as long as it leaves JSON with timings in the result
folder: faster-whisper in Docker, whisper-ctranslate2, whisper.cpp with -oj.
The engine command goes after "--". This script adds the language flag
itself; "auto" adds nothing (or --auto-lang), so engines without an "auto"
value, like faster-whisper, detect the language on their own.

    whisper_subs.py --out OUT --lang ru --lang-flag=--lang -- docker run … IMAGE in.wav OUT
    whisper_subs.py --out OUT --json OUT/asr.json        # only convert existing JSON

Long segments are split into cues by word timings when the engine gives
them: at most --max-chars characters and --max-dur seconds per cue, two lines
of --line-chars. Standard library only.
"""
import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

SENTENCE_END = (".", "!", "?", "…", ";")
SKIP_JSON = {"report.json", "job.json"}


def _num(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _words(items):
    words = []
    for w in items or []:
        if not isinstance(w, dict):
            continue
        text = str(w.get("word", w.get("text", ""))).strip()
        start, end = _num(w.get("start")), _num(w.get("end"))
        if text and start is not None:
            words.append({"text": text, "start": start, "end": max(end if end is not None else start, start)})
    return words


def _from_words(items):
    words = _words(items)
    if not words:
        return []
    return [{"start": words[0]["start"], "end": words[-1]["end"],
             "text": " ".join(w["text"] for w in words), "words": words}]


def segments_from(data):
    """Segments in seconds from the usual Whisper JSON shapes.

    faster-whisper / openai-whisper: {"segments": [{start, end, text, words}]};
    whisper.cpp -oj: {"transcription": [{offsets: {from, to} in ms, text}]};
    transformers: {"chunks": [{timestamp: [start, end], text}]}; or bare word lists.
    """
    if isinstance(data, dict):
        for key in ("segments", "transcription", "chunks"):
            if isinstance(data.get(key), list):
                return segments_from(data[key])
        return _from_words(data.get("words")) if isinstance(data.get("words"), list) else []
    if not isinstance(data, list):
        return []
    items = [i for i in data if isinstance(i, dict)]
    if items and all("word" in i and "text" not in i for i in items):
        return _from_words(items)
    segments = []
    for item in items:
        text = " ".join(str(item.get("text", "")).split())
        start, end = _num(item.get("start")), _num(item.get("end"))
        if start is None and isinstance(item.get("offsets"), dict):
            start, end = _num(item["offsets"].get("from")), _num(item["offsets"].get("to"))
            start = start / 1000 if start is not None else None
            end = end / 1000 if end is not None else None
        if start is None and isinstance(item.get("timestamp"), (list, tuple)) and len(item["timestamp"]) == 2:
            start, end = _num(item["timestamp"][0]), _num(item["timestamp"][1])
        if start is None or not text:
            continue
        segments.append({"start": start, "end": max(end if end is not None else start, start),
                         "text": text, "words": _words(item.get("words"))})
    return segments


def split_segment(seg, max_chars, max_dur, gap=1.0):
    """One cue per segment; long ones are cut on word timings."""
    text = " ".join(seg["text"].split())
    words = seg.get("words") or []
    if not words or (len(text) <= max_chars and seg["end"] - seg["start"] <= max_dur):
        return [{"start": seg["start"], "end": seg["end"], "text": text}]
    cues, cur = [], []

    def flush():
        if cur:
            cues.append({"start": cur[0]["start"], "end": cur[-1]["end"], "text": " ".join(w["text"] for w in cur)})
            cur.clear()

    for w in words:
        if cur:
            length = len(" ".join(x["text"] for x in cur)) + 1 + len(w["text"])
            if length > max_chars or w["end"] - cur[0]["start"] > max_dur or w["start"] - cur[-1]["end"] > gap:
                flush()
        cur.append(w)
        if w["text"].endswith(SENTENCE_END) and len(" ".join(x["text"] for x in cur)) >= max_chars // 2:
            flush()
    flush()
    return cues


def tidy(cues, min_dur=0.4):
    """Sorted, no overlaps, no flashes shorter than min_dur where there is room."""
    cues = sorted((c for c in cues if c["text"]), key=lambda c: c["start"])
    for i, c in enumerate(cues):
        nxt = cues[i + 1]["start"] if i + 1 < len(cues) else None
        if c["end"] - c["start"] < min_dur:
            c["end"] = c["start"] + min_dur
        if nxt is not None and c["end"] > nxt:
            c["end"] = max(nxt, c["start"] + 0.04)
    return cues


def wrap(text, width):
    """Two lines at the space nearest the middle when the cue is long."""
    if len(text) <= width or " " not in text:
        return text
    spaces = [i for i, ch in enumerate(text) if ch == " "]
    cut = min(spaces, key=lambda i: abs(i - len(text) / 2))
    return text[:cut] + "\n" + text[cut + 1:]


def timestamp(seconds, sep):
    ms = int(round(max(0.0, seconds) * 1000))
    h, ms = divmod(ms, 3_600_000)
    m, ms = divmod(ms, 60_000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d}{sep}{ms:03d}"


def to_srt(cues, width):
    return "".join(f"{i}\n{timestamp(c['start'], ',')} --> {timestamp(c['end'], ',')}\n{wrap(c['text'], width)}\n\n"
                   for i, c in enumerate(cues, 1))


def to_vtt(cues, width):
    return "WEBVTT\n\n" + "".join(f"{timestamp(c['start'], '.')} --> {timestamp(c['end'], '.')}\n{wrap(c['text'], width)}\n\n"
                                  for c in cues)


def find_json(out_dir, since=0.0):
    """The engine's JSON: asr.json first, else the newest one written during this run."""
    found = [p for p in Path(out_dir).rglob("*.json") if p.name not in SKIP_JSON and p.stat().st_mtime >= since]
    named = [p for p in found if p.name == "asr.json"]
    return (named or sorted(found, key=lambda p: p.stat().st_mtime, reverse=True) or [None])[0]


def engine_argv(command, lang, lang_flag, auto_lang):
    if lang and lang != "auto":
        return [*command, lang_flag, lang]
    return [*command, lang_flag, auto_lang] if auto_lang else list(command)


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    command = []
    if "--" in argv:
        cut = argv.index("--")
        argv, command = argv[:cut], argv[cut + 1:]
    ap = argparse.ArgumentParser(description="Распознавание речи и субтитры SRT/VTT из JSON движка")
    ap.add_argument("--out", required=True, help="папка результата: туда пишет движок и туда лягут субтитры")
    ap.add_argument("--lang", default="auto", help="ru, en … или auto")
    ap.add_argument("--lang-flag", default="--language", help="как движок принимает язык (--lang, -l …)")
    ap.add_argument("--auto-lang", default="", help="что передать при auto (whisper.cpp: auto); пусто — ничего")
    ap.add_argument("--json", help="готовый JSON движка (без запуска)")
    ap.add_argument("--name", default="subs", help="имя файлов субтитров")
    ap.add_argument("--max-chars", type=int, default=84)
    ap.add_argument("--max-dur", type=float, default=7.0)
    ap.add_argument("--line-chars", type=int, default=42)
    args = ap.parse_args(argv)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    started = 0.0
    if command:
        run = engine_argv(command, args.lang, args.lang_flag, args.auto_lang)
        print("Движок: " + " ".join(run), flush=True)
        started = time.time() - 2  # files the engine writes now, not older ones
        try:
            rc = subprocess.call(run, stdin=subprocess.DEVNULL)
        except OSError as exc:
            print(f"Движок не запустился: {exc}", file=sys.stderr)
            return 127
        if rc != 0:
            print(f"Движок завершился с кодом {rc}", file=sys.stderr)
            return rc
    elif not args.json:
        ap.error("нужна команда движка после -- или --json")

    srt_path, vtt_path = out / f"{args.name}.srt", out / f"{args.name}.vtt"
    source = Path(args.json) if args.json else find_json(out, started)
    if source is None or not source.is_file():
        made_by_engine = sorted(out.glob("*.srt"))
        if made_by_engine:
            print(f"Готово: движок сам сделал {', '.join(p.name for p in made_by_engine)}")
            return 0
        print("Движок не оставил JSON с таймкодами в папке результата", file=sys.stderr)
        return 1
    try:
        data = json.loads(source.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        print(f"Не удалось прочитать {source.name}: {exc}", file=sys.stderr)
        return 1
    cues = tidy([cue for seg in segments_from(data) for cue in split_segment(seg, args.max_chars, args.max_dur)])
    if not cues:
        keys = ", ".join(data) if isinstance(data, dict) else type(data).__name__
        print(f"В {source.name} нет отрезков с таймкодами (ключи: {keys})", file=sys.stderr)
        return 1
    made = []
    for path, text in ((srt_path, to_srt(cues, args.line_chars)), (vtt_path, to_vtt(cues, args.line_chars))):
        if not path.exists():
            path.write_text(text, encoding="utf-8")
            made.append(path.name)
    if not any(out.glob("*.txt")):
        (out / "transcript.txt").write_text("\n".join(c["text"] for c in cues) + "\n", encoding="utf-8")
        made.append("transcript.txt")
    lang = data.get("language") if isinstance(data, dict) else None
    detail = f", язык {lang}" if lang else ""
    print(f"Готово: {len(cues)} реплик до {timestamp(cues[-1]['end'], ',')}{detail}; "
          f"из {source.name} → {', '.join(made) or 'файлы уже были'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
