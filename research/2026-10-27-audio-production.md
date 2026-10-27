# Музыка и звук: MCP для DAW, плагины, открытые инструменты, уроки мастеров

Исследование 2026-10-27. Шесть параллельных разборов: MCP для Ableton и
других DAW; Audition и MCP; плагины и бесплатные аналоги; открытые
инструменты на GitHub; уроки мастеров сведения; уроки мастеров мастеринга.
Итог собран в пакет Claude Code [`packs/music-studio`](../packs/music-studio/README.md).

Задачи владельца: сочинение музыки, сведение, мастеринг, запись русского
вокала под готовые минусовки. Некоммерческие проекты. Вероятное рабочее
место — MacBook Pro M1 Pro 16 ГБ (не подтверждено).

Метки: **[стр]** — прочитано на странице или в коде; **[поиск]** — по
поисковой сводке; **[память]** — не перепроверено. Многие сайты (ableton.com,
adobe.com, Hugging Face, сайты вендоров плагинов, soundonsound.com) из
песочницы не открывались — версии, цены и цифры из уроков в основном
[поиск]. Ничего не устанавливалось.

## Коротко

- **Ableton + MCP — есть хорошие варианты.** Producer Pal (Live Suite /
  Max for Live) — самый зрелый; LiveBridge — для сведения и мастеринга
  (дБ, автоматизация, замер LUFS); wstierhout — без выполнения кода.
  Популярный `ahujasid/ableton-mcp` — телеметрия включена по умолчанию.
  Live API не умеет экспорт и видит ≤128 параметров стороннего плагина.
- **Audition + MCP — нет.** Официального нет (коннектор Adobe для Claude
  без Audition), любительские мосты требуют отключить проверку подписи CEP;
  Audition в режиме поддержки, купить из России нельзя.
- **REAPER** даёт агенту самый глубокий доступ (любые параметры плагинов,
  рендер, стемы) — запасной вариант, если не Ableton.
- **Плагины:** встроенные устройства Live 12 Standard + бесплатные
  (Valhalla Supermassive, TDR Nova, LALA/FETish, T-De-Esser 2, ANINA,
  Youlean, SPAN, Airwindows) закрывают вокал, сведение и мастеринг. Из
  России реально купить Voxengo (рубли) и, вероятно, Valhalla.
- **Открытые инструменты:** python-audio-separator (стемы, модели с
  GitHub), Matchering (мастеринг по референсу), Pedalboard (плагины
  владельца из кода), whisperX (русские таймкоды), ACE-Step 1.5 (наброски,
  MLX на маке).
- **Уроки мастеров** сведены в консенсусные рецепты: вокал на 2-track и
  мастеринг для стриминга (навыки пакета).

## 1. MCP для Ableton Live и других DAW

| Сервер | ★ / коммит / лицензия | Подключение, версии | Микс | Автоматизация | Анализ | Произвольный код | Замечания |
|---|---|---|---|---|---|---|---|
| **Producer Pal** | 349 / 2026-10-01 / GPL-3 | Max for Live, HTTP :3350; Live 12.3+ с M4L | да | нет | нет | выкл. по умолчанию | самый зрелый; HTTP без авторизации на всех интерфейсах — закрыть брандмауэром [стр] |
| **LiveBridge** | 11 / 2026-09-23 / MIT | Remote Script, TCP 9880 + токен; Live 12 | в дБ, шины, сайдчейн | клипы + запись в реальном времени | LUFS, спектр, тональность | `live_eval_python` вкл. — выключать `--no-allow-eval` | ставит Splice MCP (выкл. `--no-splice`) и навык в `~/.claude` [стр] |
| **wstierhout/ableton-live-mcp** | 62 / 2026-09-16 / MIT | Remote Script :9877; Live 11/12 | да + метры | клипы | тональность | нет | 156 инструментов, наборы через `ABLETON_TOOLSETS` [стр] |
| ahujasid/ableton-mcp | 3,3k / 2026-09-22 / MIT | Remote Script :9877 | нет | нет | нет | нет | **телеметрия вкл. по умолчанию** [стр] |
| bschoepke | 235 / 2026-10-05 / MIT | Remote Script + M4L | через API | огибающие | спектрограммы | `live_exec` без авторизации | [стр] |
| LivePilot | 90 / 2026-10-11 / BSL-1.1 | Remote Script + M4L | да | да | да | — | 474 инструмента, ходит в Splice и GitHub [стр] |
| Simon-Kansara | 396 / 2025-03 | AbletonOSC | — | — | — | — | заброшен, 1 инструмент [стр] |
| Extensions SDK (loophole, ulm0) | 2026 | внутри Live; Live 12.4.5 **Suite beta** | частично | нет | — | нет | официальный SDK Ableton ещё в бете [поиск] |

