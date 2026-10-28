# Аудио и мастеринг

Сочинение музыки, сведение, мастеринг, запись вокала под минусовки,
управление DAW через MCP. Озвучка роликов (TTS) — в [`video/`](../video/README.md).

Владелец: Ableton Live 12.4.7 Suite на маке (сведение и мастеринг), вокал
пишется на студии (студия работает в Ableton и Cubase). Проекты
некоммерческие.

## Свой пакет навыков

**[`packs/music-studio`](packs/music-studio/README.md)** — плагин Claude Code:
7 навыков (запись на студии и импорт, вокал на минусовку, разбор микса,
мастеринг, замеры громкости, управление Ableton, открытые инструменты),
справочники (приёмы мастеров, карта плагинов, цели громкости) и скрипты
замеров на ffmpeg. Без хуков и MCP-серверов, ~1,4 тыс. токенов в каждой
сессии.

```
brew install ffmpeg
claude plugin marketplace add letofftv/ClaudeRepo
claude plugin install music-studio@clauderepo
```

## Лучшее: навыки, плагины, MCP и репозитории (2026-10-27)

Основа — свой пакет `music-studio` и Producer Pal. Новое из подборки:
**русские тексты песен** (ударения, размер, рифмы — готового навыка нет,
писать свой `lyrics-ru`), **проверка сетов со студии**, **дизайн звука в
бесплатном Vital**, **маскировка «голос против минусовки»**.

| # | Находка | Тип | Для чего | Статус |
|---|---|---|---|---|
| 1 | [music-studio](packs/music-studio/README.md) | свой пакет | запись, сведение, мастеринг, замеры, Ableton | **взять** |
| 2 | [Producer Pal](finds/producer-pal.md) | MCP | управление Live 12.4.7 Suite | **попробовать** (первым) |
| 3 | [ruaccent + RussianPoetryScansionTool](finds/ruaccent.md) | библиотеки | ударения, размер, рифмы → свой навык `lyrics-ru` | **попробовать** |
| 4 | [abletoolz](finds/abletoolz.md) | CLI | проверка и починка сетов .als со студии | **попробовать** |
| 5 | [Phantom](finds/phantom.md) | CLI | маскировка голоса и минусовки, фаза, референс | **попробовать** (только CLI) |
| 6 | [vital-mcp](finds/vital-mcp.md) | MCP | пресеты бесплатного Vital словами | **попробовать** |
| 7 | [pytheory-skill](finds/pytheory-skill.md) | 6 навыков | гармония, ступени, экспорт MIDI | **попробовать** (2 навыка) |
| 8 | Коннектор Ableton Knowledge (claude.ai) | официальный коннектор | ответы по документации Live и Push, только чтение | **попробовать** |
| 9 | [song-analysis (music-workflow-skills)](https://github.com/PerIPan/music-workflow-skills) | 6 навыков | аккордовая сетка трека; 5–6 отдельных окружений — тяжело | **попробовать** (на одной минусовке) |
| 10 | [py2max](https://github.com/shakfu/py2max) | библиотека | свои устройства Max for Live (.amxd) | позже |
| 11 | [ableton-extension-skill](https://github.com/aker-dev/ableton-extension-skill) | навык | Extensions на официальном JS SDK — проверить, есть ли они в 12.4.7 | позже |
| 12 | [suno-songwriter-agent-skill](https://github.com/regiellis/suno-songwriter-agent-skill) | навык | промпты под Suno v6; оплата из России не проходит | позже |
| 13 | [ableton-skills (glincker)](https://github.com/glincker/ableton-skills) | 12 навыков | общие советы под чужие MCP — источник приёмов | позже |

**Отклонено (подборка 2026-10-27):** claude-ai-music-skills (53 навыка,
MCP на 80+ инструментов — тяжело; источник: pronunciation-specialist,
mix-engineer), китайские lyric/composition-skills (брать только формат
LYR-SPEC), awesome-music-agent-skills (тонкий каталог), Cubase MCP (Cubase
только на студии), ABLE-MCP, maxforlive-device-builder, mixmaster-ai и
другие без лицензии, serum-mcp и u-he (платные синты), MaxMCP (нужен Max
9.1, Commons Clause), Splice (подписку не оплатить).

## Находки

| Находка | Для чего | Статус | Карточка |
|---|---|---|---|
| music-studio (свой пакет) | запись вокала, сведение под минусовку, мастеринг, замеры, Ableton | **взять** | [packs/music-studio](packs/music-studio/README.md) |
| Producer Pal | MCP для Ableton Live 12.3+ Suite — у владельца 12.4.7 Suite | **попробовать** (первым) | [producer-pal.md](finds/producer-pal.md) |
| LiveBridge | MCP для Ableton с упором на сведение и мастеринг | **попробовать** (осторожно) | [livebridge.md](finds/livebridge.md) |
| python-audio-separator | стемы и вокал, модели с GitHub; на сервере — видеокарта, в 8 раз быстрее процессора | **взять** | [audio-separator.md](finds/audio-separator.md) |
| Matchering 2.0 | мастеринг по референсу | **попробовать** | [matchering.md](finds/matchering.md) |
| Pedalboard | обработка кодом с плагинами владельца | **попробовать** | [pedalboard.md](finds/pedalboard.md) |
| ACE-Step 1.5 | наброски песен (MLX на маке), фоновая музыка для роликов | **попробовать** | [ace-step-1-5.md](finds/ace-step-1-5.md) |
| ruaccent + RPST | ударения, размер, рифмы русских текстов | **попробовать** | [ruaccent.md](finds/ruaccent.md) |
| abletoolz | проверка сетов .als со студии | **попробовать** | [abletoolz.md](finds/abletoolz.md) |
| Phantom | маскировка голоса и минусовки | **попробовать** | [phantom.md](finds/phantom.md) |
| vital-mcp | дизайн звука в Vital | **попробовать** | [vital-mcp.md](finds/vital-mcp.md) |
| pytheory-skill | гармония и теория | **попробовать** | [pytheory-skill.md](finds/pytheory-skill.md) |

**Без карточек** (подробности — в исследовании):
- **Позже:** wstierhout/ableton-live-mcp (без выполнения кода), REAPER MCP
  (`bonfire-systems/reaper-mcp`, `xDarkzx/Reaper-MCP`), Audacity-MCP,
  audio-analyzer-rs, demucs-mlx, whisperX (русские таймкоды),
  MuScriptor/SOME/basic-pitch (аудио → MIDI), librosa, Essentia, beat_this,
  Magenta RealTime 2.
- **Отклонено:** Audition + MCP (нет официального, мосты требуют отключить
  проверку подписи CEP; купить из России нельзя); ahujasid/ableton-mcp
  (телеметрия по умолчанию); Simon-Kansara (заброшен); LivePilot (BSL,
  внешние вызовы); ElevenLabs MCP (архив, недоступен из России); YuE2,
  SongGeneration v2 (не для этого железа); ITO-Master, Diff-MST
  (исследовательский уровень).

## Исследования

- [Музыка и звук: MCP для DAW, плагины, открытые инструменты, уроки мастеров](research/2026-10-27-audio-production.md) (2026-10-27).
