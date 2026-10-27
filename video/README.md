# Видеомонтаж

Монтаж и сборка роликов, запись экрана для обучающих видео, субтитры,
озвучка роликов, апскейл и плавность. Моушн-графика и рендер сцен кодом —
в [`animation/`](../animation/README.md); музыка — в [`audio/`](../audio/README.md).

Оценка — с точки зрения фабрики (см. [`CLAUDE.md`](../CLAUDE.md)). Звёзды —
на дату находки.

## Что добавить к своей ферме

Ядро уже есть: своя ферма (сцены кодом → кадры в Chromium → ffmpeg), Whisper
large-v3 на видеокарте, сетка долей, маски Apple Vision.

1. **Playwright MCP** — запись настоящих интерфейсов с анимированным курсором
   для обучающих роликов.
2. **Озвучка** — **Silero** на процессоре (основная, русский) или
   **omnivoice.cpp** на видеокарте, если нужен клон постоянного голоса.
3. **Video2X** — апскейл и плавность кадров на Vulkan.

## Находки

| Находка | Для чего | Статус | Карточка |
|---|---|---|---|
| Silero TTS v5 | основная русская озвучка, на CPU | **взять** | [silero-tts.md](finds/silero-tts.md) |
| Playwright MCP (видео) | запись настоящих интерфейсов с курсором | **попробовать** | [playwright-mcp-video.md](finds/playwright-mcp-video.md) |
| omnivoice.cpp | русская озвучка с клоном голоса на GPU | **попробовать** | [omnivoice-cpp.md](finds/omnivoice-cpp.md) |
| Video2X | апскейл и интерполяция кадров на Vulkan | **попробовать** | [video2x.md](finds/video2x.md) |
| ESpeech-TTS-1 | качественный русский с клоном (F5-TTS) | **попробовать** (запасной) | [espeech-tts.md](finds/espeech-tts.md) |
| GigaAM v3 | точное распознавание русского, если Whisper не устроит | позже | [gigaam.md](finds/gigaam.md) |
| Orkas-VideoStudio | монтаж поверх HyperFrames — пересекается с фермой | позже (идеи) | [orkas-videostudio.md](finds/orkas-videostudio.md) |
| qwentts.cpp | озвучка на GPU, Pascal поддержан официально; русский слабее | позже (запасной) | [qwentts-cpp.md](finds/qwentts-cpp.md) |
| digitalsamba video toolkit | навык записи браузера, список открытых моделей | позже (по частям) | [digitalsamba-video-toolkit.md](finds/digitalsamba-video-toolkit.md) |
| Claude-Code-Video-Toolkit | список ссылок (разобран) | источник | [claude-code-video-toolkit.md](finds/claude-code-video-toolkit.md) |
| whisper.cpp на CUDA 12 | субтитры на видеокарте | не нужно — Whisper large-v3 уже работает | [whisper-cpp-cuda.md](finds/whisper-cpp-cuda.md) |

**Без карточек** (подробности — в исследовании ниже):
- **Позже:** Speaches + Piper (запасная озвучка на CPU), Chatterbox
  Multilingual (на грани 4 ГБ, водяной знак), DeepFilterNet и
  audio-separator (очистка голоса), Applio/RVC (единый голос диктора),
  MuseTalk 1.5 (говорящая голова — может не влезть), rembg и Robust Video
  Matting (удаление фона).
- **Позже, с некоммерческими весами** (допустимы, пока ролики не
  монетизируются): XTTS-v2 и русские доработки F5-TTS, Fish Speech S1-mini,
  Wav2Lip (самый лёгкий липсинк), RMBG-2.0 и MatAnyone.
- **Не для этой видеокарты:** LocalAI, VoxCPM2, Zonos, Dia, Orpheus,
  LatentSync, EchoMimic.

## Исследования

- [Локальная озвучка, субтитры и ИИ-видео на GTX 1050 Ti](research/2026-10-26-local-voice-and-video.md)
  (2026-10-26) — раздел про ИИ-видео и картинки относится к анимации.
- Переезд сервера на Ubuntu — в [`common/`](../common/README.md).

## Пробелы

1. ~~Запись экрана~~ — Playwright MCP + навык `playwright-recording`.
2. ~~Субтитры~~ — уже есть на фабрике: Whisper large-v3 на видеокарте.
3. ~~Локальная озвучка~~ — Silero (основная), omnivoice.cpp (клон голоса);
   осталось проверить на сервере.
