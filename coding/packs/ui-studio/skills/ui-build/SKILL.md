---
name: ui-build
description: Сборка интерфейса без сборщика на наборе ui-studio — оболочка с навигацией (боковая/нижняя панель), хэш-роутер, страницы как функции, API с токеном, загрузка файлов с прогрессом, опрос, формы, диалоги, уведомления; строгий CSP и доступность. Использовать, когда нужно написать или переписать фронтенд на чистом JS/CSS, встроить набор компонентов в проект или добавить экран (vanilla JS, ES modules, no build, frontend, SPA, компоненты).
---

# Сборка без сборщика

## Стек

- HTML-оболочка + `tokens.css` + `kit/base.css` + `kit/components.css` +
  стили проекта; скрипты — ES-модули (`<script type="module">`), uPlot —
  обычным `<script defer>` до модулей.
- Никаких CDN, npm-сборки и фреймворков: файлы раздаются как есть, работают
  офлайн и проходят строгий CSP `default-src 'self'`.
- Новый проект: `python3 scripts/scaffold.py new <папка> --title "…"`.
  Существующий: `scaffold.py sync <проект>/kit`, затем переводить экраны.

## Правила кода

- DOM — через `el(tag, attrs, ...children)` и `mount(root, ...)` из `ui.js`.
  Данные — только текстом (`el` сам делает `textContent`), **никогда** не
  `innerHTML` с данными.
- Стили — классами набора. `style="…"` в HTML запрещён CSP; динамические
  значения (ширина полосы) — через `element.style.width` (CSSOM разрешён).
- Иконки — `icon("server")`; новые — `scripts/build_icons.py --add <имя>`.
- Состояние — в модуле страницы; перерисовка — функцией страницы целиком или
  точечно, без библиотек. Опрос — `poll(fn, ms)`; остановить при уходе со
  страницы.
- Адреса — хэш-роутер `createRouter([["/", fn], ["/jobs/:id", fn]])`; при
  смене страницы: заголовок `document.title`, фокус на `<main>`,
  `aria-current="page"` в навигации.
- API — `createApi({tokenKey, onUnauthorized})`: `get/post/put/del`, `upload`
  с прогрессом (XHR). Ошибка — понятным текстом рядом с местом действия.

## Ловушки чистого JS (проверено на практике)

- `[hidden]` проигрывает классу с `display: flex` — в `base.css` стоит
  `[hidden] { display: none !important }`, не убирать.
- Не перерисовывать контейнер, в котором лежит поле ввода с фокусом: поле
  поиска держать вне перерисовываемой части, иначе фокус и курсор теряются.
- Живая перерисовка сбрасывает открытые `<details>`, позицию прокрутки
  лога и играющее видео. Перерисовывать карточку, только когда изменилось
  видимое: сравнивать ключ состояния.
- `replaceChildren(null)` печатает «null» — использовать `mount()`.
- Делегированный обработчик с ранним `return` пропускает закрытие и сброс
  состояния; закрывать диалоги в `close`, а не в кнопке.
- Фильтры и вкладки — в адресе через `history.replaceState`, чтобы ссылка
  и «Назад» работали.
- Import map — это инлайн-скрипт, CSP его блокирует. Только относительные
  импорты; библиотеки — в standalone-сборке.
- Canvas не читает CSS-переменные: цвета брать `token()` и пересоздавать
  графики на `themechange` (`timeChart` так делает).
- Ссылка внутри flex-контейнера перестаёт быть «строчной» и должна иметь
  зону касания ≥24 px (`.tap-link`).

## Компоненты (класс → назначение)

`app`, `app-nav`, `nav-item` (`primary` — центральная кнопка «+» на телефоне),
`app-header`, `app-main` · `page-head`, `section`, `section-head` · `card`,
`tile` (+`tile-label/value/sub/spark`) · `meter` (`meter()`), `sparkline()`,
`timeChart()`, `chartTable()` · `dot`, `badge`, `status-hero`, `alert`
(`data-level="ok|warn|serious|crit|info"`) · `btn` (`ghost`, `subtle`,
`danger`, `sm`, `icon-only`, `aria-busy`) · `field`, `input`, `search`,
`seg`, `chips`, `check` · `list`, `list-item`, `table`, `kv`, `bars` ·
`progress`, `skeleton`, `empty`, `stale` · `code` (`codeBlock()`), `pre.log` ·
`dialog.sheet` (`confirmDialog()`), `toast()`, `onDropFiles()`.
Витрина — `kit/gallery.html`.

## Доступность

- Каждое поле с `<label>`, каждая кнопка-иконка с `aria-label`.
- Статус-сообщения — `role="status"`/`aria-live="polite"` (тосты уже так).
- Порядок табуляции = визуальный; видимый фокус (`:focus-visible` в `base.css`).
- Диалоги — `<dialog>` с `showModal()`: фокус внутри, Esc закрывает.
- Не прятать важное за наведением: на телефоне наведения нет.

## Телефон

Нижняя панель ≤5 пунктов с подписями; касания ≥44 px; формы — в нижнем листе
(`dialog.sheet` сам становится им на узком экране); загрузка файла —
`<input type="file">` + перетаскивание на компьютере; учитывать
`env(safe-area-inset-bottom)`.
