# typescript-lsp + pyright-lsp

- **Ссылка:** https://github.com/anthropics/claude-plugins-official (плагины `typescript-lsp`, `pyright-lsp`)
- **Что это:** официальные плагины, подключающие языковые серверы TypeScript и Python к Claude Code
- **Найдено:** 2026-10-27, подборка лучшего для программирования
- **Статус:** взять (код фабрики на Node и Python)

## Зачем фабрике

Переход к определению и ошибки типов сразу после каждой правки — вместо
поиска текстом. Точнее навигация по коду фермы и Джарвиса.

## Риски и оговорки

- Apache-2.0. 0 навыков, 0 хуков — нет постоянного веса в контексте.
- Нужны бинарники языковых серверов.

## Как подключить

```
npm i -g typescript-language-server typescript pyright
/plugin install typescript-lsp@claude-plugins-official
/plugin install pyright-lsp@claude-plugins-official
```

## Что проверено

Плагины прочитаны в клоне каталога в исследовании. Не запускалось.
