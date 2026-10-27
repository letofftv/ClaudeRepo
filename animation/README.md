# Анимация и мультипликация

Моушн-графика, движки рендера сцен кодом, анимация персонажей, ИИ-картинки
и ИИ-видео, 3D, 2D-мультипликация. Монтаж, запись экрана и озвучка — в
[`video/`](../video/README.md); музыка — в [`audio/`](../audio/README.md).

Оценка — с точки зрения фабрики (см. [`CLAUDE.md`](../CLAUDE.md)). Звёзды —
на дату находки.

## Главный пробел — потолок фермы

Живописные персонажи, узнаваемое лицо и живописная среда уровня референсов
кодом не достигаются (клип «Город пробок»). Предложена упрощённая схема
под 4 ГБ видеопамяти — **«живописный 2.5D»**: ИИ делает живописные слои и
стилизует ключевые кадры, движение даёт ферма. Пакет для фабрики —
[`handoff/2026-10-26-clip-factory-4gb.md`](../handoff/2026-10-26-clip-factory-4gb.md),
ждёт теста. Если качества не хватит: генерация на маке (медленно), сервисы
с бесплатными тарифами (без монетизации допустимы; проверить водяные знаки и
сохранение лица), аренда GPU (проверить оплату), апгрейд видеокарты (RTX
3060 12 ГБ — лучшее соотношение).

## Лучшее: навыки, плагины, MCP и репозитории (2026-10-27)

Самые сильные находки 2026 года — не MCP-серверы, а наборы **«живописи
кодом»** для той же архитектуры, что у фермы (кадр = f(t) в headless Chrome +
ffmpeg). Они дают вид иллюстрированной книжки, но потолок «узнаваемое лицо»
не снимают. Реалистичная связка для «Города пробок»:
- живописные слои SD 1.5 — через **Comfy MCP** (ComfyUI на сервере);
- говорящий живописный персонаж — **mesh-avatar-studio** (+ LivePortrait);
- среда, переходы, мазки — **p5.brush** из ClaudeAnimationBase или paint-mv-skills.

