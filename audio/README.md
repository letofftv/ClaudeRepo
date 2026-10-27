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

## Находки

| Находка | Для чего | Статус | Карточка |
|---|---|---|---|
| music-studio (свой пакет) | запись вокала, сведение под минусовку, мастеринг, замеры, Ableton | **взять** | [packs/music-studio](packs/music-studio/README.md) |
| Producer Pal | MCP для Ableton Live 12.3+ Suite — у владельца 12.4.7 Suite | **попробовать** (первым) | [producer-pal.md](finds/producer-pal.md) |
| LiveBridge | MCP для Ableton с упором на сведение и мастеринг | **попробовать** (осторожно) | [livebridge.md](finds/livebridge.md) |
| python-audio-separator | стемы и вокал, модели с GitHub | **попробовать** | [audio-separator.md](finds/audio-separator.md) |
| Matchering 2.0 | мастеринг по референсу | **попробовать** | [matchering.md](finds/matchering.md) |
| Pedalboard | обработка кодом с плагинами владельца | **попробовать** | [pedalboard.md](finds/pedalboard.md) |
| ACE-Step 1.5 | наброски песен (MLX на маке), фоновая музыка для роликов | **попробовать** | [ace-step-1-5.md](finds/ace-step-1-5.md) |

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
