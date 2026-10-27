---
name: audio-toolkit
description: Открытые инструменты, которые Claude может запускать на маке для музыки — разделение на стемы и вокал (python-audio-separator, demucs-mlx), мастеринг по референсу (Matchering), цепочки обработки кодом с плагинами владельца (Pedalboard), тональность/темп/доли (librosa, Essentia, beat_this), высота вокала и выравнивание даблов, таймкоды русского текста (whisperX), аудио→MIDI, наброски песен (ACE-Step 1.5). Использовать, когда задачу удобнее решить скриптом, чем в DAW (stems, separation, reference mastering, pedalboard, key, BPM, alignment, MIDI).
---

# Открытые инструменты для музыки

Состояние на 2026-10-27. **Перед установкой — спросить владельца**;
ставить в отдельное окружение (`python3.12 -m venv ~/.venvs/audio`).
CLI и Python-библиотеки дешевле по контексту, чем MCP-серверы: MCP нужен
только для управления DAW (навык `ableton-control`).

Лицензии: ролики и треки некоммерческие — модели с NC-лицензиями
допустимы, но они отмечены; при монетизации пересмотреть.

## Разделение на стемы и вокал

- **python-audio-separator** (MIT, `pip install "audio-separator[cpu]"` —
  вариант для Apple Silicon уточнить в README): CLI и Python API; на маке —
  MPS и CoreML. Современные модели RoFormer (becruily, unwa, gabox) и
  ансамбли: вокал ~11,3 SDR, инструментал ~17,5 SDR. **Модели качаются с
  GitHub**, не с Hugging Face — важно для загрузок из России. Список
  моделей: `audio-separator --list_models --list_format=json`.
  Есть и полезные модели для вокала: де-реверб, шумоподавление,
  «Aspiration» (вытаскивает вдохи), отделение бэк-вокала.
- **demucs-mlx** (MIT): быстрые 4 стема (барабаны, бас, другое, вокал) на
  MLX. Веса — Hugging Face (можно зеркало через `HF_ENDPOINT`). Лицензия
  весов Demucs «неясна» (MUSDB — только для исследований).
- Зачем: стемы из минусовки для тонкой правки (опустить середину бита под
  вокал, поправить бас), инструментал из чужого трека для референса,
  чистый вокал для таймкодов текста. Основой микса оставлять оригинал —
  у разделения есть артефакты.

## Мастеринг по референсу

- **Matchering 2.0** (GPL-3): подгоняет громкость, АЧХ, пики и ширину
  стерео под референс, свой лимитер.
  ```python
  import matchering as mg
  mg.process(target="mix.wav", reference="reference.wav",
             results=[mg.pcm24("master_24bit.wav")])
  ```
  Результат — черновой мастер или ориентир; проверить
  `loudness_report.py --role master` и ушами. Референс — того же жанра.
- AI-сведение и мастеринг (ITO-Master, Diff-MST, automix-toolkit) — пока
  исследовательский уровень, не брать.

## Обработка кодом и плагины владельца

- **Pedalboard** (Spotify, GPL-3): встроенные компрессор, лимитер, EQ,
  реверб, дилей, питч; **загружает установленные у владельца AU и VST3**
  на Apple Silicon (`load_plugin`, пресеты `.vstpreset`). Плагины с iLok
  или первым запуском в своём окне — один раз открыть вручную.
  ```python
  from pedalboard import Pedalboard, HighpassFilter, Compressor, load_plugin
  from pedalboard.io import AudioFile
  board = Pedalboard([HighpassFilter(90), Compressor(threshold_db=-18, ratio=4)])
  with AudioFile("vox.wav") as f:
      audio, sr = f.read(f.frames), f.samplerate
  with AudioFile("vox_proc.wav", "w", sr, audio.shape[0]) as f:
      f.write(board(audio, sr))
  ```
- **DawDreamer** (GPL-3) — графы, автоматизация, рендер MIDI; импортировать
  до PyTorch, иначе падает.
- ffmpeg и sox (`brew install ffmpeg sox`) — конвертация, обрезка, громкость.

## Анализ

- **librosa 1.0** (ISC, Python ≥ 3.12) — общее; pYIN для высоты без модели.
- **Essentia** (AGPL-3, есть колёса для arm64) — тональность и BPM.
- **beat_this** (MIT, веса не с HF) — доли и сильные доли; сверять с сеткой
  долей фабрики.
- Структура песни: all-in-one устарел (2023); SongFormer — новее, но
  проверен только на GPU.
- madmom заброшен, модели NC — не брать.

## Высота вокала и выравнивание

- **RMVPE** (лучший трекер высоты для пения в миксе) или **torchcrepe** /
  **pYIN** — отчёты вида «эта фраза на −30 центов». Сам тюнинг — в DAW
  (Auto Shift, Graillon, Melodyne): зрелого открытого автотюна на Python нет.
- **Даблы:** открытого аналога VocAlign нет. Самодельно — synctoolbox (DTW,
  MIT) + растяжение Rubber Band (GPL-2) по карте времени. audalign находит
  только постоянный сдвиг.

## Таймкоды русского текста

- **whisperX** (BSD-2): выравнивание слов с русской моделью
  `jonatasgrosman/wav2vec2-large-xlsr-53-russian` (Hugging Face); на маке —
  CPU, int8. Пример: `whisperx vocals.wav --language ru --compute_type int8
  --device cpu` (флаги сверить с `--help`). **Выравнивать по чистому
  вокалу**, а не по миксу. На фабрике уже есть Whisper large-v3 с
  таймкодами слов — для клипов использовать его.
- ctc-forced-aligner (`--language rus --romanize`) — модель по умолчанию NC.

## Аудио → MIDI

- **MuScriptor** (код MIT, веса CC BY-NC, на маке MPS): весь микс → MIDI по
  инструментам, карта темпа, квантизация. Плагин NeuralNote v2 (Apache,
  AU/VST3) использует его внутри.
- **SOME** (MIT) — пение → MIDI; **basic-pitch** (Apache, CoreML) — одна
  партия за раз.
- Аккорды: chord-extractor (Chordino) или MIDI → music21 `chordify`.

## Наброски и демо

- **ACE-Step 1.5** (MIT): на маке — MLX, при ≤6 ГБ — модель 2B turbo без
  планировщика. Русский есть в списке языков (качество не проверено).
  Кавер, перерисовка фрагмента, Vocal2BGM (аранжировка под вокал), LoRA по
  ~8 песням. Веса — HF и ModelScope. **Его навык транскрипции текста
  отправляет аудио в OpenAI/ElevenLabs — не ставить.**
- **Magenta RealTime 2** — инструментальный джем в реальном времени на M1
  Pro (MLX, есть AUv3); лицензия весов не проверена.
- Не для этого железа: YuE2 (24 ГБ, bf16), SongGeneration v2 (22–28 ГБ),
  DiffRhythm (без русского), MusicGen (NC, заброшен).

## Сервер фабрики (GTX 1050 Ti)

Разделение — ONNX-модели audio-separator (onnxruntime-gpu на CUDA 12) или
BSRoformer.cpp (GGML, CUDA/Vulkan, без PyTorch). Генеративное — не влезает.
Правила карты — в `CLAUDE.md` репозитория ClaudeRepo.
