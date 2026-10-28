#!/usr/bin/env python3
"""Text to speech with Piper (piper-tts: ONNX on the CPU) — no server needed.

    tts_piper.py --voice ru_RU-irina-medium --voices-dir ~/hub-work/models/piper --text-file t.txt --out speech.wav

Each paragraph (blank line between) is one phrase; lines inside a paragraph
are joined, so hard-wrapped text keeps its intonation. Piper writes one WAV
per paragraph with the voice loaded once; they are joined with --pause.

Voices are two files, <voice>.onnx and <voice>.onnx.json, from Hugging Face
(rhasspy/piper-voices). Download into the voices folder with
    python3 -m piper.download_voices ru_RU-irina-medium --data-dir <folder>
or on the Mac and copy both files over. Standard library only.
"""
import argparse
import re
import subprocess
import sys
import tempfile
import wave
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from tts_openai import join_wavs  # noqa: E402


def paragraphs(text):
    return [" ".join(p.split()) for p in re.split(r"\n\s*\n", text) if p.strip()]


def find_voice(voice, voices_dir):
    path = Path(voice)
    if path.suffix == ".onnx" and path.is_file():
        return path
    candidate = Path(voices_dir).expanduser() / f"{voice}.onnx"
    return candidate if candidate.is_file() else None


def main(argv=None):
    ap = argparse.ArgumentParser(description="Озвучка текста голосами Piper")
    ap.add_argument("--voice", default="ru_RU-irina-medium", help="имя голоса или путь к .onnx")
    ap.add_argument("--voices-dir", default=".", help="папка с голосами (.onnx + .onnx.json)")
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--text-file")
    src.add_argument("--text")
    ap.add_argument("--out", required=True)
    ap.add_argument("--speed", type=float, default=1.0, help="темп: 1.2 — быстрее, 0.8 — медленнее")
    ap.add_argument("--pause", type=float, default=0.5, help="пауза между абзацами, с")
    ap.add_argument("--sentence-silence", type=float, default=0.15, help="пауза между предложениями, с")
    ap.add_argument("--speaker", type=int, help="номер диктора в многоголосой модели")
    ap.add_argument("--piper", default="piper", help="команда piper (pipx install piper-tts)")
    args = ap.parse_args(argv)

    text = Path(args.text_file).read_text(encoding="utf-8") if args.text_file else args.text
    parts = paragraphs(text)
    if not parts:
        print("Пустой текст", file=sys.stderr)
        return 2
    model = find_voice(args.voice, args.voices_dir)
    if model is None:
        print(f"Голос {args.voice} не найден в {args.voices_dir}. Скачать: python3 -m piper.download_voices "
              f"{args.voice} --data-dir {args.voices_dir}", file=sys.stderr)
        return 2
    if not model.with_name(model.name + ".json").is_file():
        print(f"Рядом с {model.name} нет {model.name}.json — скачайте оба файла голоса", file=sys.stderr)
        return 2
    speed = min(max(args.speed, 0.25), 4.0)

    with tempfile.TemporaryDirectory(prefix="piper-") as tmp:  # not next to the result: the job lists that folder
        text_file, wav_dir = Path(tmp) / "text.txt", Path(tmp) / "wav"
        text_file.write_text("\n".join(parts) + "\n", encoding="utf-8")
        cmd = [args.piper, "-m", str(model), "-i", str(text_file), "-d", str(wav_dir),
               "--length-scale", f"{1 / speed:.3f}", "--sentence-silence", str(args.sentence_silence)]
        if args.speaker is not None:
            cmd += ["-s", str(args.speaker)]
        print(f"Piper: {model.stem}, абзацев {len(parts)}, темп {speed:g}", flush=True)
        try:
            rc = subprocess.call(cmd, stdin=subprocess.DEVNULL)
        except OSError as exc:
            print(f"Piper не запустился: {exc} (pipx install piper-tts)", file=sys.stderr)
            return 127
        if rc != 0:
            print(f"Piper завершился с кодом {rc}", file=sys.stderr)
            return rc
        # files are named by a monotonic clock, so numeric order is paragraph order
        wavs = sorted(wav_dir.glob("*.wav"), key=lambda p: (len(p.stem), p.stem))
        if len(wavs) != len(parts):
            print(f"Piper вернул {len(wavs)} файлов на {len(parts)} абзацев", file=sys.stderr)
            if not wavs:
                return 1
        try:
            join_wavs([p.read_bytes() for p in wavs], args.out, args.pause)
        except (wave.Error, ValueError, EOFError, OSError) as exc:
            print(f"Не удалось склеить WAV: {exc}", file=sys.stderr)
            return 1
    with wave.open(args.out, "rb") as w:
        seconds = w.getnframes() / w.getframerate()
    print(f"Готово: {args.out} ({seconds:.1f} с)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
