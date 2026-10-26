# Находки

Оценка — с точки зрения фабрики (см. `CLAUDE.md`). Звёзды — на дату находки.

## Складывающийся конвейер (гипотеза, проверить на сервере)

Для обучающих видео по интерфейсам платформ:

1. **Playwright MCP** — агент проходит сценарий на настоящей платформе и
   записывает видео с анимированным курсором.
2. **HyperFrames** (+ **gsap-skills**) — запись в композицию: зум, выноски,
   титры, анимация.
3. **Orkas-VideoStudio** — монтаж: паузы, субтитры (whisper.cpp), озвучка,
   громкость.
4. **SkillSpector** — перед установкой любого из навыков выше.

Промо-клипы и UI-ролики без записи экрана — **product-launch-motion**.

## Все находки

| Находка | Для чего на фабрике | Статус | Карточка |
|---|---|---|---|
| SkillSpector | проверка навыков перед установкой | **взять** | [skillspector.md](skillspector.md) |
| HyperFrames | анимация, клипы, обучающие видео; рендер HTML → MP4 | **попробовать** (первым) | [hyperframes.md](hyperframes.md) |
| Playwright MCP (видео) | запись настоящих интерфейсов с курсором | **попробовать** | [playwright-mcp-video.md](playwright-mcp-video.md) |
| gsap-skills | точная GSAP-анимация внутри HyperFrames | **попробовать** (с HyperFrames) | [gsap-skills.md](gsap-skills.md) |
| Orkas-VideoStudio | монтаж записей, субтитры, озвучка поверх HyperFrames | **попробовать** (вторым) | [orkas-videostudio.md](orkas-videostudio.md) |
| product-launch-motion | промо и UI-ролики под музыку; v1 — под озвучку | **попробовать** | [product-launch-motion.md](product-launch-motion.md) |
| Remotion | то же, что HyperFrames, на React | позже (запасной) | [remotion.md](remotion.md) |
| digitalsamba video toolkit | навык записи браузера, список открытых моделей | позже (по частям) | [digitalsamba-video-toolkit.md](digitalsamba-video-toolkit.md) |
| Manim | объясняющие вставки: схемы, формулы | позже | [manim.md](manim.md) |
| ArcReel | конвейер «сценарий → ИИ-видео» | позже | [arcreel.md](arcreel.md) |
| Blender Lab MCP | 3D-анимация через Blender | позже | [blender-lab-mcp.md](blender-lab-mcp.md) |
| Claude-Code-Video-Toolkit | список ссылок (разобран) | источник | [claude-code-video-toolkit.md](claude-code-video-toolkit.md) |
| awesome-motion-design-agent-skills | список ссылок (разобран) + 5 слабых навыков | навыки отклонены | [awesome-motion-design-agent-skills.md](awesome-motion-design-agent-skills.md) |
| everything-claude-code (ECC) | сборка для разработки программ | отклонено | [everything-claude-code.md](everything-claude-code.md) |

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

## Пробелы — что поискать дальше

1. **Локальная озвучка (TTS)** на видеокарте с OpenAI-совместимым API —
   чтобы подключить к Orkas без облака. Кандидат по названию: Qwen3-TTS.
2. **Локальные видеомодели и музыка** на GPU — запуск LTX-2.3, ACE-Step,
   FLUX.2 у себя (ComfyUI или отдельные серверы), а не через Modal/RunPod.
3. ~~Запись экрана~~ — закрыто: Playwright MCP + навык `playwright-recording`.
4. ~~Субтитры~~ — закрыто: whisper.cpp в HyperFrames/Orkas.
