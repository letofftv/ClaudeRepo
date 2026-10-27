# Общее

То, что не относится к одному направлению: проверка безопасности находок,
сборки для Claude Code общего назначения, настройка сервера фабрики.

## Находки

| Находка | Для чего | Статус | Карточка |
|---|---|---|---|
| SkillSpector (NVIDIA) | проверка навыков на уязвимости перед установкой | **взять** | [skillspector.md](finds/skillspector.md) |
| everything-claude-code (ECC) | сборка для разработки программ | отклонено | [everything-claude-code.md](finds/everything-claude-code.md) |

## Исследования

- [GTX 1050 Ti при переезде с Windows на Ubuntu](research/2026-10-26-ubuntu-gpu-setup.md)
  (2026-10-26): драйвер 580, ядро, Docker и CUDA 12, память WSL2, WebGL фермы.

## Служебное

- Шаблон карточки — [`templates/finding.md`](../templates/finding.md).
- Канал передачи пакетов в фабрику — [`handoff/`](../handoff/README.md).
- Каталог плагинов этого репозитория для Claude Code —
  [`.claude-plugin/marketplace.json`](../.claude-plugin/marketplace.json).