- **Плагины:** Live API видит только параметры из списка Configure (до
  128); Configure сохраняется в пресете рэка. LiveBridge обходит это для
  VST3 [стр].
- **Нет у всех:** экспорт, заморозка, сохранение сета.
- **Другие DAW:** REAPER — `bonfire-systems/reaper-mcp` (166★, ~60
  инструментов, рендер, мастеринг-цепь, громкость) и `xDarkzx/Reaper-MCP`
  (109★, 181 инструмент, файловый мост); Logic — `koltyj/logic-pro-mcp`
  через Accessibility, ломается на локализованном интерфейсе; Bitwig и FL
  Studio — слабые варианты [стр/поиск].

## 2. Audition и MCP

- Официального MCP нет; коннектор «Adobe for creativity» (2026-04-28) —
  без Audition [поиск]. `mikechambers/adb-mcp` — без Audition [стр].
- У Audition есть недокументированный ExtendScript только через CEP-панель;
  без участия человека — открыть файл, применить Favorite, сохранить;
  Batch Process, Match Loudness, мультитрек — через диалоги [стр].
- Мосты: Brainferno MCP Bridge (3★, проверен на Windows), Flue (98★,
  не MCP, произвольный JSX) — оба требуют `PlayerDebugMode`, отключающий
  проверку подписи у всех CEP-панелей [стр]. **Не рекомендуется.**
- Audition в режиме поддержки (26.3 — «no new editing tools») [поиск];
  Adobe не продаёт в России с 2022, корпоративные лицензии через российских
  партнёров отключены с 2026-07-07 [поиск].
- Альтернативы для агента: Audacity-MCP (`xDarkzx`, 121★, без exec/eval),
  audio-analyzer-rs (70★, только анализ: LUFS, маскировка, A/B) [стр].
  ElevenLabs MCP — архив, ElevenLabs недоступен из России [стр/поиск].

## 3. Плагины

Полная карта с бесплатными аналогами — [`packs/music-studio/references/plugin-map.md`](../packs/music-studio/references/plugin-map.md).
Главное:
- Live 12.4.5 (2026-08) актуальна; Auto Shift (коррекция высоты) — во всех
  редакциях с 12.1; Stem Separation — Suite с 12.3; ARA нет [поиск].
- Отрасль 2026: iZotope перешёл к Boris FX, Native Instruments — к inMusic;
  вышли soothe3, FabFilter Pro-C 3, RX 12 [поиск].
- Rosetta уходит — только нативные для Apple Silicon плагины; Intel-only:
  Limiter No6, TDR Kotelnikov, GSnap [поиск].
- Покупка из России: российские карты не проходят; NI не продаёт; Voxengo
  принимает рубли; серые лицензии отзывают [поиск].

## 4. Открытые инструменты

| Задача | Выбор | Лицензия | Мак | Заметки |
|---|---|---|---|---|
| Стемы и вокал | python-audio-separator | MIT, модели разные | MPS + CoreML | RoFormer-модели ~11,3 SDR вокал / ~17,5 инструментал; **модели с GitHub** [стр] |
| Быстрые 4 стема | demucs-mlx | MIT, веса Demucs «неясны» | MLX | [стр] |
| Мастеринг по референсу | Matchering 2.0 | GPL-3 | CPU | стабилен [стр] |
| Обработка кодом | Pedalboard 0.9.26 | GPL-3 | arm64 | грузит AU/VST3 владельца [стр] |
| Громкость | pyloudnorm, ffmpeg loudnorm | MIT | CPU | скрипты пакета — только ffmpeg |
| Тональность, BPM, доли | librosa 1.0, Essentia, beat_this | ISC / AGPL-3 / MIT | CPU | [стр] |
| Высота вокала | RMVPE, torchcrepe, pYIN | Apache / MIT | — | зрелого открытого автотюна нет [стр] |
| Таймкоды русского текста | whisperX | BSD-2 | CPU int8 | русская модель выравнивания на HF [стр] |
| Аудио → MIDI | MuScriptor, SOME, basic-pitch | MIT / веса NC | MPS / CoreML | [стр] |
| Наброски песен | ACE-Step 1.5 | MIT | MLX | русский в списке языков; навык транскрипции шлёт аудио в OpenAI — не ставить [стр] |

