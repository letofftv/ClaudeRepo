# Проверенные библиотеки и инструменты (2026-10-28)

Для интерфейсов без сборки и со строгим CSP (`default-src 'self'`). Проверено
по дистрибутивам npm и README (исследование —
`coding/research/2026-10-28-ui-tools.md`).

## В наборе

| Что | Версия, лицензия | Почему |
|---|---|---|
| uPlot | 1.6.32, MIT | 21,5 КБ gzip, без зависимостей, поток 3 600 точек при 60 к/с ~10% CPU; в dist нет eval, `<style>`, `innerHTML` — только `el.style.*`. Темы нет — цвета передаём из токенов. Версию закрепить: в master идёт переделка форматирования |
| Иконки Lucide | 1.63.0, ISC | есть cpu, memory-stick, gpu, fan, hard-drive, thermometer, gauge; в SVG нет `style=`; спрайт собираем из нужных (`build_icons.py`), полный — 526 КБ |

## Если понадобится больше

| Что | Когда |
|---|---|
| VanJS 1.6 (1,7 КБ) или Preact 11 + htm 3 | если интерфейс вырастет; у Preact `hooks.mjs` импортирует `preact` — поправить на относительный путь |
| Alpine | только сборка `@alpinejs/csp`; строковые `:style` блокируются |
| Chart.js 4 (UMD) | если нужен тип графика, которого нет в uPlot; 69 КБ gzip, для времени нужен адаптер |
| Radix Colors 3 | как справочник шкал (12 ступеней с ролями), значения переносить в токены |
| modern-normalize 3, Open Props | идеи сброса, теней и кривых — переносить выборочно |

## Не брать

- htmx — ждёт HTML с сервера, а у нас JSON.
- petite-vue — нужен eval, проект заброшен.
- Lit — голые импорты.
- Observable Plot — вставляет `<style>` в каждый SVG.
- Lightweight Charts — обязательная плашка TradingView и `<style>`.
- ECharts, dygraphs, Frappe — подсказки через `innerHTML` со `style=`.

## Тесты и ревью

| Что | Для чего |
|---|---|
| axe-core 4.14 (MPL-2.0, есть русская локаль) | полный аудит доступности в `ui_check.mjs --axe`; работает только в контексте `bypassCSP` (использует eval), на страницы не класть |
| agent-browser (Vercel) или Playwright CLI | интерактивный просмотр страниц агентом; взять один из двух |
| Playwright | движок `ui_check.mjs` |

## Подводные камни CSP

1. Import map — инлайн-скрипт: заблокирован.
2. `<style>`, который вставляет библиотека, заблокирован.
3. `style="…"` в строке для `innerHTML` выбрасывается.
4. `setAttribute('style')` заблокирован; `el.style.x = …` и `setProperty` разрешены. `cssText` лучше не использовать.
5. `eval` нужен Alpine (обычной сборке), petite-vue и axe-core.
6. Картинки `data:` (Pico, Tabler) требуют `img-src data:`.
7. `default-src` не покрывает `frame-ancestors`, `base-uri`, `form-action` — задать явно.
8. Python на Windows может отдать `.js` как `text/plain` (реестр), и модули не загрузятся под `nosniff`. MIME закреплять в сервере.
