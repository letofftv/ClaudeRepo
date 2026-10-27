# Организация работы

Задачи и проекты, заметки и база знаний, документы, календарь и почта,
встречи, доступ к Claude с телефона. Автоматизация бизнес-процессов и CRM —
в [`business/`](../business/README.md); работа с кодом — в [`coding/`](../coding/README.md).

Владелец работает один (фабрика видео и музыка), в России: многие западные
сервисы недоступны или их нельзя оплатить — поэтому упор на локальное
(Obsidian, macOS) и российское (Яндекс).

## Лучшее (2026-10-27)

**Стартовый набор — без зависимости от санкционных сервисов:**

1. **Obsidian + obsidian-skills** — локальная база знаний на маке.
2. **Два навыка из productivity** (задачи и память) — без `.mcp.json`.
3. **document-skills** — сметы, таблицы, PDF, презентации.
4. **Коннекторы Gmail и Google Calendar в claude.ai** — почта владельца уже
   на Gmail; ставить ничего не нужно, отправку оставить с подтверждением.
5. **Apple Events MCP** — Напоминания и Календарь на маке (Яндекс Календарь и
   iCloud — через CalDAV в Календарь.app).
6. **Официальный Telegram-канал** — Claude на маке с телефона.

Уже есть и ставить не нужно: **`gh`** — задачи фабрики в GitHub Issues
(не добавляет токенов в сессию).

| # | Находка | Тип | Для чего | Статус |
|---|---|---|---|---|
| 1 | [obsidian-skills](finds/obsidian-skills.md) | 6 навыков | заметки, Bases, Canvas, CLI, веб → Markdown | **взять** |
| 2 | [document-skills](finds/document-skills.md) | 4 навыка (официальные) | docx, pdf, pptx, xlsx | **взять** |
| 3 | Коннекторы claude.ai: Gmail, Google Calendar, Drive | официальные коннекторы | почта, события, поиск свободного времени | **взять** |
| 4 | GitHub Issues/Projects через `gh` | CLI | задачи фабрики в репозитории | **взять** |
| 5 | [productivity (knowledge-work-plugins)](finds/productivity-plugin.md) | плагин (официальный) | задачи, память, доска — только 2 навыка | **попробовать** |
| 6 | [Telegram-канал](finds/telegram-channel.md) | плагин-канал (официальный) | Claude на маке из Telegram | **попробовать** |
| 7 | [Apple Events MCP](finds/apple-events-mcp.md) | MCP | Напоминания и Календарь macOS | **попробовать** |
| 8 | [yandex-tracker-mcp](finds/yandex-tracker-mcp.md) | MCP | Яндекс Трекер — если нужен настоящий трекер | **попробовать** |
| 9 | [mcp-obsidian](https://github.com/MarkusPfundstein/mcp-obsidian) | MCP | хранилище Obsidian из Claude Desktop (в Claude Code — дубль) | позже |
| 10 | [basic-memory](https://github.com/basicmachines-co/basic-memory) | MCP, AGPL | долгая память в Markdown; дублирует хранилище + CLAUDE.md | позже |
| 11 | [google_workspace_mcp](https://github.com/taylorwilsdon/google_workspace_mcp) | MCP | Google без claude.ai (для Джарвиса); ~125 инструментов | позже |
| 12 | [yacli](https://github.com/NextStat/yacli) / [caldav-mcp](https://github.com/dominik1001/caldav-mcp) | CLI+MCP / MCP | Яндекс Почта, Календарь, Диск; универсальный CalDAV | позже |
| 13 | [Meetily (meeting-minutes)](https://github.com/Zackriya-Solutions/meeting-minutes) | приложение | локальная запись и саммари встреч на Apple Silicon | позже |
| 14 | [todoist-ai](https://github.com/Doist/todoist-ai) | MCP (официальный) | Todoist работает, но Pro из России не оплатить | позже |

**Отклонено:**
- **Notion MCP** — Notion закрыл доступ пользователям из России с 2024-09-09.
- **Linear, Asana, Atlassian, monday, ClickUp** — санкционные ограничения;
  командные инструменты, одному избыточны.
- **chigwell/telegram-mcp** — полный доступ к личному аккаунту (147
  инструментов, включая удаление истории), голосовые по умолчанию уходят в
  Groq. Допустим только в режиме чтения со списком чатов и локальным Whisper.
- **memory из modelcontextprotocol/servers** — дублирует CLAUDE.md и
  автопамять Claude Code.
- **apple-mcp (supermemoryai), obsidian-claude-code-mcp** — заброшены.
- **Официальный MCP Битрикс24** — нужен платный тариф и подписки; тяжело для
  одного человека.
- **MCP для YouGile, Kaiten, Weeek** — только мелкие сторонние (≤32 ★);
  смотреть, если владелец уже работает в одном из них.
- **Сторонние MCP для Яндекс 360** — все меньше 30 ★, один в архиве.

**Подборки — источник, не ставить:** punkpeye/awesome-mcp-servers,
ComposioHQ/awesome-claude-skills, anthropics/claude-plugins-official.

Общее правило: у всех `npx`/`uvx` закреплять версию; навыки — через SkillSpector.

## Источники

[anthropics/skills](https://github.com/anthropics/skills) ·
[knowledge-work-plugins](https://github.com/anthropics/knowledge-work-plugins) ·
[claude-plugins-official](https://github.com/anthropics/claude-plugins-official) ·
[obsidian-skills](https://github.com/kepano/obsidian-skills) ·
[Channels](https://code.claude.com/docs/en/channels) ·
[Google Workspace connectors](https://support.claude.com/en/articles/10166901-use-google-workspace-connectors) ·
[Notion: ограничения для России](https://notion.com/help/restrictions-for-customers-based-in-russia) ·
[Todoist: оплата из России](https://todoist.com/help/articles/making-payments-from-russia-nAHXlBAPn) ·
[Obsidian CLI](https://help.obsidian.md/cli)
