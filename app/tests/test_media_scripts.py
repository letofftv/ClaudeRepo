"""Wrappers in app/tools: Whisper JSON → SRT/VTT, Piper → one WAV. Fake engines, no models.

    cd app && python3 -m unittest tests.test_media_scripts -v
"""
import io
import json
import os
import sys
import tempfile
import unittest
import wave
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

APP = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(APP / "tools"))

import tts_piper  # noqa: E402
import whisper_subs as ws  # noqa: E402

FASTER_WHISPER = {
    "language": "ru",
    "segments": [
        {"start": 0.0, "end": 2.0, "text": " Привет, мир.", "words": [
            {"word": " Привет,", "start": 0.0, "end": 0.8}, {"word": " мир.", "start": 0.9, "end": 2.0}]},
        {"start": 2.5, "end": 4.0, "text": " Второй отрезок", "words": []},
    ],
}

FAKE_ENGINE = """import json, sys
from pathlib import Path
out = Path(sys.argv[2])
(out / "argv.json").write_text(json.dumps(sys.argv[1:]))
if "fail" in sys.argv:
    sys.exit(2)
(out / "asr.json").write_text(json.dumps(%s, ensure_ascii=False), encoding="utf-8")
"""

FAKE_PIPER = """#!%s
import os, sys, time, wave
from pathlib import Path
args = sys.argv[1:]
text, out = Path(args[args.index("-i") + 1]), Path(args[args.index("-d") + 1])
out.mkdir(parents=True, exist_ok=True)
if os.environ.get("FAKE_PIPER_ARGS"):
    Path(os.environ["FAKE_PIPER_ARGS"]).write_text(" ".join(args))
for line in text.read_text(encoding="utf-8").splitlines():
    if line.strip():
        with wave.open(str(out / f"{time.monotonic_ns()}.wav"), "wb") as w:
            w.setnchannels(1); w.setsampwidth(2); w.setframerate(22050)
            w.writeframes(b"\\x01\\x00" * 22050)  # 1 s per paragraph
"""


def quiet(fn, *args):
    with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
        return fn(*args)


class WhisperSubsTest(unittest.TestCase):
    def test_json_shapes(self):
        segs = ws.segments_from(FASTER_WHISPER)
        self.assertEqual([s["text"] for s in segs], ["Привет, мир.", "Второй отрезок"])
        self.assertEqual(len(segs[0]["words"]), 2)
        cpp = {"transcription": [{"offsets": {"from": 1500, "to": 3250}, "text": " Раз два"}]}
        self.assertEqual(ws.segments_from(cpp), [{"start": 1.5, "end": 3.25, "text": "Раз два", "words": []}])
        words = [{"word": "один", "start": 0.1, "end": 0.4}, {"word": "два", "start": 0.5, "end": 0.9}]
        self.assertEqual(ws.segments_from({"words": words})[0]["text"], "один два")
        self.assertEqual(ws.segments_from(words)[0]["end"], 0.9)
        chunks = {"chunks": [{"timestamp": [0.0, 1.0], "text": "чанк"}]}
        self.assertEqual(ws.segments_from(chunks)[0]["text"], "чанк")
        self.assertEqual(ws.segments_from({"text": "без таймкодов"}), [])

    def test_long_segment_split_by_words(self):
        words = [{"text": f"слово{i}", "start": i * 0.5, "end": i * 0.5 + 0.4} for i in range(30)]
        seg = {"start": 0.0, "end": 15.0, "text": " ".join(w["text"] for w in words), "words": words}
        cues = ws.split_segment(seg, max_chars=40, max_dur=4.0)
        self.assertGreater(len(cues), 3)
        self.assertTrue(all(len(c["text"]) <= 40 and c["end"] - c["start"] <= 4.0 for c in cues))
        self.assertEqual(" ".join(c["text"] for c in cues), seg["text"])

    def test_tidy_and_formats(self):
        cues = ws.tidy([{"start": 1.0, "end": 3.0, "text": "второй"}, {"start": 0.0, "end": 1.5, "text": "первый"},
                        {"start": 3.0, "end": 3.1, "text": "вспышка"}])
        self.assertEqual([c["text"] for c in cues], ["первый", "второй", "вспышка"])
        self.assertEqual(cues[0]["end"], 1.0)  # no overlap with the next cue
        self.assertAlmostEqual(cues[2]["end"], 3.4)  # stretched to the minimum length
        srt = ws.to_srt(cues[:1], 42)
        self.assertEqual(srt, "1\n00:00:00,000 --> 00:00:01,000\nпервый\n\n")
        self.assertTrue(ws.to_vtt(cues[:1], 42).startswith("WEBVTT\n\n00:00:00.000 --> 00:00:01.000\n"))
        self.assertEqual(ws.wrap("раз два три четыре", 10), "раз два\nтри четыре")

    def test_language_flag(self):
        cmd = ["engine", "in.wav"]
        self.assertEqual(ws.engine_argv(cmd, "ru", "--lang", ""), ["engine", "in.wav", "--lang", "ru"])
        self.assertEqual(ws.engine_argv(cmd, "auto", "--lang", ""), cmd)
        self.assertEqual(ws.engine_argv(cmd, "auto", "-l", "auto"), ["engine", "in.wav", "-l", "auto"])

    def test_runs_engine_and_writes_subtitles(self):
        with tempfile.TemporaryDirectory() as tmp:
            engine = Path(tmp) / "engine.py"
            engine.write_text(FAKE_ENGINE % json.dumps(FASTER_WHISPER, ensure_ascii=False), encoding="utf-8")
            out = Path(tmp) / "out"
            out.mkdir()
            base = ["--out", str(out), "--lang-flag=--lang", "--", sys.executable, str(engine), "in.wav", str(out)]
            self.assertEqual(quiet(ws.main, ["--lang", "auto", *base]), 0)
            self.assertNotIn("--lang", json.loads((out / "argv.json").read_text()))
            srt = (out / "subs.srt").read_text(encoding="utf-8")
            self.assertIn("00:00:02,500 --> 00:00:04,000\nВторой отрезок", srt)
            self.assertTrue((out / "subs.vtt").read_text(encoding="utf-8").startswith("WEBVTT"))
            self.assertIn("Привет, мир.", (out / "transcript.txt").read_text(encoding="utf-8"))

            for name in ("subs.srt", "subs.vtt", "asr.json"):
                (out / name).unlink()
            self.assertEqual(quiet(ws.main, ["--lang", "ru", *base]), 0)
            self.assertEqual(json.loads((out / "argv.json").read_text())[-2:], ["--lang", "ru"])
            self.assertEqual(quiet(ws.main, ["--lang", "ru", *base, "fail"]), 2)

    def test_reports_missing_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            self.assertEqual(quiet(ws.main, ["--out", tmp, "--", sys.executable, "-c", "pass"]), 1)
            (out / "clip.srt").write_text("1\n00:00:00,000 --> 00:00:01,000\nготово\n", encoding="utf-8")
            self.assertEqual(quiet(ws.main, ["--out", tmp, "--", sys.executable, "-c", "pass"]), 0)  # engine made SRT
            (out / "clip.srt").unlink()
            (out / "odd.json").write_text('{"text": "без таймкодов"}', encoding="utf-8")
            self.assertEqual(quiet(ws.main, ["--out", tmp, "--json", str(out / "odd.json")]), 1)


