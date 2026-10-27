# claude-plugins-official

- **Ссылка:** https://github.com/anthropics/claude-plugins-official
- **Что это:** официальный каталог плагинов Claude Code — 315 плагинов: 40 от Anthropic, остальные от вендоров
- **Найдено:** 2026-10-27, подборка лучшего для программирования
- **Статус:** взять — как единственный каталог

## Зачем фабрике

Один доверенный источник плагинов: LSP-серверы языков, superpowers,
Context7, frontend-design, security-guidance, канал Telegram и др.
Подключён в Claude Code по умолчанию.

## Риски и оговорки

- Apache-2.0, ~45 тыс. ★, обновляется ежедневно.
- **Сторонние плагины Anthropic не проверяет** — читать каждый перед
  установкой и прогонять через SkillSpector.
- Официальные code-review, code-simplifier и ralph-loop дублируют встроенные
  `/code-review`, `/simplify` и `/goal` — не ставить. hookify — 4 хука на
  каждый запрос и вызов инструмента, лучше 2–3 своих хука.

## Как подключить

```
/plugin marketplace add anthropics/claude-plugins-official
```

## Что проверено

Клон прочитан в исследовании: marketplace.json, security-guidance, telegram,
ralph-loop, hookify, frontend-design, конфиги MCP. Не запускалось.
