# Локальная озвучка, субтитры и ИИ-видео на GTX 1050 Ti (4 ГБ)

Исследование 2026-10-26. Четыре параллельных разбора (модели озвучки; серверы
озвучки и распознавание речи; генерация видео и картинок; вспомогательные
инструменты) плюс ручная перепроверка ключевых фактов.

**Ничего не устанавливалось и не запускалось.** Ни для одного инструмента нет
замеров на GTX 1050 Ti — всё про скорость ниже либо взято из чужих отчётов на
похожих картах, либо является оценкой.

Метки: **[стр]** — прочитано на странице или в коде 2026-10-26;
**[поиск]** — только из поисковой выдачи; **[память]** — не перепроверено;
**[оценка]** — расчёт, а не замер. Hugging Face, Reddit и Habr из песочницы не
открывались, поэтому лицензии весов с Hugging Face — в основном [поиск].

## Коротко

- **Карта тянет:** озвучку (C++/GGML-серверы на GPU, Silero на CPU),
  субтитры (whisper.cpp на CUDA 12, Parakeet, GigaAM), апскейл и интерполяцию
  кадров (ncnn/Vulkan), удаление фона, очистку голоса, картинки SD1.5
  (~30 с), короткие анимационные петли AnimateDiff, музыку ACE-Step 1.5
  (режим «≤4 ГБ» заявлен авторами).
- **Не тянет:** современные видеомодели — Wan 2.2, LTX-2.x, HunyuanVideo 1.5,
  FramePack: часы на клип или нехватка памяти. Ни одного отчёта о запуске
  видеомоделей на 10-й серии с 4 ГБ не найдено.
- **Платформа заканчивается:** PyTorch 2.14 — последний с поддержкой Pascal,
  драйверы ветки 580 — последние. Предпочитать инструменты **без PyTorch**
  (C++/GGML, ncnn/Vulkan, ONNX) — они переживут это ограничение.
- **ИИ-видео** — в аренду (RTX 4090 ≈ $0,34–0,89/ч, центы за клип) или после
  апгрейда (RTX 3060 12 ГБ б/у ≈ $290–320 + ОЗУ от 32 ГБ + блок питания с
  PCIe-разъёмом).

## Уточнение после ответов владельца (2026-10-26)

Ролики **не монетизируются**, озвучка **на русском**, на сервере **16 ГБ ОЗУ
и Windows**, планируется переезд на Ubuntu. Что это меняет:

- **Озвучка: Silero v5 (`v5_ru`) становится основной.** Её лицензия CC-NC-BY
  для некоммерческих роликов подходит, а по качеству русского это лучший
  вариант на CPU. omnivoice.cpp остаётся для клонирования постоянного голоса
  диктора — сравнить с Silero на слух. qwentts.cpp отходит на третье место
  (русский слабее). Спор о лицензии весов OmniVoice больше не важен.
- **Снимаются лицензионные запреты** (некоммерческие веса теперь допустимы):
  XTTS-v2 (CPML) и русские доработки F5-TTS (CC-BY-NC) — запасные варианты с
  клонированием; Fish Speech S1-mini (CC-BY-NC-SA); MusicGen small (музыка,
  CC-BY-NC); **Wav2Lip** — самый лёгкий липсинк для говорящей головы;
  RMBG-2.0 (модель по умолчанию в rembg) и MatAnyone — удаление фона;
  модели InsightFace в LivePortrait. Ограничения по видеопамяти при этом
  остаются те же.
- **Не снимается:** водяной знак Chatterbox (не лицензия, а встроенная
  метка) и все ограничения видеокарты.
- **16 ГБ ОЗУ:** хватает для рекомендованного набора; тесно для SDXL с hires
  fix и для разгрузки больших моделей — ещё один довод против локального
  ИИ-видео. Апгрейд до 32 ГБ полезен, но не срочен.
- **Windows сейчас, Ubuntu потом:** на Ubuntu нужен проприетарный драйвер
  580, и нет подкачки видеопамяти в ОЗУ — то, что «влезало» на Windows, на
  Linux может падать. Подробно: `research/2026-10-26-ubuntu-gpu-setup.md`.

Пометки «лицензия!» и «отклонено (лицензия)» ниже относятся к коммерческому
использованию — если монетизация начнётся, они снова в силе.

