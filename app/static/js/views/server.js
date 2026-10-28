// Сервер: живая панель — ресурсы, история, видеокарта, диски, службы, контейнеры, процессы, версия.
import { el, icon, mount, fmt, level, toast, codeBlock } from "../../kit/ui.js";
import { meter, timeChart, chartTable } from "../../kit/charts.js";
import { api, live, subscribe, appendPoint, pointOf, alertItem, alertLevel, getTools, uiConfig, refreshLive } from "../core.js";
import { liveMeta, statusHero, resourceTiles, readinessLine } from "./overview.js";

export const title = "Сервер";

const RANGES = [["15m", "15 мин", 900], ["1h", "1 ч", 3600], ["6h", "6 ч", 21600], ["24h", "24 ч", 86400]];
const pct = (v) => fmt.pct(v);
const CHARTS = [
  { key: "cpu", title: "Процессор, %", yMax: 100, format: pct, series: [{ label: "Процессор", col: "cpu", color: "--series-1" }] },
  { key: "mem", title: "Память, %", yMax: 100, format: pct,
    series: [{ label: "Оперативная", col: "mem", color: "--series-1" }, { label: "Подкачка", col: "swap", color: "--series-2" }] },
  { key: "gpu", title: "Видеокарта, %", yMax: 100, format: pct, gpu: true,
    series: [{ label: "Загрузка", col: "gpu", color: "--series-1" }, { label: "Видеопамять", col: "vram", color: "--series-2" }] },
  { key: "temp", title: "Температура видеокарты", yMin: 20, yMax: 100, format: (v) => fmt.temp(v), gpu: true,
    series: [{ label: "Температура", col: "gpu_temp", color: "--series-1" }] },
  { key: "net", title: "Сеть", yMax: null, format: (v) => fmt.rate(v),
    series: [{ label: "Приём", col: "rx", color: "--series-1" }, { label: "Передача", col: "tx", color: "--series-2" }] },
  { key: "disk", title: "Диск", yMax: null, format: (v) => fmt.rate(v),
    series: [{ label: "Чтение", col: "dr", color: "--series-1" }, { label: "Запись", col: "dw", color: "--series-2" }] },
];

function card(heading, meta, ...content) {
  return el("div", { class: "card" }, el("div", { class: "card-head" }, el("h3", {}, heading), meta ? el("span", { class: "meta" }, meta) : null), ...content);
}

function kv(rows) {
  return el("dl", { class: "kv" }, rows.filter(Boolean).flatMap(([k, v]) => [el("dt", {}, k), el("dd", {}, v)]));
}

