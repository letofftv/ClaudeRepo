# Находки

Оценка — с точки зрения фабрики (см. `CLAUDE.md`). Звёзды — на дату находки.
Широкие исследования — в `research/`.

## Что добавить к своей ферме (гипотеза, проверить на сервере)

Ядро уже есть: своя ферма (сцены кодом → кадры в Chromium → ffmpeg), Whisper
large-v3 на видеокарте, сетка долей, маски Apple Vision. Находки дополняют
его, а не заменяют:

1. **Playwright MCP** — запись настоящих интерфейсов с анимированным курсором
   для обучающих роликов.
2. **Озвучка** — **Silero** на процессоре (основная, русский) или
   **omnivoice.cpp** на видеокарте, если нужен клон постоянного голоса.
3. **Приёмы и блоки для сцен** — режиссура **product-launch-motion**, блоки и
   захват кадров через BeginFrame из **HyperFrames**, **gsap-skills** (если
   ферма на GSAP).
4. **Музыка** — **ACE-Step 1.5**, апскейл и плавность — **Video2X**, обложки —
   **stable-diffusion.cpp**.
5. **SkillSpector** — перед установкой любого навыка.

**Главный пробел — потолок фермы** (живописные персонажи, узнаваемое лицо,
живописная среда): локально на 4 ГБ не закрывается, см. «Пробелы».

## Все находки

| Находка | Для чего на фабрике | Статус | Карточка |
|---|---|---|---|
| SkillSpector | проверка навыков перед установкой | **взять** | [skillspector.md](skillspector.md) |
| Silero TTS v5 | основная русская озвучка, на CPU | **взять** | [silero-tts.md](silero-tts.md) |
| product-launch-motion | справочник режиссуры: та же техника, что у фермы | **взять** (справочник) | [product-launch-motion.md](product-launch-motion.md) |
| Playwright MCP (видео) | запись настоящих интерфейсов с курсором | **попробовать** | [playwright-mcp-video.md](playwright-mcp-video.md) |
| omnivoice.cpp | русская озвучка с клоном голоса на GPU | **попробовать** | [omnivoice-cpp.md](omnivoice-cpp.md) |
| HyperFrames | блоки сцен, навыки, захват кадров через BeginFrame — не замена ферме | **попробовать** (по частям) | [hyperframes.md](hyperframes.md) |
| gsap-skills | точная GSAP-анимация, если ферма на GSAP | **попробовать** | [gsap-skills.md](gsap-skills.md) |
| Video2X | апскейл и интерполяция кадров на Vulkan | **попробовать** | [video2x.md](video2x.md) |
| ACE-Step 1.5 | фоновая музыка, режим «≤4 ГБ» | **попробовать** | [ace-step-1-5.md](ace-step-1-5.md) |
| stable-diffusion.cpp | обложки и фоны без PyTorch | **попробовать** | [stable-diffusion-cpp.md](stable-diffusion-cpp.md) |
| GigaAM v3 | точное распознавание русского, если Whisper не устроит | позже | [gigaam.md](gigaam.md) |
| Orkas-VideoStudio | монтаж поверх HyperFrames — пересекается с фермой | позже (идеи) | [orkas-videostudio.md](orkas-videostudio.md) |
| ESpeech-TTS-1 | качественный русский с клоном (F5-TTS) | **попробовать** (запасной) | [espeech-tts.md](espeech-tts.md) |
| qwentts.cpp | озвучка на GPU, Pascal поддержан официально; русский слабее | позже (запасной) | [qwentts-cpp.md](qwentts-cpp.md) |
| Remotion | то же, что HyperFrames, на React | позже (запасной) | [remotion.md](remotion.md) |
| digitalsamba video toolkit | навык записи браузера, список открытых моделей | позже (по частям) | [digitalsamba-video-toolkit.md](digitalsamba-video-toolkit.md) |
| Manim | объясняющие вставки: схемы, формулы | позже | [manim.md](manim.md) |
| ArcReel | конвейер «сценарий → ИИ-видео» | позже | [arcreel.md](arcreel.md) |
| Blender Lab MCP | 3D-анимация через Blender | позже | [blender-lab-mcp.md](blender-lab-mcp.md) |
| Claude-Code-Video-Toolkit | список ссылок (разобран) | источник | [claude-code-video-toolkit.md](claude-code-video-toolkit.md) |
| awesome-motion-design-agent-skills | список ссылок (разобран) + 5 слабых навыков | навыки отклонены | [awesome-motion-design-agent-skills.md](awesome-motion-design-agent-skills.md) |
| whisper.cpp на CUDA 12 | субтитры на видеокарте | не нужно — Whisper large-v3 уже работает | [whisper-cpp-cuda.md](whisper-cpp-cuda.md) |
| everything-claude-code (ECC) | сборка для разработки программ | отклонено | [everything-claude-code.md](everything-claude-code.md) |

## Музыка и звук (2026-10-27)

Собранный пакет навыков — [`packs/music-studio`](../packs/music-studio/README.md);
исследование — `research/2026-10-27-audio-production.md`.

