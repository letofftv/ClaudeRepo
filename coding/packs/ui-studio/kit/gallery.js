// Gallery of the kit: every component in one page, real data shapes, both themes.
// ui_check.mjs runs over this page as the kit's self-test.
import { $, $$, el, icon, mount, fmt, level, toast, confirmDialog, codeBlock, initTheme, setTheme, getTheme, setIconSprite } from "./ui.js";
import { sparkline, meter, timeChart, chartTable } from "./charts.js";

setIconSprite("icons.svg");
initTheme();

const seg = $("#theme-seg");
function syncSeg() { for (const b of $$("button", seg)) b.setAttribute("aria-pressed", String(b.dataset.mode === getTheme())); }
seg.addEventListener("click", (e) => { const b = e.target.closest("button"); if (b) { setTheme(b.dataset.mode); syncSeg(); } });
syncSeg();

const now = Date.now() / 1000;
const cpu = Array.from({ length: 60 }, (_, i) => 20 + 15 * Math.sin(i / 6) + (i > 50 ? 35 : 0));

function tile(label, iconName, value, unit, sub, lvl, extra) {
  return el("div", { class: "tile", "data-level": lvl },
    el("div", { class: "tile-label" }, icon(iconName, { cls: "sm" }), label),
    el("div", { class: "tile-value" }, value, unit ? el("small", {}, unit) : null),
    el("div", { class: "tile-sub" }, sub), extra);
}