export function render(main, params, query) {
  let range = RANGES.some(([k]) => k === query.range) ? query.range : "15m";
  let series = null;
  let lastFetch = 0;
  const charts = {};
  const chartNow = {};
  const chartTables = {};

  const meta = el("span");
  const badges = el("span", { class: "badges" });
  const hero = el("div");
  const alerts = el("div", { class: "stack gap-2" });
  const wsl = el("div");
  const tiles = el("div", { class: "tiles" });
  const ready = el("div");
  const seg = el("div", { class: "seg", role: "group", "aria-label": "Период графиков" });
  const chartGrid = el("div", { class: "grid-2" });
  const cores = el("div");
  const gpu = el("div");
  const disks = el("div");
  const services = el("div");
  const docker = el("div");
  const procCpu = el("div");
  const procMem = el("div");
  const system = el("div");
  const links = el("div");

  mount(main,
    el("div", { class: "page-head" }, badges, el("span", { class: "spacer" }), meta),
    hero, el("div", { class: "mt-3 stack gap-2" }, alerts, wsl),
    el("div", { class: "section-head mt-6" }, el("h3", {}, "Сейчас")), tiles, el("div", { class: "mt-3" }, ready),
    el("div", { class: "filter-row" }, el("h3", {}, "История"), seg), chartGrid,
    el("div", { class: "grid-2 section" }, cores, gpu),
    el("div", { class: "section" }, disks),
    el("div", { class: "grid-2 section" }, services, docker),
    el("div", { class: "grid-2 section" }, procCpu, procMem),
    el("div", { class: "grid-2 section" }, system, links));

  function renderSeg() {
    mount(seg, RANGES.map(([k, label]) => el("button", { type: "button", "aria-pressed": String(k === range),
      onclick: () => { if (k !== range) { range = k; history.replaceState(null, "", `#/server?range=${k}`); renderSeg(); loadRange(); } } }, label)));
  }
  renderSeg();

  function buildCharts(hasGpu) {
    for (const c of CHARTS) {
      if (c.gpu && !hasGpu) continue;
      const now = el("span", { class: "now" });
      const tableBox = el("div");
      const details = el("details", {}, el("summary", {}, "Таблица"), tableBox);
      details.addEventListener("toggle", () => { if (details.open) renderTable(c.key); });
      const box = el("div", { class: "card chart-card" }, el("div", { class: "card-head" }, el("h4", {}, c.title), now));
      chartGrid.append(box);
      charts[c.key] = timeChart(box, { series: c.series, yMin: c.yMin ?? 0, yMax: c.yMax, format: c.format, height: 170 });
      box.append(details);
      chartNow[c.key] = now;
      chartTables[c.key] = { details, tableBox };
    }
  }

  function renderTable(key) {
    const c = CHARTS.find((x) => x.key === key);
    const t = chartTables[key];
    if (!c || !t || !series) return;
    mount(t.tableBox, chartTable(series.t, c.series.map((s) => series[s.col] || []), c.series.map((s) => ({ label: s.label, format: c.format }))));
  }

  function pushCharts() {
    if (!series) return;
    for (const c of CHARTS) {
      if (!charts[c.key]) continue;
      charts[c.key].update(series.t, ...c.series.map((s) => series[s.col] || []));
      if (chartTables[c.key].details.open) renderTable(c.key);
    }
  }

  async function loadRange() {
    Object.values(charts).forEach((ch) => ch.setStale(true));
    try {
      const res = await api.get(`/api/metrics/history?range=${range}`);
      series = res.series;
      lastFetch = Date.now();
      pushCharts();
    } catch (e) {
      toast(`История не загрузилась: ${e.message}`, { level: "crit" });
    } finally {
      Object.values(charts).forEach((ch) => ch.setStale(false));
    }
  }

  let built = false;
  function update(state) {
    const m = state.metrics;
    mount(meta, liveMeta(m));
    if (!m || !m.time) { mount(hero, statusHero(null)); mount(tiles, resourceTiles(null, null, { detailed: true })); return; }
    if (!built) { built = true; buildCharts((m.gpus || []).length > 0); loadRange(); }
    mount(badges, el("span", { class: "badge" }, m.host), m.wsl ? el("span", { class: "badge", "data-level": "info" }, "WSL2") : null);
    mount(hero, statusHero(m, { link: false }));
    mount(alerts, (m.alerts || []).map(alertItem));
    mount(wsl, m.wsl ? el("details", { class: "card" }, el("summary", {}, "Особенности WSL2: что показывают цифры"),
      el("p", { class: "secondary small mt-2" }, "Пульт работает внутри WSL2. Память, подкачка и диск «/» — это виртуальная машина: её лимит задаётся в .wslconfig, а «/» показывает размер виртуального диска, а не реальное место. Настоящее свободное место Windows — на /mnt/c и /mnt/d. Загрузка видеокарты и список процессов на ней в WSL могут быть недоступны, температура процессора не видна.")) : null);
    const hist = range === "15m" && series ? series : live.history;
    mount(tiles, resourceTiles(m, hist, { detailed: true }));
    mount(ready, readinessLine(m));

    // charts: append live points for short ranges, refetch long ones once a minute
    const span = RANGES.find(([k]) => k === range)[2];
    if (series && (range === "15m" || range === "1h")) { if (appendPoint(series, pointOf(m), span)) pushCharts(); }
    else if (series && Date.now() - lastFetch > 60000) loadRange();
    const p = pointOf(m);
    for (const c of CHARTS) {
      if (chartNow[c.key]) chartNow[c.key].textContent = c.series.map((s) => `${c.series.length > 1 ? s.label.toLowerCase() + " " : ""}${p[s.col] === null || p[s.col] === undefined ? "—" : c.format(p[s.col])}`).join(" · ");
    }

    renderCores(m);
    renderGpu(m);
    renderDisks(m);
    renderServices(m);
    renderDocker(m);
    renderProcesses(m);
    renderSystem(m);
  }

  function renderCores(m) {
    const cpu = m.cpu || {};
    mount(cores, card("Процессор", `${m.cpu_count} потоков`,
      el("div", { class: "bars" }, (cpu.per_core || []).map((v, i) => el("div", { class: "bar-row" },
        el("span", { class: "label" }, `Поток ${i + 1}`), meter(v, level(v, 80, 95), { size: "sm", label: `Поток ${i + 1}` }), el("span", { class: "value" }, fmt.pct(v))))),
      el("div", { class: "mt-4" }, kv([
        ["Нагрузка 1 / 5 / 15 мин", cpu.load ? cpu.load.map((v) => fmt.num(v, 2)).join(" / ") : "—"],
        ["Среднее за 5 мин", cpu.avg_window !== null && cpu.avg_window !== undefined ? fmt.pct(cpu.avg_window) : "копится"],
        ["Температура", cpu.temp_c !== null && cpu.temp_c !== undefined ? fmt.temp(cpu.temp_c) : (m.wsl ? "не видна из WSL" : "датчик не найден")],
      ]))));
  }

  function renderGpu(m) {
    const g = (m.gpus || [])[0];
    if (!g) {
      mount(gpu, card("Видеокарта", null, el("div", { class: "empty" }, icon("gpu"), el("h3", {}, "Видеокарта не видна"),
        el("p", {}, m.gpu_error || "На сервере нет nvidia-smi — проверьте драйвер NVIDIA."))));
      return;
    }
    const free = g.mem_total_mb !== null && g.mem_used_mb !== null ? g.mem_total_mb - g.mem_used_mb : null;
    const procs = m.gpu_procs || [];
    mount(gpu, card("Видеокарта", g.pstate ? `режим ${g.pstate}` : null,
      kv([["Модель", g.name], ["Драйвер", g.driver],
        ["Загрузка", g.util === null ? "нет данных" : fmt.pct(g.util)],
        ["Видеопамять", `${fmt.num(g.mem_used_mb, 0)} из ${fmt.num(g.mem_total_mb, 0)} МБ${free !== null ? ` · свободно ${fmt.num(free, 0)} МБ` : ""}`],
        ["Температура", fmt.temp(g.temp_c)],
        ["Питание", g.power_w === null ? "нет данных" : `${fmt.num(g.power_w, 0)}${g.power_limit_w ? ` из ${fmt.num(g.power_limit_w, 0)}` : ""} Вт`],
        ["Вентилятор", g.fan_pct === null ? "нет данных" : fmt.pct(g.fan_pct)],
        ["Частота", g.clock_mhz === null ? "—" : `${fmt.num(g.clock_mhz, 0)}${g.clock_max_mhz ? ` из ${fmt.num(g.clock_max_mhz, 0)}` : ""} МГц`]]),
      el("h4", { class: "mt-4 mb-2" }, "Процессы на видеокарте"),
      procs.length
        ? el("table", { class: "table" }, el("tbody", {}, procs.map((p) => el("tr", {}, el("td", {}, p.name), el("td", { class: "num" }, p.mem_mb === null ? "—" : `${fmt.num(p.mem_mb, 0)} МБ`)))))
        : el("p", { class: "secondary small" }, m.wsl ? "В WSL2 список процессов видеокарты недоступен." : "Сейчас никто не использует видеокарту.")));
  }

  function renderDisks(m) {
    mount(disks, card("Диски", `${(m.disks || []).length}`,
      el("div", { class: "stack" }, (m.disks || []).map((d) => {
        const lvl = alertLevel(m, `disk:${d.path}`);
        return el("div", { class: "stack gap-1" },
          el("div", { class: "row between" }, el("span", { class: "row gap-2" }, icon("hard-drive", { cls: "sm" }), el("strong", {}, d.path),
            d.workdir ? el("span", { class: "badge", "data-level": "info" }, "рабочая папка") : null),
            el("span", { class: "small secondary" }, `свободно ${fmt.bytes(d.free)} из ${fmt.bytes(d.total)} · ${fmt.pct(d.free_pct)}`)),
          meter(100 - d.free_pct, lvl, { label: `Занято на ${d.path}` }));
      }))));
  }

  function renderServices(m) {
    const list = m.services || [];
    mount(services, card("Службы", list.length ? `${list.filter((s) => s.ok).length} из ${list.length} в порядке` : null,
      list.length
        ? el("div", { class: "list" }, list.map((s) => {
          const lvl = s.ok ? "ok" : (s.fails || 0) >= 3 ? "crit" : "warn";
          return el("div", { class: "list-item" }, el("span", { class: "dot", "data-level": lvl }),
            el("span", { class: "list-item-main" }, el("span", { class: "list-item-title" }, s.name),
              el("span", { class: "list-item-sub" }, `${s.kind} · ${s.state || "нет ответа"}`)),
            el("span", { class: "list-item-meta" }, s.latency_ms !== null && s.latency_ms !== undefined ? `${fmt.num(s.latency_ms, 0)} мс` : (s.ok ? "ок" : `сбоев подряд: ${s.fails || 1}`)));
        }))
        : el("div", { class: "stack" }, el("p", { class: "secondary small" }, "Проверки не настроены. Добавьте их в config/hub.json — пульт будет показывать, что работает, и поднимать тревогу, когда служба не отвечает:"),
          codeBlock('"services": [\n  {"name": "Postgres", "tcp": "127.0.0.1:5432"},\n  {"name": "Redis", "tcp": "127.0.0.1:6379"},\n  {"name": "Ollama", "http": "http://127.0.0.1:11434/api/version"},\n  {"name": "Ферма", "docker": "имя-контейнера"}\n]'))));
  }

  function renderDocker(m) {
    const list = m.docker;
    if (list === null || list === undefined) {
      mount(docker, card("Контейнеры", null, el("p", { class: "secondary small" }, "Docker не отвечает или не установлен для пользователя пульта.")));
      return;
    }
    const running = list.filter((c) => c.state === "running").length;
    mount(docker, card("Контейнеры", `${running} из ${list.length} запущено`,
      list.length ? el("div", { class: "list" }, list.map((c) => {
        const lvl = c.health === "unhealthy" ? "crit" : c.state === "running" ? "ok" : c.state === "restarting" ? "warn" : "unknown";
        return el("div", { class: "list-item" }, el("span", { class: "dot", "data-level": lvl }),
          el("span", { class: "list-item-main" }, el("span", { class: "list-item-title" }, c.name), el("span", { class: "list-item-sub" }, c.image)),
          el("span", { class: "list-item-meta" }, c.status));
      })) : el("p", { class: "secondary small" }, "Контейнеров нет.")));
  }

  function renderProcesses(m) {
    const table = (rows, mainCol) => el("table", { class: "table" },
      el("thead", {}, el("tr", {}, el("th", {}, "Процесс"), el("th", { class: "num" }, "Процессор"), el("th", { class: "num" }, "Память"))),
      el("tbody", {}, rows.map((p) => el("tr", {}, el("td", {}, `${p.name}${p.count > 1 ? ` ×${p.count}` : ""}`),
        el("td", { class: "num" }, fmt.pct(p.cpu, 1)), el("td", { class: "num" }, fmt.bytes(p.rss))))));
    mount(procCpu, card("Больше всего процессора", `всего процессов: ${m.processes}`, el("div", { class: "table-wrap" }, table(m.top_cpu || []))));
    mount(procMem, card("Больше всего памяти", null, el("div", { class: "table-wrap" }, table(m.top_mem || []))));
  }

  const RESULT = { updated: "обновлён", "up-to-date": "свежая версия", "tests-failed": "новая версия не прошла тесты", error: "ошибка обновления", "local-changes": "в клоне правки — обновление стоит" };
  let updateTool = null;
  getTools().then((t) => { updateTool = t.find((x) => x.id === "update_now" && x.available) || null; if (live.metrics) renderSystem(live.metrics); }).catch(() => {});
  function renderSystem(m) {
    const u = m.update;
    mount(system, card("Система и пульт", null,
      kv([["Хост", m.host], ["Система", `${m.system}${m.wsl ? " (WSL2)" : ""}`], ["Python", m.python],
        ["Работает", fmt.duration(m.uptime_s)],
        ["Версия пульта", `${m.version}${m.repo?.commit ? ` · ${m.repo.commit}` : ""}${m.repo?.date ? ` от ${new Date(m.repo.date).toLocaleDateString("ru-RU")}` : ""}`],
        ["Обновление", u ? `${RESULT[u.result] || u.result} · ${fmt.ago(u.time)}` : "обновлятор не настроен"],
        u && u.message && u.result !== "up-to-date" ? ["Подробности", u.message] : null]),
      updateTool ? el("button", { class: "btn ghost mt-4", type: "button", onclick: async (e) => {
        e.currentTarget.setAttribute("aria-busy", "true");
        try { await api.post("/api/jobs", { tool: "update_now", params: {} }); toast("Проверка обновлений запущена"); refreshLive(); }
        catch (err) { toast(err.message, { level: "crit" }); }
      } }, icon("refresh-cw", { cls: "sm" }), "Обновить сейчас") : null));
  }

  uiConfig().then((cfg) => {
    const list = cfg.links || [];
    mount(links, card("Другие панели", null, list.length
      ? el("div", { class: "list" }, list.map((l) => el("a", { class: "list-item", href: l.url, target: "_blank", rel: "noopener noreferrer" },
        icon("external-link"), el("span", { class: "list-item-main" }, el("span", { class: "list-item-title" }, l.title), el("span", { class: "list-item-sub" }, l.url)))))
      : el("div", { class: "stack" }, el("p", { class: "secondary small" }, "Для глубокой истории (30 дней, графики по контейнерам) и логов можно поставить рядом Beszel и Dozzle и добавить ссылки в config/hub.json:"),
        codeBlock('"links": [\n  {"title": "Beszel — история за 30 дней", "url": "http://<адрес>:8090"},\n  {"title": "Dozzle — логи контейнеров", "url": "http://<адрес>:8080"}\n]'))));
  }).catch(() => {});

  const off = subscribe(update);
  update(live);
  return () => { off(); Object.values(charts).forEach((c) => c.destroy()); };
}
