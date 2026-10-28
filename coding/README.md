# Программирование и вайбкодинг

Навыки, плагины, MCP-серверы и репозитории для работы с кодом в Claude
Code: методика, документация библиотек, навигация по коду, проверка своих
интерфейсов, безопасность. Задачи и заметки — в [`productivity/`](../productivity/README.md).

## Главное (2026-10-27)

К осени 2026 Claude Code уже умеет сам большую часть того, ради чего ставили
большие сборки: plan mode, `/goal` (вместо ralph-loop), `/code-review`,
`/simplify`, `/security-review`, `/batch`, `claude -w` (worktree),
`/statusline`, `/usage` (расход по плагинам и MCP), Remote Control.
Официальный гайд: короткий CLAUDE.md, **CLI лучше MCP** (MCP держит описания
инструментов в контексте постоянно), правила без исключений — в хуки.
Поэтому из сборок нужно немного.

## Стартовый набор (≤6, ~3–4 тыс. токенов в каждой сессии)

1. **Встроенные возможности + [best practices](https://code.claude.com/docs/en/best-practices)** —
   0 токенов: `/plan` или «расспроси меня → SPEC.md»; Stop-хук с тестами или
   проверкой типов проекта; `claude -w` для параллельных задач;
   `/code-review` и `/security-review` перед пушем; `/goal` для длинных задач.
2. **[superpowers](finds/superpowers.md)** — единственный нужный набор методики.
3. **[Context7](finds/context7.md)** — меньше выдуманных API.
4. **[typescript-lsp + pyright-lsp](finds/lsp-plugins.md)** — точная навигация по коду фермы и Джарвиса.
5. **[Playwright CLI](finds/playwright-cli.md)** — Claude смотрит свои HTML/Canvas-сцены и интерфейсы.
6. **[karpathy-guidelines](finds/karpathy-guidelines.md)** — текстом в `~/.claude/CLAUDE.md`.

Для сравнения: отклонённый ECC — ~30 тыс. токенов и 27 хуков.

## Интерфейсы: свой пакет ui-studio (2026-10-28)

**[ui-studio](packs/ui-studio/README.md)** — «создатель интерфейсов», свой
плагин. Шесть навыков проходят цикл: сценарии → экраны → токены → сборка →
живые панели → проверка. В комплекте:
- генератор токенов (OKLCH + WCAG);
- набор компонентов без сборки (uPlot, Lucide);
- `ui_check.mjs` — снимки и проверки в Chromium на телефоне и компьютере в
  обеих темах.

На нём собран интерфейс пульта 0.3. Исследование —
[research/2026-10-28-ui-tools.md](research/2026-10-28-ui-tools.md).

```
claude plugin marketplace add letofftv/ClaudeRepo
claude plugin install ui-studio@clauderepo
```

| Находка | Для чего | Статус |
|---|---|---|
| [uPlot](finds/uplot.md) | графики временных рядов, CSP-чистый, 21 КБ | **взять** (в наборе) |
| [Lucide](finds/lucide-icons.md) | иконки одного стиля, спрайт из нужных | **взять** (в наборе) |
| [axe-core](finds/axe-core.md) | полный аудит доступности в проверках | **взять** (для тестов) |
| [humane-agentic-design](finds/humane-agentic-design.md) | ловушки JS, договор о ревью, русская типографика | **взять** части (перенесены) |
| [web-interface-guidelines](finds/web-interface-guidelines.md) | ~100 проверяемых правил | **взять** как источник |
| [agent-browser](finds/agent-browser.md) | просмотр страниц агентом, axe, сравнение снимков | **попробовать** (против Playwright CLI) |
| [taste-skill](https://github.com/Leonxlnx/taste-skill) (`app-screens.md`) | правила дашбордов: один вопрос — один вывод | источник |
| [design-review](https://github.com/OneRedOak/claude-code-workflows) | фазы ревью и важность находок | источник |
| [impeccable](https://github.com/pbakaus/impeccable) | только CLI `detect`, один раз; плагин ставит хуки и телеметрию | позже |
| [ui-ux-pro-max](https://github.com/nextlevelbuilder/ui-ux-pro-max-skill) | пересекается с ui-studio, срабатывает на любую задачу UI | позже |

**Отклонено:**
- superdesign — облачный вход, HTML уходит в сервис;
- 21st/Magic MCP — платный ключ;
- Figma MCP — 6 вызовов в месяц, оплата из России невозможна;
- shadcn MCP, onlook, ui-skills — React и Tailwind;
- Playwright MCP — для проверок лучше CLI.

## Лучшее: навыки, плагины, MCP и репозитории

| # | Находка | Тип | Для чего | Статус |
|---|---|---|---|---|
| 1 | [claude-plugins-official](finds/claude-plugins-official.md) | официальный каталог | единственный доверенный каталог плагинов | **взять** |
| 2 | [typescript-lsp + pyright-lsp](finds/lsp-plugins.md) | плагины (официальные) | переход к определению, ошибки типов | **взять** |
| 3 | [superpowers](finds/superpowers.md) | 15 навыков + 1 хук | обсуждение → план → TDD → ревью | **взять** |
| 4 | [karpathy-guidelines](finds/karpathy-guidelines.md) | текст для CLAUDE.md | простота, точечные правки | **взять** |
| 5 | [Context7](finds/context7.md) | MCP, 2 инструмента | документация библиотек под версию | **взять** |
| 6 | Best practices + встроенные команды | официальный гайд | методика без установки | **взять** |
| 7 | [Playwright CLI](finds/playwright-cli.md) | CLI + навыки | проверка своих сцен и интерфейсов | **попробовать** |
| 8 | [security-guidance](finds/security-guidance.md) | плагин (официальный) | безопасность ботов и сервисов; ревью на остановке выключить | **попробовать** |
| 9 | [frontend-design](https://github.com/anthropics/claude-plugins-official) | 1 навык (официальный) | признаки «шаблонного вида» и цикл критики по снимкам — перенесены в ui-studio; рядом с ним не ставить | источник |
| 10 | [Telegram-канал](../productivity/finds/telegram-channel.md) | плагин-канал | управлять сессией на маке из Telegram | **попробовать** |
| 11 | [ccusage](https://github.com/ryoppippi/ccusage) | CLI | отчёты по токенам из локальных логов (`--offline`) | **попробовать** |
| 12 | [anthropics/skills](https://github.com/anthropics/skills) | примеры навыков | спецификация и шаблон навыков | позже (источник) |
| 13 | [mattpocock/skills](https://github.com/mattpocock/skills) | 27 навыков | дублирует superpowers; можно взять только grill-me | позже |
| 14 | [OpenSpec](https://github.com/Fission-AI/OpenSpec) / [spec-kit](https://github.com/github/spec-kit) | spec-driven development | для больших проектов на много сессий; телеметрия OpenSpec — `OPENSPEC_TELEMETRY=0` | позже (OpenSpec) |
| 15 | [wshobson/agents](https://github.com/wshobson/agents) | 92 плагина | брать по одному плагину, целиком ~30 тыс. токенов | позже |
| 16 | [Chrome DevTools MCP](https://github.com/ChromeDevTools/chrome-devtools-mcp) | MCP | профилирование; статистика Google — `--no-usage-statistics` | позже |
| 17 | [GitHub MCP](https://github.com/github/github-mcp-server) | MCP | то же делает `gh` без постоянного веса | позже |
| 18 | [Serena](https://github.com/oraios/serena) | MCP | навигация по символам; LSP-плагины покрывают большую часть | позже |
| 19 | [claude-code-router](https://github.com/musistudio/claude-code-router) | шлюз | запасной путь к другим моделям только со своими API-ключами; токены подписки так использовать нельзя | позже |
| 20 | [ccstatusline](https://github.com/sirmalloc/ccstatusline) | строка статуса | встроенный `/statusline` справляется | позже |
| — | [disler/claude-code-hooks-mastery](https://github.com/disler/claude-code-hooks-mastery) | примеры хуков | без лицензии; источник приёмов (блок `rm -rf`, чтения `.env`) | источник |
| — | [awesome-claude-code](https://github.com/hesreallyhim/awesome-claude-code) | каталог | поиск новых находок | источник |

**Позже, без строки в таблице:** feature-dev (альтернатива superpowers),
pr-review-toolkit, commit-commands, claude-md-management, отдельные
ревьюеры из VoltAgent subagents, claude-squad (AGPL), container-use (ранняя
разработка), postgres-mcp (сначала `psql`), Sentry MCP (если появится Sentry).

**Отклонено:**
- [everything-claude-code](finds/everything-claude-code.md) — ~30 тыс. токенов, 27 хуков.
- **SuperClaude** — 30 команд, 20 агентов, 8 MCP; дублирует встроенное и superpowers.
- **Ruflo (бывший claude-flow)** — 314 MCP-инструментов, 27 хуков, внешний endpoint.
- **GSD (open-gsd/gsd-core)** — 72 навыка, 64 агента, 15 хуков — вес уровня ECC.
- **BMAD-METHOD** — команда ролей, избыточно для одного человека; v7 в альфе.
- **claude-task-master** — Commons Clause, MCP-режим 5–21 тыс. токенов; plan mode и superpowers покрывают.
- **claude-mem** — 6 хуков на каждый шаг, облачный «наблюдатель» и реклама криптотокена.
- **Sequential Thinking MCP** — устарел (уровни effort и `ultrathink`).
- **Официальные code-review, code-simplifier, ralph-loop** — дубли встроенных команд; **hookify** — 4 хука на каждый вызов.
- **opcode, Crystal, vibe-kanban** — без бинарников / устарел / закрывается; есть официальное приложение и `claude -w`.
- **overwirehq/claude-code-telegram** — Agent SDK с входом по подписке, что запрещено условиями с февраля 2026; есть официальный канал.
- **ComposioHQ/awesome-claude-skills** — вендорский уклон, нужен ключ Composio.

## Источники

[Best practices](https://code.claude.com/docs/en/best-practices) ·
[Команды](https://code.claude.com/docs/en/commands) ·
[Remote Control](https://code.claude.com/docs/en/remote-control) ·
[claude-plugins-official](https://github.com/anthropics/claude-plugins-official) ·
[superpowers](https://github.com/obra/superpowers) ·
[Context7](https://github.com/upstash/context7) ·
[Playwright CLI](https://github.com/microsoft/playwright-cli) ·
[условия о токенах подписки (февраль 2026)](https://winbuzzer.com/2026/02/19/anthropic-bans-claude-subscription-oauth-in-third-party-apps-xcxwbn/)
