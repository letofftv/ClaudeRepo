# Находки

Оценка — с точки зрения фабрики (см. `CLAUDE.md`). Звёзды — на дату находки.

| Находка | Для чего на фабрике | Статус | Карточка |
|---|---|---|---|
| HyperFrames | анимация, клипы, обучающие видео по UI; рендер HTML → MP4 на сервере | **попробовать** (первым) | [hyperframes.md](hyperframes.md) |
| Remotion | то же, что HyperFrames, на React | позже (запасной) | [remotion.md](remotion.md) |
| Manim | объясняющие вставки: схемы, формулы, алгоритмы | позже | [manim.md](manim.md) |
| Claude-Code-Video-Toolkit | список ссылок; запись экрана через Playwright для роликов по UI | позже (разобрать ссылки) | [claude-code-video-toolkit.md](claude-code-video-toolkit.md) |
| ArcReel | конвейер «сценарий → ИИ-видео» | позже | [arcreel.md](arcreel.md) |
| Blender Lab MCP | 3D-анимация через Blender | позже | [blender-lab-mcp.md](blender-lab-mcp.md) |
| awesome-motion-design-agent-skills | список ссылок по моушн-дизайну + 5 слабых навыков | навыки отклонены; ссылки — в очередь | [awesome-motion-design-agent-skills.md](awesome-motion-design-agent-skills.md) |
| everything-claude-code (ECC) | сборка для разработки программ | отклонено | [everything-claude-code.md](everything-claude-code.md) |

## Очередь на проверку

Ссылки из других находок, ещё не разобранные:

- `greensock/gsap-skills` — официальные навыки GSAP; дополнение к HyperFrames.
- `AbubakrChan/product-launch-motion` — сайт → ролик через Playwright и FFmpeg.
- `Orkas-AI/Orkas-VideoStudio` — 14 навыков для видео.
- `NVIDIA/SkillSpector` — сканер навыков перед установкой (для самой песочницы).
- Из Claude-Code-Video-Toolkit: digitalsamba video toolkit (`/record-demo`),
  Playwright MCP `--save-video`.

## Остальное из подборки по анимации (2026-10-26), без карточек

- **GSAP, Motion, anime.js, Lottie, Three.js** — библиотеки, которые
  используются *внутри* HyperFrames/Remotion. Отдельно не ставить.
  GSAP с 2025 года полностью бесплатный, включая плагины.
- **Motion Canvas** — пересекается с HyperFrames/Remotion. Отклонено.
- **pixel2motion** (`nolangz/pixel2motion`) — навык: растровый логотип →
  анимированный SVG. Может пригодиться для заставок. Позже, не проверено.
- **stickman-video-director** — ролики со стикменами для «безликих» каналов.
  Позже, если понадобится такой формат.
- **Graphite, Friction, Aseprite** — программы для ручной работы, не для
  конвейера. Отклонено для фабрики.
- **oil-motion** — анимации для сайтов. Отклонено: фабрика не делает сайты.

## Пробелы — что поискать дальше

Направления, под которые находок пока нет:

1. **Запись экрана и UI-туториалы** — автоматическая запись сценария в браузере
   (Playwright), курсор и зум, как в Screen Studio.
2. **Локальная озвучка (TTS)** на видеокарте сервера, без платных сервисов.
3. **Субтитры** — распознавание речи (Whisper и аналоги) и вшивание.
4. **Локальные видеомодели** на GPU (ComfyUI и модели image/text-to-video) —
   для ИИ-вставок и анимации.
