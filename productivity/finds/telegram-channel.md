# Официальный Telegram-канал для Claude Code

- **Ссылка:** https://github.com/anthropics/claude-plugins-official (плагин `telegram`); документация — https://code.claude.com/docs/en/channels
- **Что это:** плагин-канал (research preview): писать в сессию Claude Code на маке из Telegram и получать ответы туда же
- **Найдено:** 2026-10-27, подборка навыков для организации работы
- **Статус:** попробовать

## Зачем фабрике

Доступ к Claude на маке с телефона — отдельно от Джарвиса: дать задачу,
получить ответ или файл, подтвердить действие, пока не у компьютера.

## Риски и оговорки

- Apache-2.0, официальный маркетплейс Anthropic.
- Нужны Bun и отдельный бот от BotFather; сессия на маке должна быть открыта.
- Привязка кодом + allowlist; 4 инструмента (reply, react,
  download_attachment, edit_message); ходит только на api.telegram.org.
- **Тот, кто в allowlist, может подтверждать действия в сессии** — держать
  в allowlist только себя; бот — только под этот канал.

## Как подключить

```
/plugin install telegram@claude-plugins-official
claude --channels plugin:telegram@claude-plugins-official
```

## Что проверено

Страница плагина и описание инструментов прочитаны в исследовании. Не запускалось.
