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