| Находка | Для чего | Статус | Карточка |
|---|---|---|---|
| music-studio (свой пакет) | запись вокала, сведение под минусовку, мастеринг, замеры, Ableton | **взять** | [packs/music-studio](../packs/music-studio/README.md) |
| Producer Pal | MCP для Ableton Live 12.3+ Suite (Max for Live) | **попробовать** | [producer-pal.md](producer-pal.md) |
| LiveBridge | MCP для Ableton с упором на сведение и мастеринг | **попробовать** (осторожно) | [livebridge.md](livebridge.md) |
| python-audio-separator | стемы и вокал, модели с GitHub | **попробовать** | [audio-separator.md](audio-separator.md) |
| Matchering 2.0 | мастеринг по референсу | **попробовать** | [matchering.md](matchering.md) |
| Pedalboard | обработка кодом с плагинами владельца | **попробовать** | [pedalboard.md](pedalboard.md) |
| ACE-Step 1.5 | наброски песен (MLX на маке), фоновая музыка | **попробовать** | [ace-step-1-5.md](ace-step-1-5.md) |

Без карточек (подробности в исследовании):
- **Позже:** wstierhout/ableton-live-mcp (без выполнения кода), REAPER MCP
  (`bonfire-systems/reaper-mcp`, `xDarkzx/Reaper-MCP` — если DAW будет
  REAPER), Audacity-MCP, audio-analyzer-rs, demucs-mlx, whisperX (русские
  таймкоды), MuScriptor/SOME/basic-pitch (аудио → MIDI), librosa, Essentia,
  beat_this, Magenta RealTime 2.
- **Отклонено:** Audition + MCP (нет официального, мосты требуют отключить
  проверку подписи CEP; купить из России нельзя); ahujasid/ableton-mcp
  (телеметрия по умолчанию); Simon-Kansara (заброшен); LivePilot (BSL,
  внешние вызовы); ElevenLabs MCP (архив, недоступен из России); YuE2,
  SongGeneration v2 (не для этого железа); ITO-Master, Diff-MST
  (исследовательский уровень).

## Из пакета для фабрики 2026-10-26, без карточек

Схема «живописный 2.5D» под 4 ГБ — `handoff/2026-10-26-clip-factory-4gb.md`.
Все — **попробовать в первом тесте пакета**:

- **EbSynth** (общественное достояние, CPU/CUDA) и **Ezsynth** (AGPL, для
  видео) — перенос стиля с ключевых кадров на всю последовательность.
- **Depth Anything V2 Small** (Apache-2.0) — карты глубины для параллакса.
- **IP-Adapter FaceID для SD 1.5** — сохранение лица при стилизации фото.
- **ControlNet для SD 1.5** + LCM/Hyper-LoRA — композиция из фермы, 4–6 шагов.
- **LivePortrait** — мимика портрета по видео, на маке (Apple Silicon).

## Из исследования 2026-10-26, без карточек

Подробности и источники — `research/2026-10-26-local-voice-and-video.md`;
переезд на Ubuntu — `research/2026-10-26-ubuntu-gpu-setup.md`.

- **Позже:** Speaches + Piper (запасная озвучка на CPU), Chatterbox
  Multilingual (на грани 4 ГБ, водяной знак), rembg, Robust Video Matting,
  DeepFilterNet и audio-separator (очистка голоса), Applio/RVC (единый
  голос диктора), MuseTalk 1.5 (говорящая голова — может не влезть),
  AnimateDiff и LTX-Video 2B через ComfyUI cu126 (ИИ-анимация, медленно),
  аренда RunPod для видеомоделей.
- **Позже, с некоммерческими весами** (допустимы, пока ролики не
  монетизируются): XTTS-v2 и русские доработки F5-TTS (озвучка с клоном),
  Fish Speech S1-mini, MusicGen small (музыка), **Wav2Lip** (самый лёгкий
  липсинк), RMBG-2.0 и MatAnyone (удаление фона).
- **Не для этой видеокарты:** Wan 2.2, LTX-2.x, HunyuanVideo 1.5, FramePack,
  CogVideoX, SVD, LocalAI, VoxCPM2, Zonos, Dia, Orpheus, LatentSync,
  EchoMimic, YuE, MMAudio.

## Остальное из подборки по анимации (2026-10-26), без карточек

- **GSAP, Motion, anime.js, Lottie, Three.js** — библиотеки, которые
  используются *внутри* HyperFrames/Remotion. Отдельно не ставить.
- **Motion Canvas** — пересекается с HyperFrames/Remotion. Отклонено.
- **pixel2motion** (`nolangz/pixel2motion`) — навык: растровый логотип →
  анимированный SVG. Может пригодиться для заставок. Позже, не проверено.
- **stickman-video-director** — ролики со стикменами для «безликих» каналов.
  Позже, если понадобится такой формат.
- **Graphite, Friction, Aseprite** — программы для ручной работы, не для
  конвейера. Отклонено для фабрики.
- **oil-motion** — анимации для сайтов. Отклонено: фабрика не делает сайты.

## Очередь на проверку

Пусто.

## Пробелы

1. **Потолок фермы — живописные персонажи, узнаваемое лицо, живописная
   среда** (клип «Город пробок»). Главный открытый пробел. Предложена
   упрощённая схема под 4 ГБ — «живописный 2.5D» (пакет
   `handoff/2026-10-26-clip-factory-4gb.md`), ждёт теста на ферме. Если
   качества не хватит: генерация на маке (медленно),
   генерация через сервисы (без монетизации допустимы бесплатные тарифы —
   проверить водяные знаки и сохранение лица), аренда GPU (проверить
   способы оплаты), апгрейд видеокарты (RTX 3060 12 ГБ — лучшее
   соотношение).
2. ~~Запись экрана~~ — закрыто: Playwright MCP + навык `playwright-recording`.
3. ~~Субтитры~~ — уже есть на фабрике: Whisper large-v3 на видеокарте.
4. ~~Локальная озвучка~~ — найдено: Silero (основная), omnivoice.cpp (клон
   голоса). Осталось проверить на сервере.