| # | Находка | Тип | Для чего | Статус |
|---|---|---|---|---|
| 1 | [ClaudeAnimationBase](finds/claude-animation-base.md) | набор + гайд агента | p5.brush: акварель, мазки, персонаж с 31 эмоцией | **попробовать** |
| 2 | [paint-mv-skills](finds/paint-mv-skills.md) | 4 навыка | песня + текст → акварельный клип | **попробовать** (на фрагменте клипа) |
| 3 | [mesh-avatar-studio](finds/mesh-avatar-studio.md) | приложение + рантайм | иллюстрация → говорящий 2D-аватар, офлайн-рендер | **попробовать** |
| 4 | [lemo-opuscar](finds/lemo-opuscar.md) | библиотека стилей | 59 стилей кодом: аниме, импасто, акварель, тушь… | **попробовать** (читать, не ставить) |
| 5 | [vocaloid-style-mv-pipeline](finds/vocaloid-style-mv-pipeline.md) | конвейер | кинетическая типографика текста песни, 9:16 | **попробовать** (проверить кириллицу) |
| 6 | [Comfy MCP](finds/comfy-mcp.md) | MCP (официальный, бета) | Claude управляет ComfyUI на сервере | **попробовать** |
| 7 | [motion-design-skill (LottieFiles)](https://github.com/LottieFiles/motion-design-skill) | 1 навык | «режиссёр движения»: принципы Диснея, тайминг | **попробовать** (сравнить с product-launch-motion, оставить один) |
| 8 | [text-to-lottie](https://github.com/diffusionstudio/lottie) | навык | Lottie из текста или SVG | позже |
| 9 | [anidoodle](https://github.com/alexgreensh/anidoodle) | плагин | 32 стиля «нарисовано кодом» — дублирует lemo-opuscar | позже |
| 10 | [MCP for Blender](https://github.com/ahujasid/blender-mcp) | MCP | toon-3D; выполняет любой Python, телеметрия — выключать | позже |
| 11 | [Remotion skills](https://github.com/remotion-dev/skills) | 12 навыков | только вместе с Remotion | позже |
| 12 | [manim-skill](https://github.com/Yusuke710/manim-skill) | навык | диктор → TTS → Manim (TTS заменить на Silero) | позже |
| 13 | [an + cutan](https://github.com/reeleehq/cutan) | библиотека | перекладная анимация из scene.md, липсинк — сырой | позже |
| 14 | [pixel2motion](https://github.com/nolangz/pixel2motion) | навык | логотип → анимированный SVG для заставок | позже |
| — | [awesome-claude-video-skills](finds/awesome-claude-video-skills.md) | подборка | 362 репозитория с пометками SAFE/CAUTION | источник |

**Отклонено:** character-animation-skill (кадры через Gemini — платно,
недоступно из России), Spine-инструменты (нужна платная лицензия
редактора), After Effects MCP (Adobe не продаётся в России), Rive MCP и
Lottie Creator MCP (облако, аккаунт), Motion Canvas skill (дубль фермы),
Three.js-пакеты (3D на 4 ГБ — узкое место), animation-principles (144
навыка — тяжело), motion-skills (рекламная воронка), Math-To-Manim (платные
API), инструменты Krita/Synfig/OpenToonz (нет годных для агента),
mcp-drawthings (только txt2img/img2img; сам Draw Things стоит проверить как
хост живописи на маке), сообщественные ComfyUI MCP (архив/GUI).

## Что добавить к своей ферме

Своя ферма повторяет подход HyperFrames/Remotion (HTML → кадры → ffmpeg),
поэтому такие находки — **источник приёмов и блоков**, а не замена:
- режиссура **product-launch-motion**;
- блоки сцен и захват кадров через BeginFrame из **HyperFrames**;
- **gsap-skills**, если ферма анимирует на GSAP;
- обложки и фоны — **stable-diffusion.cpp**.

## Находки

| Находка | Для чего | Статус | Карточка |
|---|---|---|---|
| product-launch-motion | справочник режиссуры: та же техника, что у фермы | **взять** (справочник) | [product-launch-motion.md](finds/product-launch-motion.md) |
| HyperFrames | блоки сцен, навыки, захват кадров через BeginFrame — не замена ферме | **попробовать** (по частям) | [hyperframes.md](finds/hyperframes.md) |
| gsap-skills | точная GSAP-анимация, если ферма на GSAP | **попробовать** | [gsap-skills.md](finds/gsap-skills.md) |
| stable-diffusion.cpp | обложки, фоны, живописные слои без PyTorch | **попробовать** | [stable-diffusion-cpp.md](finds/stable-diffusion-cpp.md) |
| Remotion | то же, что HyperFrames, на React | позже (запасной) | [remotion.md](finds/remotion.md) |
| Manim | объясняющие вставки: схемы, формулы | позже | [manim.md](finds/manim.md) |
| ArcReel | конвейер «сценарий → ИИ-видео» | позже | [arcreel.md](finds/arcreel.md) |
| Blender Lab MCP | 3D-анимация через Blender | позже | [blender-lab-mcp.md](finds/blender-lab-mcp.md) |
| awesome-motion-design-agent-skills | список ссылок (разобран) + 5 слабых навыков | навыки отклонены | [awesome-motion-design-agent-skills.md](finds/awesome-motion-design-agent-skills.md) |

**Без карточек:**
- **Схема «живописный 2.5D»** (попробовать в первом тесте пакета): EbSynth
  и Ezsynth (перенос стиля с ключевых кадров), Depth Anything V2 Small
  (глубина для параллакса), IP-Adapter FaceID и ControlNet для SD 1.5 +
  LCM/Hyper-LoRA, LivePortrait (мимика портрета на маке).
- **ИИ-анимация на 4 ГБ, медленно:** AnimateDiff + AnimateLCM и LTX-Video 2B
  через ComfyUI (сборка cu126); аренда GPU для видеомоделей.
- **Не для этой видеокарты:** Wan 2.2, LTX-2.x, HunyuanVideo 1.5, FramePack,
  CogVideoX, SVD.
- **Библиотеки внутри движков** (отдельно не ставить): GSAP, Motion,
  anime.js, Lottie, Three.js.
- **Позже, не проверено:** pixel2motion (логотип → анимированный SVG),
  stickman-video-director (ролики со стикменами).
- **Отклонено:** Motion Canvas (пересекается с HyperFrames/Remotion),
  Graphite, Friction, Aseprite (ручная работа, не конвейер), oil-motion
  (анимации для сайтов).

## Исследования и пакеты

- ИИ-видео и картинки на GTX 1050 Ti — раздел 4 исследования
  [`video/research/2026-10-26-local-voice-and-video.md`](../video/research/2026-10-26-local-voice-and-video.md).
- Пакет для фабрики «живописная графика в 4 ГБ» —
  [`handoff/2026-10-26-clip-factory-4gb.md`](../handoff/2026-10-26-clip-factory-4gb.md).
