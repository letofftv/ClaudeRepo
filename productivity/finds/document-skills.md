# document-skills (anthropics/skills)

- **Ссылка:** https://github.com/anthropics/skills
- **Что это:** официальные навыки Anthropic для документов — docx, pdf, pptx, xlsx (в claude.ai уже встроены)
- **Найдено:** 2026-10-27, подборка навыков для организации работы
- **Статус:** взять

## Зачем фабрике

Сметы и таблицы, PDF (заполнение, извлечение, сборка), презентации,
договоры и брифы в Word — прямо из Claude Code. Пригодится и для
организации работы, и для бизнеса.

## Риски и оговорки

- Репозиторий ~184 тыс. ★; лицензия навыков документов —
  **source-available, проприетарная** (не открытая).
- Запускают локальные скрипты Python и JS; нужны pandoc, LibreOffice,
  npm-пакеты docx и pptxgenjs.
- Вес ~740 токенов.

## Как подключить

```
/plugin marketplace add anthropics/skills
/plugin install document-skills@anthropic-agent-skills
```

## Что проверено

Страница и состав навыков прочитаны в исследовании. Не запускалось.