const sections = [
  el("section", { id: "status", class: "stack gap-4" },
    el("div", { class: "page-head" }, el("h2", {}, "Статус"), el("span", { class: "meta" }, el("span", { class: "dot live", "data-level": "ok" }), " обновлено только что")),
    el("div", { class: "status-hero", "data-level": "warn", role: "status" }, icon("triangle-alert"),
      el("div", {}, el("h2", {}, "Есть замечания"), el("p", {}, "Видеопамять занята на 93% · 1 служба не отвечает"))),
    el("div", { class: "grid-auto-sm" },
      tile("Процессор", "cpu", fmt.num(cpu[cpu.length - 1], 0), "%", "нагрузка 2,1 · 8 потоков", level(cpu[cpu.length - 1], 70, 90),
        el("div", { class: "tile-spark" }, sparkline(cpu, { max: 100 }))),
      tile("Память", "memory-stick", "5,2", "ГБ", "из 7,7 ГБ · 68%", "ok", meter(68, "ok", { label: "Память" })),
      tile("Видеопамять", "gpu", "3,8", "ГБ", "из 4 ГБ · 93%", "warn", meter(93, "warn", { label: "Видеопамять" })),
      tile("Температура GPU", "thermometer", "71", "°C", "вентилятор 45%", "ok", null),
      tile("Диск /mnt/d", "hard-drive", "18", "ГБ", "свободно из 931 ГБ", "crit", meter(98, "crit", { label: "Диск" }))),
    el("div", { class: "stack gap-2" },
      el("div", { class: "alert", "data-level": "crit" }, icon("circle-alert"),
        el("div", {}, el("div", { class: "alert-title" }, "Не отвечает: Postgres (Connection refused)"), el("div", { class: "alert-meta" }, "с 12:03 · 14 мин"))),
      el("div", { class: "alert", "data-level": "warn" }, icon("triangle-alert"),
        el("div", {}, el("div", { class: "alert-title" }, "Видеопамять занята на 93%"), el("div", { class: "alert-meta" }, "с 12:10"))),
      el("div", { class: "alert", "data-level": "info" }, icon("info"),
        el("div", {}, el("div", { class: "alert-title" }, "Задача «Замер громкости» завершилась с ошибкой"), el("div", { class: "alert-meta" }, "5 мин назад"))))),

  el("section", { id: "controls", class: "section stack gap-4" },
    el("div", { class: "section-head" }, el("h3", {}, "Элементы управления")),
    el("div", { class: "cluster" },
      el("button", { class: "btn", type: "button", onclick: () => toast("Задача запущена") }, icon("play", { cls: "sm" }), "Запустить"),
      el("button", { class: "btn ghost", type: "button" }, icon("upload", { cls: "sm" }), "Загрузить"),
      el("button", { class: "btn subtle", type: "button" }, "Отмена"),
      el("button", { class: "btn danger", type: "button", onclick: () => confirmDialog("Удалить файл mix-v3.wav?", { title: "Удалить файл", okText: "Удалить", danger: true }) }, icon("trash-2", { cls: "sm" }), "Удалить"),
      el("button", { class: "btn ghost icon-only", type: "button", "aria-label": "Обновить" }, icon("refresh-cw")),
      el("button", { class: "btn", type: "button", "aria-busy": "true" }, "Идёт…")),
    el("div", { class: "grid-2" },
      el("div", { class: "field" }, el("label", { for: "g-name" }, "Название"), el("input", { class: "input", id: "g-name", value: "Город пробок" }),
        el("span", { class: "hint" }, "Видно в списке проектов")),
      el("div", { class: "field" }, el("label", { for: "g-sel" }, "Роль файла"),
        el("select", { class: "input", id: "g-sel" }, el("option", {}, "Мастер"), el("option", {}, "Микс"), el("option", {}, "Минусовка")))),
    el("div", { class: "cluster" },
      el("div", { class: "search" }, icon("search"), el("input", { class: "input", type: "search", placeholder: "Поиск", "aria-label": "Поиск" })),
      el("div", { class: "seg", role: "group", "aria-label": "Период" },
        ["15 мин", "1 ч", "6 ч", "24 ч"].map((t, i) => el("button", { type: "button", "aria-pressed": String(i === 1) }, t)))),
    el("div", { class: "chips" }, ["Аудио", "Видео", "Генерация"].map((t, i) => el("button", { class: "chip", type: "button", "aria-pressed": String(i === 0) }, t))),
    el("div", { class: "cluster" }, ["ok", "warn", "serious", "crit", "info"].map((l) => el("span", { class: "badge", "data-level": l }, l)))),

  el("section", { id: "data", class: "section stack gap-4" },
    el("div", { class: "section-head" }, el("h3", {}, "Данные"), el("span", { class: "meta" }, "uPlot, линия 2px, подсказка по курсору")),
    el("div", { class: "card", id: "chart-card" }, el("div", { class: "card-head" }, el("h4", {}, "Процессор и память, %"))),
    el("div", { class: "grid-2" },
      el("div", { class: "card" }, el("div", { class: "card-head" }, el("h4", {}, "Потоки процессора")),
        el("div", { class: "bars" }, [12, 64, 93, 40, 22, 8, 71, 35].map((v, i) => el("div", { class: "bar-row" },
          el("span", { class: "label" }, `Поток ${i + 1}`), meter(v, level(v, 70, 90), { size: "sm" }), el("span", { class: "value" }, fmt.pct(v)))))),
      el("div", { class: "card" }, el("div", { class: "card-head" }, el("h4", {}, "Сводка")),
        el("dl", { class: "kv" }, el("dt", {}, "Система"), el("dd", {}, "Linux 6.6 (WSL2)"), el("dt", {}, "Работает"), el("dd", {}, fmt.duration(392000)),
          el("dt", {}, "Сеть"), el("dd", {}, `↓ ${fmt.rate(1450000)} · ↑ ${fmt.rate(82000)}`), el("dt", {}, "Обновлено"), el("dd", {}, fmt.ago(now - 3))))),
    el("div", { class: "card flush" }, el("div", { class: "table-wrap" }, el("table", { class: "table" },
      el("thead", {}, el("tr", {}, el("th", {}, "Процесс"), el("th", { class: "num" }, "Процессор"), el("th", { class: "num" }, "Память"))),
      el("tbody", {}, [["chrome ×14", 63.2, 2.1e9], ["python3", 12.4, 3.4e8], ["postgres ×9", 1.2, 5.1e8]].map(([n, c, m]) =>
        el("tr", {}, el("td", {}, n), el("td", { class: "num" }, fmt.pct(c, 1)), el("td", { class: "num" }, fmt.bytes(m))))))))),

  el("section", { id: "lists", class: "section stack gap-4" },
    el("div", { class: "section-head" }, el("h3", {}, "Списки")),
    el("div", { class: "card flush list" },
      el("button", { class: "list-item", type: "button", "aria-current": "true" }, icon("audio-waveform"),
        el("span", { class: "list-item-main" }, el("span", { class: "list-item-title" }, "Замер громкости — mix-v3.wav"), el("span", { class: "list-item-sub" }, "−13,8 LUFS · TP −0,6 dBTP")),
        el("span", { class: "badge", "data-level": "ok" }, "готово")),
      el("button", { class: "list-item", type: "button" }, icon("film"),
        el("span", { class: "list-item-main" }, el("span", { class: "list-item-title" }, "Вертикаль 9:16 — урок-03.mp4"), el("div", { class: "progress mt-1" }, el("span", { class: "g-progress" }))),
        el("span", { class: "list-item-meta" }, "42% · ≈ 3 мин")),
      el("button", { class: "list-item", type: "button" }, icon("captions"),
        el("span", { class: "list-item-main" }, el("span", { class: "list-item-title" }, "Субтитры — интервью.wav"), el("span", { class: "list-item-sub" }, "ошибка: модель не найдена")),
        el("span", { class: "badge", "data-level": "crit" }, "ошибка"))),
    codeBlock("claude plugin marketplace add letofftv/ClaudeRepo\nclaude plugin install ui-studio@clauderepo")),

  el("section", { id: "states", class: "section stack gap-4" },
    el("div", { class: "section-head" }, el("h3", {}, "Состояния")),
    el("div", { class: "grid-2" },
      el("div", { class: "card" }, el("div", { class: "empty" }, icon("inbox"), el("h3", {}, "Задач ещё нет"),
        el("p", {}, "Перетащите файл в окно — пульт предложит, что с ним сделать."), el("button", { class: "btn", type: "button" }, "Загрузить файл"))),
      el("div", { class: "card stack" }, el("div", { class: "skeleton" }), el("div", { class: "skeleton" }), el("div", { class: "progress indeterminate" }, el("span", {}))))),
];

mount($("#main"), sections);
$(".g-progress").style.width = "42%";

window.addEventListener("load", () => {
  const card = $("#chart-card");
  const chart = timeChart(card, {
    series: [{ label: "Процессор", color: "--series-1", format: (v) => fmt.pct(v) }, { label: "Память", color: "--series-2", format: (v) => fmt.pct(v) }],
    yMax: 100, format: (v) => fmt.pct(v),
  });
  const times = cpu.map((_, i) => now - (cpu.length - i) * 5);
  const mem = cpu.map((_, i) => 55 + 10 * Math.cos(i / 9));
  chart.update(times, cpu, mem);
  card.append(el("details", { class: "mt-3" }, el("summary", {}, "Таблица"), chartTable(times, [cpu, mem], [{ label: "Процессор", format: (v) => fmt.pct(v) }, { label: "Память", format: (v) => fmt.pct(v) }])));
});