Не для этого железа: YuE2 (24 ГБ, bf16), SongGeneration v2 (22–28 ГБ);
AI-сведение (ITO-Master, Diff-MST) — исследовательский уровень, NC.

## 5. Уроки мастеров

Пересказ по каждому инженеру со ссылками —
[`packs/music-studio/references/masters-techniques.md`](../packs/music-studio/references/masters-techniques.md);
рецепты — навыки `vocal-over-beat` и `mastering`. Ключевое для владельца:
- **Пережатая минусовка:** опустить её на 6–10 дБ, плотность добирать
  вокалом (последовательная + параллельная компрессия, сатурация), место
  под вокал — сайдчейн-провал 1,5–3 дБ на 2–4 кГц, на мастере 0–2 дБ
  лимитирования (Firkins, Kesha Lee, Bainz, Weinberg).
- **Русские шипящие:** два де-эссера — узкий на «с/з/ц» (5–8 кГц) и
  широкий на «ш/щ/ч/ж» (3–5 кГц, ≤3 дБ); не пере-де-эссировать.
- **Громкость:** ~−14 LUFS / −1 dBTP для нормализующих площадок; для
  Яндекса/VK нормализация не подтверждена — компромисс −12…−10 LUFS, PSR ≥ 8.

## Что осталось неизвестным

Редакция и версия Live у владельца (от неё зависит выбор MCP), на каком
компьютере запись, аудиоинтерфейс и микрофон; официальные требования
Яндекс Музыки и VK Музыки к громкости; цифры из уроков не сверены с
оригиналами (сайты недоступны из песочницы).

## Источники (основные)

- Ableton MCP: [Producer Pal](https://github.com/adamjmurray/producer-pal),
  [LiveBridge](https://github.com/valentijnh/livebridge-ableton-mcp),
  [wstierhout](https://github.com/wstierhout/ableton-live-mcp),
  [ahujasid](https://github.com/ahujasid/ableton-mcp),
  [AbletonOSC](https://github.com/ideoforms/AbletonOSC),
  [Extensions SDK (анонс)](https://www.ableton.com/en/blog/introducing-extensions-sdk/)
- Другие DAW: [bonfire reaper-mcp](https://github.com/bonfire-systems/reaper-mcp),
  [xDarkzx Reaper-MCP](https://github.com/xDarkzx/Reaper-MCP),
  [logic-pro-mcp](https://github.com/koltyj/logic-pro-mcp)
- Audition: [adb-mcp](https://github.com/mikechambers/adb-mcp),
  [Brainferno](https://github.com/Brainferno/brainferno-mcp-bridge),
  [Flue](https://github.com/sfkislev/flue),
  [CEP-Resources](https://github.com/Adobe-CEP/CEP-Resources),
  [Audacity-MCP](https://github.com/xDarkzx/Audacity-MCP),
  [audio-analyzer-rs](https://github.com/JuzzyDee/audio-analyzer-rs)
- Открытые инструменты: [python-audio-separator](https://github.com/nomadkaraoke/python-audio-separator),
  [demucs-mlx](https://github.com/ssmall256/demucs-mlx),
  [Matchering](https://github.com/sergree/matchering),
  [Pedalboard](https://github.com/spotify/pedalboard),
  [whisperX](https://github.com/m-bain/whisperX),
  [MuScriptor](https://github.com/muscriptor/muscriptor),
  [ACE-Step 1.5](https://github.com/ace-step/ACE-Step-1.5),
  [beat_this](https://github.com/CPJKU/beat_this),
  [Essentia](https://github.com/MTG/essentia)
- Плагины и Live: [Live 12.4](https://www.ableton.com/en/blog/live-12-4-is-out-now/),
  [Live 12.3](https://musictech.com/news/music/ableton-live-12-3/),
  [Ozone 12](https://www.attackmagazine.com/news/izotope-announces-ozone-12-with-new-stem-eq-bass-control-and-unlimiter/),
  [RX 12](https://www.prosoundweb.com/izotope-unveils-new-rx-12-editing-restoration-suite/),
  [Voxengo и Россия](https://www.voxengo.com/press/on-the-current-geopolitical-events-and-more-450/),
  [оплата из России](https://dtf.ru/howto/5207359-kak-oplatit-splice)
- Громкость: [Spotify](https://support.spotify.com/au/artists/article/loudness-normalization/),
  [Production Advice: no LUFS targets](https://productionadvice.co.uk/no-lufs-targets/),
  [AES TD1008](https://productionadvice.co.uk/td1008/)
- Уроки мастеров — ссылки в `masters-techniques.md`.
