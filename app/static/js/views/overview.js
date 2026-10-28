// Обзор: «всё ли в порядке?» — итог, тревоги, ресурсы, готовность видеокарты, задачи.
import { el, icon, mount, fmt } from "../../kit/ui.js";
import { sparkline, meter } from "../../kit/charts.js";
import { live, subscribe, ensureHistory, LEVEL, alertItem, alertLevel, gpuReadiness, jobRow, pickFiles, getTools, runSheet } from "../core.js";

export const title = "Обзор";

export function liveMeta(m) {
  return el("span", { class: "live" },
    el("span", { class: "dot live", "data-level": m ? "ok" : "unknown" }),
    m ? el("span", {}, "обновлено ", el("span", { "data-ago": m.time }, fmt.ago(m.time))) : "ждём данные…");
}

export function statusHero(m, { link = true } = {}) {
  if (!m || !m.time) {
    return el("div", { class: "status-hero" }, el("div", { class: "skeleton grow" }));
  }
  const lvl = m.status === "ok" || m.status === "warn" || m.status === "crit" ? m.status : "unknown";
  const top = (m.alerts || []).filter((a) => a.level !== "info");
  const running = m.jobs?.running || 0;
  const text = `Работает ${fmt.duration(m.uptime_s)} · ${running ? `идёт задач: ${running}` : "задач нет"}`;
  const body = [icon(LEVEL[lvl].icon), el("div", { class: "grow" },
    el("h2", {}, lvl === "ok" ? LEVEL.ok.title : `${LEVEL[lvl].title}${top.length ? ` (${top.length})` : ""}`), el("p", {}, text))];
  return link
    ? el("a", { class: "status-hero", href: "#/server", "data-level": lvl }, body, icon("chevron-right", { cls: "sm" }))
    : el("div", { class: "status-hero", "data-level": lvl }, body);
}

/** Resource tiles shared by Обзор and Сервер; levels come from server alerts. */
export function resourceTiles(m, hist, { detailed = false } = {}) {
  if (!m || !m.time) return Array.from({ length: detailed ? 8 : 6 }, () => el("div", { class: "tile" }, el("div", { class: "skeleton" }), el("div", { class: "skeleton mt-2" })));
  const tiles = [];
  const spark = (values, opts) => el("div", { class: "tile-spark" }, sparkline(values || [], opts));
  const tile = (label, ic, value, unit, sub, lvl, extra, href = "#/server") =>
    el("a", { class: "tile", href, "data-level": lvl }, el("div", { class: "tile-label" }, icon(ic, { cls: "sm" }), label),
      el("div", { class: "tile-value" }, value, unit ? el("small", {}, unit) : null), el("div", { class: "tile-sub" }, sub), extra);
  const cpu = m.cpu || {};
  tiles.push(tile("Процессор", "cpu", fmt.num(cpu.percent, 0), "%",
    `нагрузка ${cpu.load ? fmt.num(cpu.load[0], 2) : "—"} · ${m.cpu_count} потоков`, alertLevel(m, "cpu"), spark(hist?.cpu, { max: 100 })));
  const mem = m.memory || {};
  tiles.push(tile("Память", "memory-stick", fmt.num(mem.used / 1024 ** 3, 1), "ГБ",
    `из ${fmt.bytes(mem.total)}${m.swap?.total ? ` · подкачка ${fmt.pct(m.swap.pct)}` : ""}`, alertLevel(m, "mem", "swap", "oom"),
    meter(mem.pct, alertLevel(m, "mem", "swap", "oom"), { label: "Занято памяти" })));
  const g = (m.gpus || [])[0];
  if (g) {
    const vramLvl = alertLevel(m, "vram");
    tiles.push(tile("Видеопамять", "gpu", fmt.num((g.mem_used_mb || 0) / 1024, 1), "ГБ",
      `из ${fmt.num((g.mem_total_mb || 0) / 1024, 1)} ГБ · свободно ${fmt.num((g.mem_total_mb || 0) - (g.mem_used_mb || 0), 0)} МБ`, vramLvl,
      meter(g.mem_pct, vramLvl, { label: "Занято видеопамяти" })));
    tiles.push(tile("Видеокарта", "thermometer", g.util === null ? "—" : fmt.num(g.util, 0), g.util === null ? "" : "%",
      `${fmt.temp(g.temp_c)}${g.power_w !== null ? ` · ${fmt.num(g.power_w, 0)} Вт` : ""}`, alertLevel(m, "gpu_temp", "gpu_error"),
      spark(hist?.gpu_temp, { min: 20, max: 100 })));
  } else {
    tiles.push(tile("Видеокарта", "gpu", "—", "", m.gpu_error || "nvidia-smi не найден", "unknown", null));
  }
  const work = (m.disks || []).find((d) => d.workdir) || (m.disks || [])[0];
  if (work) {
    const lvl = alertLevel(m, `disk:${work.path}`);
    tiles.push(tile(detailed ? `Диск ${work.path}` : "Рабочий диск", "hard-drive", fmt.num(work.free / 1024 ** 3, work.free > 100 * 1024 ** 3 ? 0 : 1), "ГБ",
      `свободно из ${fmt.bytes(work.total)}`, lvl, meter(100 - work.free_pct, lvl, { label: "Занято на диске" })));
  }
  tiles.push(tile("Сеть", "activity", fmt.rate(m.net?.rx_bps), "", `приём · передача ${fmt.rate(m.net?.tx_bps)}`, "ok", spark(hist?.rx)));
  if (detailed) {
    tiles.push(tile("Диск, чтение/запись", "hard-drive", fmt.rate(m.disk_io?.read_bps), "", `запись ${fmt.rate(m.disk_io?.write_bps)}`, "ok", spark(hist?.dw)));
    tiles.push(tile("Работает", "clock", fmt.duration(m.uptime_s), "", `${m.processes} процессов`, "ok", null));
  }
  return tiles;
}

