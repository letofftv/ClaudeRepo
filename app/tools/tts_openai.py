#!/usr/bin/env python3
"""Text to speech through any OpenAI-compatible /v1/audio/speech endpoint.

Works with local servers (omnivoice.cpp, qwentts.cpp, Silero wrappers,
openedai-speech) and with hosted ones. Long text is split into chunks by
sentences; the WAV pieces are joined into one file. Standard library only.

    python3 tts_openai.py --url http://127.0.0.1:8880/v1 --text-file t.txt --out speech.wav

An API key, if the server needs one, is read from the TTS_API_KEY
environment variable — never from the command line.
"""
import argparse
import io
import json
import os
import re
import sys
import urllib.error
import urllib.request
import wave


def endpoint(url):
    url = url.rstrip("/")
    if url.endswith("/audio/speech"):
        return url
    if not url.endswith("/v1"):
        url += "/v1"
    return url + "/audio/speech"


def split_text(text, max_chars):
    """Split by paragraphs, then sentences, keeping chunks under max_chars."""
    chunks, current = [], ""
    for para in re.split(r"\n\s*\n", text.strip()):
        sentences = re.split(r"(?<=[.!?…])\s+", para.strip())
        for sentence in sentences:
            while len(sentence) > max_chars:  # a very long sentence: cut on a space
                cut = sentence.rfind(" ", 0, max_chars)
                cut = cut if cut > 0 else max_chars
                if current:
                    chunks.append(current)
                    current = ""
                chunks.append(sentence[:cut].strip())
                sentence = sentence[cut:].strip()
            if current and len(current) + 1 + len(sentence) > max_chars:
                chunks.append(current)
                current = sentence
            else:
                current = (current + " " + sentence).strip()
        if current:
            chunks.append(current)
            current = ""
    return [c for c in chunks if c]


def synthesize(url, model, voice, text, fmt, timeout, speed=None):
    body = {"model": model, "input": text, "voice": voice, "response_format": fmt}
    if speed:
        body["speed"] = speed
    headers = {"Content-Type": "application/json"}
    key = os.environ.get("TTS_API_KEY")
    if key:
        headers["Authorization"] = "Bearer " + key
    req = urllib.request.Request(endpoint(url), data=json.dumps(body).encode("utf-8"),
                                 headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


def join_wavs(pieces, out_path, pause_s):
    """Concatenate PCM WAV pieces with a short pause between them."""
    params = None
    with wave.open(out_path, "wb") as out:
        for i, data in enumerate(pieces):
            with wave.open(io.BytesIO(data), "rb") as w:
                p = w.getparams()
                if params is None:
                    params = p
                    out.setparams(p)
                elif (p.nchannels, p.sampwidth, p.framerate) != (params.nchannels, params.sampwidth, params.framerate):
                    raise ValueError("куски WAV в разных форматах")
                if i and pause_s:
                    out.writeframes(b"\x00" * int(params.framerate * pause_s) * params.nchannels * params.sampwidth)
                out.writeframes(w.readframes(w.getnframes()))


def main(argv=None):
    ap = argparse.ArgumentParser(description="Озвучка текста через OpenAI-совместимый сервер")
    ap.add_argument("--url", required=True, help="адрес сервера, например http://127.0.0.1:8880/v1")
    ap.add_argument("--model", default="tts-1")
    ap.add_argument("--voice", default="default")
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--text-file")
    src.add_argument("--text")
    ap.add_argument("--out", required=True)
    ap.add_argument("--format", default="wav", choices=["wav", "mp3", "flac", "opus"])
    ap.add_argument("--max-chars", type=int, default=800, help="длина куска текста за один запрос")
    ap.add_argument("--pause", type=float, default=0.25, help="пауза между кусками, с (только WAV)")
    ap.add_argument("--speed", type=float)
    ap.add_argument("--timeout", type=float, default=600)
    args = ap.parse_args(argv)

    if args.text_file:
        with open(args.text_file, encoding="utf-8") as f:
            text = f.read()
    else:
        text = args.text
    chunks = split_text(text, args.max_chars)
    if not chunks:
        print("Пустой текст", file=sys.stderr)
        return 2
    if len(chunks) > 1 and args.format != "wav":
        print("Длинный текст склеивается только в WAV — используйте --format wav", file=sys.stderr)
        return 2
    pieces = []
    for i, chunk in enumerate(chunks, 1):
        print(f"[{i}/{len(chunks)}] {len(chunk)} символов", flush=True)
        try:
            pieces.append(synthesize(args.url, args.model, args.voice, chunk, args.format,
                                     args.timeout, args.speed))
        except urllib.error.HTTPError as exc:
            detail = exc.read()[:500].decode("utf-8", errors="replace")
            print(f"Сервер ответил {exc.code}: {detail}", file=sys.stderr)
            return 1
        except (urllib.error.URLError, OSError) as exc:
            print(f"Сервер озвучки недоступен: {exc}", file=sys.stderr)
            return 1
    if len(pieces) == 1:
        with open(args.out, "wb") as f:
            f.write(pieces[0])
    else:
        try:
            join_wavs(pieces, args.out, args.pause)
        except (wave.Error, ValueError, EOFError) as exc:
            print(f"Не удалось склеить WAV: {exc}", file=sys.stderr)
            return 1
    print(f"Готово: {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
