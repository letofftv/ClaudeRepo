# Видеомонтаж

Монтаж и сборка роликов, запись экрана для обучающих видео, субтитры,
озвучка роликов, апскейл и плавность. Моушн-графика и рендер сцен кодом —
в [`animation/`](../animation/README.md); музыка — в [`audio/`](../audio/README.md).

Оценка — с точки зрения фабрики (см. [`CLAUDE.md`](../CLAUDE.md)). Звёзды —
на дату находки.

## Лучшее: навыки, плагины, MCP и репозитории (2026-10-27)

**Связка, всё локально и без облака:** auto-editor (грубая резка записей
экрана → Premiere XML) → ffmpeg-skill (субтитры, громкость, экспорт) →
claude-video (Claude видит результат и проверяет его). video-use — образец
процесса после замены транскрипции на свой Whisper.

| # | Находка | Тип | Для чего | Статус |
|---|---|---|---|---|
| 1 | [ffmpeg-skill](finds/ffmpeg-skill.md) | навык + плагин + MCP | 42 инструмента: субтитры (кириллица), громкость, LUT, экспорт | **взять** |
| 2 | [claude-video](finds/claude-video.md) | плагин | агент «смотрит» видео: кадры + транскрипт | **взять** |
| 3 | [auto-editor](finds/auto-editor.md) | CLI + навыки | вырезает тишину, экспорт в Premiere/Resolve/FCP | **взять** |
| 4 | [video-use](finds/video-use.md) | навык | монтаж разговором: EDL, самопроверка склеек | **попробовать** |
| 5 | [PySceneDetect](https://github.com/Breakthrough/PySceneDetect) | CLI | нарезка по сценам на CPU (BSD-3) | **попробовать** (если не хватит ffmpeg-skill) |
| 6 | [Premiere MCP (hetpatel-11)](https://github.com/hetpatel-11/Adobe_Premiere_Pro_MCP) | MCP | управление Premiere; телеметрия по умолчанию — `PREMIERE_MCP_TELEMETRY=0` | **попробовать**, если есть легальный Premiere |
| 7 | [davinci-resolve-mcp](https://github.com/samuelgursky/davinci-resolve-mcp) | MCP | самый зрелый MCP монтажки; в Resolve 21.1 скриптинг только в Studio | позже |
| 8 | [fcp-mcp-server](https://github.com/DareDev256/fcp-mcp-server) | MCP | FCPXML без Final Cut, монтаж под музыку | позже |
| 9 | [kinocut](https://github.com/KyaniteLabs/kinocut) | MCP + CLI | дублирует ffmpeg-skill, моложе | позже |
| 10 | [OpenMontage](https://github.com/calesthio/OpenMontage) | фреймворк | огромный (700+ навыков), AGPL — только как источник приёмов | позже |
| 11 | [LosslessCut](https://github.com/mifi/lossless-cut) | GUI + CLI + HTTP API | резка без перекодирования | позже |
| 12 | [obs-studio-mcp](https://github.com/aaronckj/obs-studio-mcp) | MCP | запись экрана через OBS, `dry_run` у изменяющих | позже |
| 13 | [shotcut-mcp](https://github.com/matrodrigs/shotcut-mcp) | MCP | правка проектов MLT | позже |

**Отклонено:** Youtube-clipper-skill (под YouTube и китайский перевод,
дублирует линию нарезки), коннектор Adobe «for creativity» (облачный, не
управляет локальными проектами), pyJianYingDraft / VectCutAPI (только
JianYing на Windows), mcp-kdenlive (без лицензии, нужен патченный Kdenlive),
MoviePy и editly (дублируют ферму), heygen-com/skills (облачные аватары,
платно), мелкие дубли auto-editor и ffmpeg-skill, royshil/obs-mcp (заброшен).

## Что добавить к своей ферме

Ядро уже есть: своя ферма (сцены кодом → кадры в Chromium → ffmpeg), Whisper
(faster-whisper large-v3-turbo) на видеокарте, сетка долей, маски Apple Vision.

1. **Playwright MCP** — запись настоящих интерфейсов с анимированным курсором
   для обучающих роликов.
2. **Озвучка** — **Silero** на процессоре (основная, русский) или
   **omnivoice.cpp** на видеокарте, если нужен клон постоянного голоса.
3. **Video2X** — апскейл и плавность кадров на Vulkan, после переезда на
   Ubuntu: в WSL на сервере Vulkan не работает.

## Находки

| Находка | Для чего | Статус | Карточка |
|---|---|---|---|
| ffmpeg-skill | субтитры, громкость, LUT, экспорт поверх ffmpeg | **взять** | [ffmpeg-skill.md](finds/ffmpeg-skill.md) |
| claude-video | агент «смотрит» рендеры и референсы | **взять** | [claude-video.md](finds/claude-video.md) |
| auto-editor | вырезает тишину, экспорт таймлайна в Premiere XML | **взять** | [auto-editor.md](finds/auto-editor.md) |
| video-use | образец монтажа разговором (транскрипцию заменить) | **попробовать** | [video-use.md](finds/video-use.md) |
| Silero TTS v5 | основная русская озвучка, на CPU | **взять** | [silero-tts.md](finds/silero-tts.md) |
| Playwright MCP (видео) | запись настоящих интерфейсов с курсором | **попробовать** | [playwright-mcp-video.md](finds/playwright-mcp-video.md) |
| omnivoice.cpp | русская озвучка с клоном голоса на GPU | **попробовать** | [omnivoice-cpp.md](finds/omnivoice-cpp.md) |
| Video2X | апскейл и интерполяция кадров на Vulkan | позже (после переезда на Ubuntu: в WSL нет Vulkan) | [video2x.md](finds/video2x.md) |
| Piper | черновая русская озвучка на CPU без сервера; в пульте — `tts_piper`, 18 с речи за 3,4 с | **взять** (черновики) | [piper.md](finds/piper.md) |
| ESpeech-TTS-1 | качественный русский с клоном (F5-TTS) | **попробовать** (запасной) | [espeech-tts.md](finds/espeech-tts.md) |
| GigaAM v3 | точное распознавание русского, если Whisper не устроит | позже | [gigaam.md](finds/gigaam.md) |
| Orkas-VideoStudio | монтаж поверх HyperFrames — пересекается с фермой | позже (идеи) | [orkas-videostudio.md](finds/orkas-videostudio.md) |
| qwentts.cpp | озвучка на GPU, Pascal поддержан официально; русский слабее | позже (запасной) | [qwentts-cpp.md](finds/qwentts-cpp.md) |
| digitalsamba video toolkit | навык записи браузера, список открытых моделей | позже (по частям) | [digitalsamba-video-toolkit.md](finds/digitalsamba-video-toolkit.md) |
| Claude-Code-Video-Toolkit | список ссылок (разобран) | источник | [claude-code-video-toolkit.md](finds/claude-code-video-toolkit.md) |
| whisper.cpp на CUDA 12 | субтитры на видеокарте | не нужно — на сервере faster-whisper large-v3-turbo (Docker), в пульт подключён обёрткой | [whisper-cpp-cuda.md](finds/whisper-cpp-cuda.md) |

**Без карточек** (подробности — в исследовании ниже):
- **Позже:** Speaches (сервер с Piper — не нужен, Piper в пульте вызывается
  напрямую), Chatterbox Multilingual (на грани 4 ГБ, водяной знак),
  DeepFilterNet (очистка голоса; audio-separator уже взят —
  [`audio/finds/audio-separator.md`](../audio/finds/audio-separator.md)), Applio/RVC (единый голос диктора),
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