export function readinessLine(m) {
  if (!m || !m.time) return null;
  const r = gpuReadiness(m);
  return el("div", { class: "ready", "data-level": r.level }, icon(r.level === "ok" ? "circle-check" : "triangle-alert"),
    el("div", { class: "grow" }, el("div", { class: "ready-title" }, r.title), el("div", { class: "small secondary" }, r.text)));
}

export function render(main) {
  const meta = el("span");
  const head = el("div", { class: "page-head" }, meta);
  const hero = el("div");
  const alerts = el("div", { class: "stack gap-2" });
  const tiles = el("div", { class: "tiles" });
  const ready = el("div");
  const running = el("div");
  const recent = el("div");
  const actions = el("div", { class: "card stack" },
    el("div", { class: "card-head" }, el("h3", {}, "Быстрые действия")),
    el("button", { class: "btn block", type: "button", onclick: () => pickFiles() }, icon("upload", { cls: "sm" }), "Загрузить файл"),
    el("button", { class: "btn ghost block", type: "button", onclick: () => quickTool("loudness_report") }, icon("audio-waveform", { cls: "sm" }), "Проверить громкость"),
    el("a", { class: "btn ghost block", href: "#/run" }, icon("wrench", { cls: "sm" }), "Все инструменты"),
    el("p", { class: "hint" }, "Файл можно просто перетащить в окно — пульт предложит, что с ним сделать."));
  mount(main, head, hero, el("div", { class: "mt-3" }, alerts),
    el("div", { class: "section-head mt-6" }, el("h3", {}, "Ресурсы"), el("a", { href: "#/server" }, "Подробно")), tiles,
    el("div", { class: "mt-3" }, ready),
    el("div", { class: "cols section" }, el("div", { class: "stack gap-4" }, running, recent), actions));

  let hist = null;
  ensureHistory().then((h) => { hist = h; update(live); }).catch(() => {});

  function update(state) {
    const m = state.metrics;
    mount(meta, liveMeta(m));
    mount(hero, statusHero(m));
    const list = (m?.alerts || []).filter((a) => a.level !== "info");
    mount(alerts, list.slice(0, 3).map(alertItem),
      list.length > 3 ? el("a", { class: "small", href: "#/server" }, `Все тревоги: ${list.length}`) : null);
    mount(tiles, resourceTiles(m, hist));
    mount(ready, readinessLine(m));
    const active = state.jobs.filter((j) => j.state === "running" || j.state === "queued");
    mount(running, active.length ? listCard("Идёт сейчас", null, el("div", { class: "list" }, active.map((j) => jobRow(j)))) : null);
    const done = state.jobs.filter((j) => !["running", "queued"].includes(j.state)).slice(0, 5);
    mount(recent, listCard("Свежие результаты", el("a", { href: "#/jobs" }, "Все задачи"),
      done.length ? el("div", { class: "list" }, done.map((j) => jobRow(j)))
        : el("div", { class: "empty" }, icon("inbox"), el("h3", {}, "Задач ещё нет"),
          el("p", {}, "Перетащите файл в окно или нажмите «Загрузить файл»."))));
  }

  const off = subscribe(update);
  update(live);
  return off;
}

export function listCard(heading, link, content) {
  return el("div", { class: "card flush" }, el("div", { class: "card-head list-head" }, el("h3", {}, heading), link), content);
}

async function quickTool(id) {
  const tools = await getTools();
  const t = tools.find((x) => x.id === id);
  if (t) runSheet(t);
}
