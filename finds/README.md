# Находки

Оценка — с точки зрения фабрики (см. `CLAUDE.md`). Звёзды — на дату находки.
Широкие исследования — в `research/`.

## Складывающийся конвейер (гипотеза, проверить на сервере)

Для обучающих видео по интерфейсам платформ:

1. **Playwright MCP** — агент проходит сценарий на настоящей платформе и
   записывает видео с анимированным курсором.
2. **HyperFrames** (+ **gsap-skills**) — запись в композицию: зум, выноски,
   титры, анимация. Рендер с NVENC (`--gpu`).
3. **Озвучка** — **Silero** на процессоре (основная, русский) или
   **omnivoice.cpp** на видеокарте, если нужен клон постоянного голоса.
4. **Orkas-VideoStudio** — монтаж: паузы, субтитры (**whisper.cpp на CUDA 12**),
   озвучка, громкость.
5. **SkillSpector** — перед установкой любого из навыков выше.

Промо-клипы и UI-ролики без записи экрана — **product-launch-motion**.
Музыка — **ACE-Step 1.5**, апскейл и плавность — **Video2X**, обложки —
**stable-diffusion.cpp**.

## Все находки

| Находка | Для чего на фабрике | Статус | Карточка |
|---|---|---|---|
| SkillSpector | проверка навыков перед установкой | **взять** | [skillspector.md](skillspector.md) |
| Silero TTS v5 | основная русская озвучка, на CPU | **взять** | [silero-tts.md](silero-tts.md) |
| whisper.cpp на CUDA 12 | русские субтитры на видеокарте (настройка HyperFrames) | **взять** | [whisper-cpp-cuda.md](whisper-cpp-cuda.md) |
| HyperFrames | анимация, клипы, обучающие видео; рендер HTML → MP4 | **попробовать** (первым) | [hyperframes.md](hyperframes.md) |
| Playwright MCP (видео) | запись настоящих интерфейсов с курсором | **попробовать** | [playwright-mcp-video.md](playwright-mcp-video.md) |
| gsap-skills | точная GSAP-анимация внутри HyperFrames | **попробовать** (с HyperFrames) | [gsap-skills.md](gsap-skills.md) |
| omnivoice.cpp | русская озвучка с клоном голоса на GPU, сервер для Orkas | **попробовать** | [omnivoice-cpp.md](omnivoice-cpp.md) |
| Orkas-VideoStudio | монтаж записей, субтитры, озвучка поверх HyperFrames | **попробовать** (вторым) | [orkas-videostudio.md](orkas-videostudio.md) |
| product-launch-motion | промо и UI-ролики под музыку; v1 — под озвучку | **попробовать** | [product-launch-motion.md](product-launch-motion.md) |
| Video2X | апскейл и интерполяция кадров на Vulkan | **попробовать** | [video2x.md](video2x.md) |
| ACE-Step 1.5 | фоновая музыка, режим «≤4 ГБ» | **попробовать** | [ace-step-1-5.md](ace-step-1-5.md) |
| stable-diffusion.cpp | обложки и фоны без PyTorch | **попробовать** | [stable-diffusion-cpp.md](stable-diffusion-cpp.md) |
| GigaAM v3 | точное распознавание русского | **попробовать** | [gigaam.md](gigaam.md) |
| ESpeech-TTS-1 | качественный русский с клоном (F5-TTS) | **попробовать** (запасной) | [espeech-tts.md](espeech-tts.md) |
| qwentts.cpp | озвучка на GPU, Pascal поддержан официально; русский слабее | позже (запасной) | [qwentts-cpp.md](qwentts-cpp.md) |
| Remotion | то же, что HyperFrames, на React | позже (запасной) | [remotion.md](remotion.md) |
| digitalsamba video toolkit | навык записи браузера, список открытых моделей | позже (по частям) | [digitalsamba-video-toolkit.md](digitalsamba-video-toolkit.md) |
| Manim | объясняющие вставки: схемы, формулы | позже | [manim.md](manim.md) |
| ArcReel | конвейер «сценарий → ИИ-видео» | позже | [arcreel.md](arcreel.md) |
| Blender Lab MCP | 3D-анимация через Blender | позже | [blender-lab-mcp.md](blender-lab-mcp.md) |
| Claude-Code-Video-Toolkit | список ссылок (разобран) | источник | [claude-code-video-toolkit.md](claude-code-video-toolkit.md) |
| awesome-motion-design-agent-skills | список ссылок (разобран) + 5 слабых навыков | навыки отклонены | [awesome-motion-design-agent-skills.md](awesome-motion-design-agent-skills.md) |
| everything-claude-code (ECC) | сборка для разработки программ | отклонено | [everything-claude-code.md](everything-claude-code.md) |

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

1. ~~Запись экрана~~ — закрыто: Playwright MCP + навык `playwright-recording`.
2. ~~Субтитры~~ — закрыто: whisper.cpp на CUDA 12, GigaAM.
3. ~~Локальная озвучка~~ — найдено: Silero (основная), omnivoice.cpp (клон
   голоса). Осталось проверить на сервере и написать обёртку Silero для Orkas.
4. **Генеративное ИИ-видео** — на 4 ГБ не решается; варианты: аренда GPU или
   апгрейд видеокарты (RTX 3060 12 ГБ — лучшее соотношение).