class PiperTest(unittest.TestCase):
    def test_paragraphs_become_one_wav_with_pauses(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            piper = tmp / "piper"
            piper.write_text(FAKE_PIPER % sys.executable, encoding="utf-8")
            piper.chmod(0o755)
            voices = tmp / "voices"
            voices.mkdir()
            (voices / "ru_RU-test-medium.onnx").write_bytes(b"")
            (voices / "ru_RU-test-medium.onnx.json").write_text("{}")
            out = tmp / "job" / "speech.wav"
            out.parent.mkdir()
            text = "Первый абзац,\nперенесённый строкой.\n\nВторой абзац.\n\n\nТретий."
            args = ["--piper", str(piper), "--voices-dir", str(voices), "--voice", "ru_RU-test-medium",
                    "--text", text, "--out", str(out), "--pause", "0.5", "--speed", "1.25"]
            self.assertEqual(quiet(tts_piper.main, args), 0)
            with wave.open(str(out), "rb") as w:
                self.assertAlmostEqual(w.getnframes() / w.getframerate(), 3 + 2 * 0.5, places=2)
            self.assertEqual(list(out.parent.iterdir()), [out])  # the temp folder is gone
            self.assertEqual(tts_piper.paragraphs(text)[0], "Первый абзац, перенесённый строкой.")

            self.assertEqual(quiet(tts_piper.main, [*args[:4], "--voice", "ru_RU-missing", *args[6:]]), 2)
            (voices / "ru_RU-test-medium.onnx.json").unlink()
            self.assertEqual(quiet(tts_piper.main, args), 2)

    def test_length_scale_follows_speed(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            piper = tmp / "piper"
            piper.write_text(FAKE_PIPER % sys.executable, encoding="utf-8")
            piper.chmod(0o755)
            (tmp / "v.onnx").write_bytes(b"")
            (tmp / "v.onnx.json").write_text("{}")
            os.environ["FAKE_PIPER_ARGS"] = str(tmp / "args.txt")
            try:
                rc = quiet(tts_piper.main, ["--piper", str(piper), "--voice", str(tmp / "v.onnx"), "--text", "Раз.",
                                            "--out", str(tmp / "speech.wav"), "--speed", "2", "--speaker", "1"])
            finally:
                os.environ.pop("FAKE_PIPER_ARGS", None)
            self.assertEqual(rc, 0)
            args = (tmp / "args.txt").read_text()
            self.assertIn(f"-m {tmp / 'v.onnx'}", args)
            self.assertIn("--length-scale 0.500", args)  # twice as fast
            self.assertIn("-s 1", args)

if __name__ == "__main__":
    unittest.main()