## 1. Платформа

| Что | Факт |
|---|---|
| PyTorch | Сборки под CUDA 12.8/12.9 убрали Pascal начиная с 2.8; CUDA 13 Pascal не поддерживает. Работают только сборки **cu126** (и старше). PyTorch 2.15 прекращает выпуск cu126 — **Pascal остаётся на ≤2.14** [стр: pytorch issue #190385; поиск: dev-discuss]. Стандартный `pip install torch` с 2.11 ставит CUDA 13 — на этой карте не заработает [поиск]. |
| Драйвер | Ветка 580 — последняя для Pascal; с 590 — только legacy [поиск: Phoronix, NVIDIA]. |
| Точность | Нет тензорных ядер и bf16, FP16 на GP107 не ускоряется → всё в FP32 или int8. Модели, рассчитанные на bf16/FlashAttention, в FP32 занимают примерно вдвое больше памяти [память]. |
| int8 | CTranslate2 (faster-whisper) на CC 6.1 считает int8 как `int8_float32`; float16 откатывается в float32 [стр]. ggml использует int8-инструкции DP4A на sm_61 [память]. |
| ComfyUI | Нужна отдельная портативная сборка `…nvidia_cu126` («10 series and older»); основная — CUDA 13 [стр]. Пользовательские узлы могут молча обновить torch и сломать установку [поиск]. Новый менеджер памяти comfy-aimdo требует torch 2.8+ и CUDA 12.8+ — вероятно, недоступен [стр + вывод]. |
| Docker | Брать образы под **CUDA 12** (`:cuda12`, `cuda-12.6`), не `:cuda13` и не официальный `whisper.cpp:main-cuda` (CUDA 13, архитектуры от 75) [стр]. |
| ОЗУ | Для всего тяжелее SD1.5/SDXL системная память решает больше, чем видеопамять: планировать от 32 ГБ [стр: Wan2GP #1612]. |
| ОС | На Linux драйвер не выгружает видеопамять в ОЗУ — нехватка = падение; на Windows медленно, но работает [поиск]. ОС сервера пока неизвестна. |

**Правило:** никогда не ставить torch строкой из README как есть. Закреплять
`torch<=2.14` из индекса cu126.

## 2. Озвучка

### Как Orkas-VideoStudio вызывает озвучку [стр: `speech.ts`]

- `POST ${OVS_TTS_BASE_URL}/audio/speech` → адрес должен **заканчиваться на `/v1`**.
- `OVS_TTS_API_KEY` должен быть непустым (подойдёт любое значение).
- По умолчанию модель `tts-1`, голос `alloy`, формат `mp3`.
- **Язык серверу не передаётся** — его задают при запуске сервера.
- **Таймаут 60 с на запрос** — длинные абзацы резать на короткие фрагменты.

### Рекомендация

**GPU — два сервера одного автора с одинаковым API** (`/v1/audio/speech`,
регистрация клонированных голосов через `/v1/audio/voices`, вывод только
`wav`/`pcm`). Их можно сравнить, просто подменяя контейнер:

1. **omnivoice.cpp** — C++/GGML-порт OmniVoice (Xiaomi / k2-fsa): 20 338 часов
   русской речи в обучении [стр: languages.md], клонирование голоса по 3–10 с
   образца. MIT; веса по странице порта — Apache-2.0 [стр], но в других
   источниках встречается CC-BY-NC [поиск] — проверить на Hugging Face.
   Поддержка Pascal на странице не названа; код общий с qwentts.cpp — вероятно,
   та же сборка, проверить. Карточка: `finds/omnivoice-cpp.md`.
2. **qwentts.cpp** — C++/GGML-порт Qwen3-TTS. Образ `:cuda12` **прямо собран под
   Pascal (sm_61)** [стр: docs/DOCKER.md, CMakeLists.txt]. MIT, веса Qwen3-TTS —
   Apache-2.0. Русский есть, но готовых русских голосов нет — нужно
   клонировать; по отзывам русский у Qwen3-TTS слабее Silero и ESpeech [поиск].
   Карточка: `finds/qwentts-cpp.md`.

**CPU — Silero TTS v5:** по отзывам лучший локальный русский, быстрый на CPU,
ударения и омографы. **Основные модели (`v5_ru`) — CC-NC-BY,
некоммерческие** [стр]; базовые `v5_cis_base` — MIT, с отдельным MIT-пакетом
ударений `silero-stress` [стр]. Готового OpenAI-совместимого сервера нет.
Карточка: `finds/silero-tts.md`.

**Качество и клонирование офлайн — ESpeech-TTS-1** (русская доработка F5-TTS):
по обзорам «отличное» качество [поиск]; лицензия вариант SFT-256K отмечена как
Apache-2.0 [поиск], у других русских доработок F5 — CC-BY-NC. Требует PyTorch
(cu126). Карточка: `finds/espeech-tts.md`.

**Запасной на CPU — Speaches + Piper:** готовый OpenAI-совместимый сервер
(MIT, образы CPU и CUDA 12.6) с русскими голосами Piper (irina, denis, dmitri,
ruslan, среднее качество). Модель указывать явно — алиас `tts-1` ведёт на
Kokoro, а у Kokoro нет русского [стр]. Speaches без коммитов с 2026-04 [стр].

### Все проверенные модели и серверы

| Кандидат | Русский | Клон | Лицензия код / веса | 4 ГБ Pascal / CPU | Вывод |
|---|---|---|---|---|---|
| omnivoice.cpp (OmniVoice) | да, 20k ч | да | MIT / Apache? (спор) | GGML, CUDA/Vulkan/CPU; Pascal — проверить | **попробовать** |
| qwentts.cpp (Qwen3-TTS) | да, слабее | да | MIT / Apache | `:cuda12` — sm_61 ✓ | **попробовать** |
| Silero v5 | лучший по отзывам | нет | MIT / CC-NC-BY; cis_base MIT | CPU быстро | **взять** (некоммерч. — ок) |
| ESpeech-TTS-1 (F5) | да, «отлично» | да | MIT / Apache? (поиск) | вероятно влезает; скорость неизвестна | попробовать (после) |
| Speaches + Piper | 4 голоса, среднее | нет | MIT / GPL, голоса разные | CPU | запасной |
| Chatterbox Multilingual | да | да | MIT / MIT | 3,5–4,1 ГБ — на грани; **водяной знак** в каждом выводе | позже |
| XTTS-v2 | да | да | MPL / **CPML, некоммерч.** | 2–4 ГБ | позже (некоммерч. — ок) |
| F5-TTS (база), Fish S1-mini | да | да | веса CC-BY-NC / NC-SA | — | позже (некоммерч. — ок) |
| Qwen3-TTS через PyTorch | да | да | Apache | FP32 > 4 ГБ | — (брать qwentts.cpp) |
| Kokoro (+ Kokoro-FastAPI) | **нет** (есть любительский kokoro-ru) | нет | Apache | CPU быстро | только английский |
| VibeVoice | нет | — | код TTS удалён в 2025-09 | — | отклонено |
| IndexTTS-2, Higgs Audio, Orpheus, Zonos, Dia, Spark, Kani, VoxCPM2 | нет / не указан / велики | — | разные | 6–12+ ГБ или нет русского | отклонено |
| RHVoice, Vosk-TTS, TeraTTS | да, проще | нет | GPL / Apache / MIT | CPU | позже (если нужен лёгкий) |
| LocalAI | через Piper/Qwen3 | — | MIT | CUDA-сборка от sm_75 | отклонено (тяжёлый) |
| openedai-speech, AllTalk, xtts-api-server | — | — | AGPL / заброшены | — | отклонено |

### Пример настройки Orkas (адрес — свой, в репозиторий не записывать)

```
OVS_TTS_BASE_URL=http://<сервер>:8080/v1
OVS_TTS_API_KEY=local
OVS_TTS_MODEL=<алиас модели, заданный при запуске>
OVS_TTS_VOICE=<имя клонированного голоса>
OVS_TTS_FORMAT=wav
```

## 3. Субтитры и распознавание речи

- **HyperFrames по умолчанию собирает whisper.cpp только для CPU** и берёт
  модель `small.en` [стр: `whisper/manager.ts`]. Для GPU: собрать whisper.cpp с
  `-DGGML_CUDA=1` на CUDA 12.x (архитектура 61 добавляется автоматически при
  CUDA < 13) и указать путь в `HYPERFRAMES_WHISPER_PATH` [стр]. На Windows
  официальные сборки whisper.cpp — CUDA 12.4 и 11.8 [стр].
- **Модель:** large-v3 (~3,9 ГБ) на 4 ГБ впритык; брать **large-v3-turbo**
  (квантованную q5_0/q8_0) или medium (~2,1 ГБ) [стр/память]. Сравнения по
  русскому между ними не найдено — сделать короткий A/B на своей записи.
- **Parakeet TDT 0.6B v3** уже встроен в HyperFrames: CPU, int8, русский,
  тайминги слов; ставится `hyperframes models install parakeet` [стр].
  Качество на русском не проверено.
- **GigaAM v3 (Сбер)** — MIT, по замерам авторов выигрывает у Whisper large-v3
  в 70% сравнений на русском; тайминги слов с 2026-04; за один вызов ≤25 с,
  длиннее — нужна нарезка; интеграции с HyperFrames нет [стр].
- faster-whisper — int8 работает на этой карте; WhisperX закреплён на torch
  cu128 — без переделки не пойдёт [стр].

## 4. ИИ-видео и картинки

| Модель | Вердикт для 1050 Ti |
|---|---|
| SD1.5 (+ LCM/Hyper) | **работает:** 1,5–1,7 с/шаг [стр, замер на 1050 Ti] → ~30 с, ~10 с в 4–6 шагов [оценка] |
| SDXL (+ Lightning/DMD2) | работает медленно: ~3–4 мин, ~1 мин на быстрых LoRA [оценка; замер 9–10 мин с hires fix] |
| FLUX.2 klein 4B (GGUF Q4) | вероятно работает: ~1–4 мин [оценка]. Лучший современный кандидат для картинок |
| Z-Image-Turbo, FLUX.1 | медленно: 5–15+ мин [оценка] |
| AnimateDiff + AnimateLCM | **работает:** петля 16 кадров ~2–5 мин [оценка] — единственный реальный путь ИИ-анимации |
| LTX-Video 2B 0.9.8 (GGUF) | работает, но медленно: ~5–15 мин на 4 с 768×512 [оценка]; качество слабое |
| Wan 2.1 1.3B | 2–4 ч на клип; с дистиллятом 4–8 шагов при 512×288 — ~3–10 мин [оценка, не подтверждено] |
| CogVideoX-2B | влезает, но 2–3 ч на клип [оценка] |
| Wan 2.2 5B/14B, LTX-2.x (22B), HunyuanVideo 1.5, FramePack, SVD | **не работает** |

**Инструменты:**
- **stable-diffusion.cpp** — без PyTorch: CUDA, Vulkan, CPU; GGUF; поддерживает
  SD1.5/SDXL/FLUX, Wan 2.1/2.2, LTX; разгрузка в ОЗУ и тайлинг VAE [стр].
  Переживёт уход PyTorch с Pascal. **Пробовать первым.** Карточка:
  `finds/stable-diffusion-cpp.md`.
- ComfyUI (сборка cu126) с флагами `--lowvram`, `--force-fp32` (SD1.5),
  `--use-split-cross-attention` (SDXL/FLUX) [стр]; GGUF-узлы для DiT-моделей.

**Аренда для видео:** RunPod RTX 4090 $0,34/ч (Community) – $0,89/ч (Secure);
Vast.ai ~$0,40/ч; Modal L40S ~$1,95/ч [поиск]. Wan 1.3B — ~4 мин на 5 с 480p
на 4090 [стр]. Деньги уходят не на генерацию, а на запуск пода и загрузку
моделей — держать модели на сетевом томе.

**Апгрейд (США, октябрь 2026, цены нестабильны) [поиск]:**

| Карта | Цена | Что открывает |
|---|---|---|
| RTX 3060 12 ГБ | б/у ~$290–320 | bf16 и тензорные ядра; Wan 1.3B за минуты, Wan 2.2 5B с разгрузкой. **Лучшее соотношение** |
| RTX 5060 Ti 16 ГБ | MSRP $429 | лучшая новая карта для этого; FP4/FP8 |
| RTX 4060 Ti 16 ГБ | б/у ~$470 | FP8; Wan 14B в GGUF |
| RTX 3090 24 ГБ | б/у ~$1 400–1 550 | Wan 14B, LTX-2 в fp8; дорого |

1050 Ti питается только от слота (75 Вт): для любой из этих карт нужен блок
питания с PCIe-разъёмами (≈170 Вт на 3060, 350 Вт на 3090) [память] и ОЗУ от
32 ГБ.

## 5. Вспомогательные инструменты

| Задача | Выбор для этой карты | Оговорки |
|---|---|---|
| Апскейл видео | **Video2X 6.x** (CLI, Vulkan; Real-ESRGAN, Real-CUGAN, RIFE внутри) | AGPL-3 — для внутреннего использования нормально |
| Апскейл картинок | realesrgan-/realcugan-ncnn-vulkan (MIT) | записи экрана лучше сразу снимать в нужном разрешении |
| Интерполяция кадров | rife-ncnn-vulkan (MIT) или RIFE внутри Video2X | сглаживает AnimateDiff и анимацию |
| Удаление фона, картинки | **rembg** (MIT, CLI + сервер, CPU/CUDA) | модель по умолчанию `bria-rmbg` **платная для коммерции** — всегда указывать `-m birefnet-general-lite` или `isnet-general-use` |
| Удаление фона, видео | Robust Video Matting (GPL-3) — ~30 fps HD [оценка по 1080 Ti] | не обновлялся с 2023 |
| Музыка | **ACE-Step 1.5** (MIT): режим «≤4 ГБ» — только DiT, INT8, разгрузка на CPU, до 6 мин [стр]; REST API | заявление авторов, скорость неизвестна, лицензия весов не проверена |
| Звуки, короткие петли | Stable Audio Open Small (CPU) | только английские промпты; лицензия Community, бесплатно до $1 млн выручки [поиск] |
| Очистка голоса | DeepFilterNet (CPU, Rust, без Python); audio-separator (модели UVR) | DeepFilterNet принимает только 48 кГц |
| Единый голос диктора | Applio / RVC (MIT): обучить голос один раз на ~10 мин чистой речи | скорость обучения на 4 ГБ неизвестна |
| Говорящая голова | MuseTalk 1.5 (MIT, веса для коммерции) — 8 с клипа ~5 мин на 4 ГБ RTX 3050 Ti в FP16 | на Pascal может не влезть в FP32 — самая слабая категория |

**Некоммерческие веса** (для фабрики сейчас допустимы, при монетизации — нет):
MusicGen и MMAudio (CC-BY-NC), Wav2Lip (коммерция запрещена), RMBG-2.0
(CC BY-NC), MatAnyone (S-Lab), модели InsightFace в LivePortrait, YuE (NC).
Из них по видеопамяти реальны MusicGen small, Wav2Lip и RMBG-2.0; MMAudio и
YuE не влезают. Chatterbox ставит водяной знак Perth на каждый вывод.

## 6. План проверок на сервере

1. Выяснить ОС, процессор, объём ОЗУ, версию драйвера (`nvidia-smi`).
2. Озвучка, A/B на одном русском абзаце: Silero `v5_ru` на CPU,
   omnivoice.cpp `:cuda12` (с клоном голоса), при желании qwentts.cpp.
   Замерить скорость, оценить на слух, проверить укладывание в таймаут Orkas
   (60 с). Для Silero понадобится обёртка с `/v1/audio/speech`.
3. Субтитры: whisper.cpp с CUDA 12 — large-v3-turbo против medium против
   Parakeet на одной записи.
4. Video2X: апскейл и RIFE на готовом рендере HyperFrames.
5. stable-diffusion.cpp: время картинки SD1.5 и FLUX.2 klein Q4.
6. ACE-Step 1.5 в режиме «≤4 ГБ»: один трек на 30 с.

## Источники

Основные страницы, прочитанные 2026-10-26:

- Платформа: [pytorch #190385](https://github.com/pytorch/pytorch/issues/190385),
  [PyTorch releases](https://github.com/pytorch/pytorch/releases),
  [ComfyUI](https://github.com/comfyanonymous/ComfyUI) и
  [обсуждение #4604](https://github.com/comfyanonymous/ComfyUI/discussions/4604),
  [CTranslate2 quantization](https://github.com/OpenNMT/CTranslate2),
  [Wan2GP #1612](https://github.com/deepbeepmeep/WanGP/issues/1612),
  [Phoronix: 580 — последний](https://www.phoronix.com/news/NVIDIA-580-Linux-Driver-Last-HW)
- Озвучка: [omnivoice.cpp](https://github.com/ServeurpersoCom/omnivoice.cpp),
  [qwentts.cpp](https://github.com/ServeurpersoCom/qwentts.cpp),
  [OmniVoice](https://github.com/k2-fsa/OmniVoice),
  [Qwen3-TTS](https://github.com/QwenLM/Qwen3-TTS),
  [silero-models](https://github.com/snakers4/silero-models),
  [silero-stress](https://github.com/snakers4/silero-stress),
  [F5-TTS](https://github.com/SWivid/F5-TTS),
  [Chatterbox](https://github.com/resemble-ai/chatterbox),
  [Speaches](https://github.com/speaches-ai/speaches),
  [piper1-gpl](https://github.com/OHF-Voice/piper1-gpl),
  [Kokoro-FastAPI](https://github.com/remsky/Kokoro-FastAPI),
  [LocalAI](https://github.com/mudler/LocalAI),
  [Orkas-VideoStudio](https://github.com/Orkas-AI/Orkas-VideoStudio)
- Распознавание: [whisper.cpp](https://github.com/ggml-org/whisper.cpp),
  [faster-whisper](https://github.com/SYSTRAN/faster-whisper),
  [WhisperX](https://github.com/m-bain/whisperX),
  [GigaAM](https://github.com/salute-developers/GigaAM),
  [HyperFrames](https://github.com/heygen-com/hyperframes)
- Видео и картинки: [stable-diffusion.cpp](https://github.com/leejet/stable-diffusion.cpp),
  [ComfyUI-GGUF](https://github.com/city96/ComfyUI-GGUF),
  [AnimateDiff-Evolved](https://github.com/Kosinkadink/ComfyUI-AnimateDiff-Evolved),
  [LTX-Video](https://github.com/Lightricks/LTX-Video),
  [LTX-2](https://github.com/Lightricks/LTX-2),
  [Wan2.1](https://github.com/Wan-Video/Wan2.1),
  [Wan2.2](https://github.com/Wan-Video/Wan2.2),
  [CogVideo](https://github.com/zai-org/CogVideo),
  [HunyuanVideo-1.5](https://github.com/Tencent-Hunyuan/HunyuanVideo-1.5),
  [FramePack](https://github.com/lllyasviel/FramePack),
  [FLUX.2](https://github.com/black-forest-labs/flux2),
  [Z-Image](https://github.com/Tongyi-MAI/Z-Image),
  [A1111 #8901 (замер на 1050 Ti)](https://github.com/AUTOMATIC1111/stable-diffusion-webui/issues/8901),
  [Forge #1370 (замер на 1050 Ti)](https://github.com/lllyasviel/stable-diffusion-webui-forge/discussions/1370)
- Вспомогательные: [Video2X](https://github.com/k4yt3x/video2x),
  [Real-ESRGAN-ncnn-vulkan](https://github.com/xinntao/Real-ESRGAN-ncnn-vulkan),
  [rife-ncnn-vulkan](https://github.com/nihui/rife-ncnn-vulkan),
  [rembg](https://github.com/danielgatis/rembg),
  [RobustVideoMatting](https://github.com/PeterL1n/RobustVideoMatting),
  [ACE-Step 1.5](https://github.com/ace-step/ACE-Step-1.5),
  [DeepFilterNet](https://github.com/Rikorose/DeepFilterNet),
  [audio-separator](https://github.com/nomadkaraoke/python-audio-separator),
  [Applio](https://github.com/IAHispano/Applio),
  [MuseTalk](https://github.com/TMElyralab/MuseTalk)

Только из поиска (не открывались): уведомления PyTorch на dev-discuss, цены
RunPod/Vast/Modal и б/у видеокарт, карточки моделей на Hugging Face (ESpeech,
kokoro-ru, RMBG-2.0, Stable Audio Open Small), обзор русских TTS на Habr.
