# Иконки Lucide

- **Ссылка:** https://github.com/lucide-icons/lucide (npm `lucide-static`)
- **Что это:** набор из ~1 900 контурных SVG-иконок одного стиля
- **Найдено:** 2026-10-28, исследование инструментов для интерфейсов
- **Статус:** взять — 70 иконок в спрайте набора ui-studio (`kit/icons.svg`)

## Зачем фабрике

Единый вид иконок во всех своих интерфейсах. Есть всё для панели сервера:
- cpu, memory-stick, gpu, fan, hard-drive, thermometer, gauge;
- для звука и видео: audio-waveform, film, captions.

## Риски и оговорки

- **Лицензия.** ISC (часть иконок от Feather — MIT); текст лицензии лежит рядом со спрайтом.
- **Атрибуты `style=`** в файлах отсутствуют. Цвет и толщина задаются CSS (`.icon`).
- **Полный спрайт** — 526 КБ, поэтому собираем только нужные.

## Как подключить

```
npm pack lucide-static && tar -xzf lucide-static-*.tgz
python3 coding/packs/ui-studio/scripts/build_icons.py --from package --out kit/icons.svg --add <имя>
```

## Что проверено

Спрайт собран скриптом и работает в пульте: тесты проверяют, что каждая
использованная иконка есть в спрайте.
