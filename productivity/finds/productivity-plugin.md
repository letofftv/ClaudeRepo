# productivity (anthropics/knowledge-work-plugins)

- **Ссылка:** https://github.com/anthropics/knowledge-work-plugins
- **Что это:** официальный плагин Anthropic для Cowork и Claude Code — список задач, двухуровневая память, HTML-доска, команды `/start` и `/update`
- **Найдено:** 2026-10-27, подборка навыков для организации работы
- **Статус:** попробовать — взять только навыки task-management и memory-management, без `.mcp.json`

## Зачем фабрике

`TASKS.md` со списком задач, память о людях и проектах (CLAUDE.md +
`memory/`), доска задач — без единого внешнего сервиса.

## Риски и оговорки

- Apache-2.0, v1.3.1, репозиторий ~33 тыс. ★, активен.
- **`.mcp.json` подключает 9 западных HTTP-серверов** (Slack, Notion, Asana,
  Linear, Atlassian, monday, ClickUp, Gmail, Google Calendar) — большинство
  недоступно из России. Не ставить плагин целиком.
- Пишет CLAUDE.md в текущую папку — запускать в отдельной папке (например,
  в хранилище Obsidian), не в ClaudeRepo.
- Доска (~98 КБ HTML) грузит Google Fonts. Вес ~250 токенов.

## Как подключить

Скопировать навыки task-management и memory-management в
`.claude/skills` рабочей папки (без `.mcp.json`), после SkillSpector.

## Что проверено

Клон прочитан в исследовании: состав навыков, `.mcp.json`, запись CLAUDE.md.
Не запускалось.
