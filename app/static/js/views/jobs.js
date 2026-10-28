// Задачи: список и карточка — результат первым, прогресс, «Дальше →», лог свёрнут.
import { el, icon, mount, fmt, toast, confirmDialog, poll } from "../../kit/ui.js";
import { api, live, subscribe, jobRow, stateBadge, progressText, mediaPreview, download, getTools, suggestionsFor,
  firstFileParam, runSheet, openSheet, toolIcon, fileType, refreshLive, TYPE_ICON } from "../core.js";

export const title = "Задачи";

const DEVICE = { gpu: "на видеокарте", cpu: "на процессоре" };

/** Where the job ran; a CPU run after a failed GPU attempt says so. */
function deviceText(job) {
  if (!DEVICE[job.device]) return "";
  const fellBack = job.device === "cpu" && (job.runs || []).some((r) => r.device === "gpu");
  return ` · ${DEVICE[job.device]}${fellBack ? " (видеокарта не справилась)" : ""}`;
}

export function render(main, params) {
  const jobId = params.id || null;
  const layout = el("div", { class: `jobs-layout${jobId ? " has-detail" : ""}` });
  const listBox = el("div", { class: "jobs-list stack gap-3" });
  const detail = el("div", { class: "stack gap-4" });
  mount(main, el("div", { class: "page-head" }, el("span", { class: "spacer" }),
    el("button", { class: "btn ghost sm", type: "button", onclick: cleanupSheet }, icon("hard-drive", { cls: "sm" }), "Место")), layout);
  mount(layout, listBox, jobId ? detail : el("div", { class: "card empty hide-sm" }, icon("list-checks"), el("h3", {}, "Выберите задачу"),
    el("p", {}, "Слева — все задачи, новые сверху. Идущие показывают прогресс.")));

  function renderList(state) {
    const jobs = state.jobs || [];
    mount(listBox, jobs.length ? el("div", { class: "card flush list" }, jobs.map((j) => jobRow(j, { current: j.id === jobId })))
      : el("div", { class: "card empty" }, icon("inbox"), el("h3", {}, "Задач ещё нет"),
        el("p", {}, "Запустите инструмент в разделе «Запуск» или перетащите файл в окно."), el("a", { class: "btn", href: "#/run" }, "К инструментам")));
  }

  let stopDetail = null;
  if (jobId) {
    let finished = false;
    stopDetail = poll(async () => {
      if (finished) return;
      try {
        const job = await api.get(`/api/jobs/${encodeURIComponent(jobId)}`);
        finished = !["queued", "running"].includes(job.state);
        await renderDetail(job);
      } catch (e) {
        mount(detail, el("a", { class: "back-link small", href: "#/jobs" }, "← Все задачи"),
          el("div", { class: "card empty" }, icon("circle-alert"), el("h3", {}, e.status === 404 ? "Задача не найдена" : "Не удалось загрузить задачу"),
            el("p", {}, e.status === 404 ? "Возможно, её удалили." : e.message)));
        finished = true;
      }
    }, 2000);
  }

  let rendered = "";
  async function renderDetail(job) {
    // re-render only when something visible changed: keeps the player and open sections intact
    const key = JSON.stringify([job.state, job.progress, job.files.length, job.log.length, job.error]);
    if (key === rendered) return;
    const first = !rendered;
    rendered = key;
    const running = ["queued", "running"].includes(job.state);
    const tools = await getTools();
    const actions = el("div", { class: "cluster" },
      running ? el("button", { class: "btn ghost", type: "button", onclick: () => cancel(job) }, icon("x", { cls: "sm" }), "Отменить") : null,
      !running ? el("button", { class: "btn ghost", type: "button", onclick: () => repeat(job, tools) }, icon("refresh-cw", { cls: "sm" }), "Повторить") : null,
      !running ? el("button", { class: "btn subtle", type: "button", onclick: () => remove(job) }, icon("trash-2", { cls: "sm" }), "Удалить") : null);
    const duration = job.started ? ((job.finished || Date.now() / 1000) - job.started) : null;
    const progressBar = el("span");
    if (job.progress) progressBar.style.width = `${job.progress.percent}%`;
    const logOpen = job.state === "failed";
    const log = el("pre", { class: "log" }, job.log || "—");
    const media = job.files.filter((f) => ["image", "video", "audio"].includes(fileType(f.name)));
    const previewBox = el("div", { class: "preview-box" });

    mount(detail,
      el("a", { class: "back-link small", href: "#/jobs" }, "← Все задачи"),
      el("div", { class: "card stack" },
        el("div", { class: "row top" }, icon(toolIcon(job.tool), { cls: "lg" }), el("div", { class: "grow stack gap-1" },
          el("h3", {}, job.title), el("span", { class: "small secondary" },
            `создана ${fmt.when(job.created)}${duration !== null ? ` · ${running ? "идёт" : "заняла"} ${fmt.duration(duration)}` : ""}${deviceText(job)}${job.returncode !== null && job.returncode !== undefined ? ` · код ${job.returncode}` : ""}`)),
          stateBadge(job.state)),
        running ? el("div", { class: "job-progress" }, el("div", { class: job.progress ? "progress" : "progress indeterminate" }, progressBar),
          el("span", { class: "small secondary nowrap" }, progressText(job.progress))) : null,
        job.error ? el("div", { class: "alert", "data-level": "crit" }, icon("circle-alert"), el("div", {}, el("div", { class: "alert-title" }, job.error))) : null,
        actions),
      job.report ? reportCard(job) : null,
      job.files.length ? el("div", { class: "card stack" }, el("div", { class: "card-head" }, el("h3", {}, "Результаты"), el("span", { class: "meta" }, `${job.files.length}`)),
        previewBox,
        el("div", { class: "list" }, job.files.map((f) => fileRow(f, tools, previewBox)))) : (running ? null : el("div", { class: "card" },
          el("p", { class: "secondary" }, job.state === "done" ? "Файлов нет — результат в логе ниже." : "Результатов нет."))),
      Object.keys(job.params || {}).length ? el("details", { class: "card" }, el("summary", {}, "Параметры"),
        el("dl", { class: "kv mt-2" }, Object.entries(job.params).flatMap(([k, v]) => [el("dt", {}, k), el("dd", { class: "mono" }, String(v).slice(0, 300))]))) : null,
      el("details", { class: "card", open: logOpen || running || null }, el("summary", {}, "Лог"), log));
    log.scrollTop = log.scrollHeight;
    if (first && media.length) showPreview(media[0], previewBox);
  }

  function fileRow(f, tools, previewBox) {
    const next = suggestionsFor(tools, f.name);
    return el("div", { class: "list-item" }, icon(TYPE_ICON[fileType(f.name)]),
      el("span", { class: "list-item-main" }, el("span", { class: "list-item-title" }, f.name), el("span", { class: "list-item-sub" }, fmt.bytes(f.size))),
      el("span", { class: "inline-actions" },
        el("button", { class: "btn ghost sm", type: "button", onclick: () => showPreview(f, previewBox) }, "Показать"),
        el("button", { class: "btn ghost sm icon-only", type: "button", "aria-label": `Скачать ${f.name}`, onclick: () => download(f.path) }, icon("download", { cls: "sm" })),
        next.length ? el("button", { class: "btn sm", type: "button", onclick: () => nextSheet(f, next) }, "Дальше", icon("arrow-right", { cls: "sm" })) : null));
  }

  async function showPreview(f, box) {
    try {
      const node = await mediaPreview(f.path);
      mount(box, node || el("p", { class: "secondary small" }, "Для этого файла предпросмотра нет — скачайте его."));
    } catch (e) { mount(box, el("p", { class: "error-text" }, e.message)); }
  }

  function nextSheet(f, next) {
    const dlg = openSheet({ title: "Что сделать дальше?", subtitle: f.name,
      body: el("div", { class: "card flush list" }, next.map((t) => el("button", { class: "list-item", type: "button",
        onclick: () => { dlg.close(); runSheet(t, { [firstFileParam(t).name]: f.path }); } },
        icon(toolIcon(t)), el("span", { class: "list-item-main" }, el("span", { class: "list-item-title" }, t.title), el("span", { class: "list-item-sub" }, t.description)),
        icon("chevron-right", { cls: "sm" })))) });
  }

  async function cancel(job) {
    try { await api.post(`/api/jobs/${job.id}/cancel`); toast("Задача отменяется"); refreshLive(); stopDetail?.now(); }
    catch (e) { toast(e.message, { level: "crit" }); }
  }

  async function repeat(job, tools) {
    const t = tools.find((x) => x.id === job.tool);
    if (!t) { toast("Этого инструмента больше нет", { level: "crit" }); return; }
    if (!t.available) { toast(`Инструмент недоступен: ${t.reason}`, { level: "crit" }); return; }
    runSheet(t, job.params || {});
  }

  async function remove(job) {
    if (!(await confirmDialog(`Удалить задачу «${job.title}» вместе с её результатами?`, { title: "Удалить задачу", okText: "Удалить", danger: true }))) return;
    try { await api.del(`/api/jobs/${job.id}`); toast("Задача удалена"); refreshLive(); location.hash = "#/jobs"; }
    catch (e) { toast(e.message, { level: "crit" }); }
  }

  async function cleanupSheet() {
    let usage = null;
    try { usage = await api.get("/api/jobs/usage"); } catch (e) { toast(e.message, { level: "crit" }); return; }
    const days = el("input", { class: "input", type: "number", min: 1, value: 30, id: "cleanup-days", inputmode: "numeric" });
    const go = el("button", { class: "btn danger", type: "button" }, icon("trash-2", { cls: "sm" }), "Удалить старые");
    const dlg = openSheet({ title: "Место под задачи", subtitle: `${usage.jobs} задач · ${usage.files} файлов · ${fmt.bytes(usage.bytes)}`,
      body: el("div", { class: "stack" }, el("p", { class: "secondary" }, "Удаляются только завершённые задачи с их результатами. Загруженные файлы остаются."),
        el("div", { class: "field" }, el("label", { for: "cleanup-days" }, "Старше, дней"), days)),
      actions: [el("button", { class: "btn ghost", type: "button", onclick: () => dlg.close() }, "Отмена"), go] });
    go.addEventListener("click", async () => {
      try {
        const res = await api.post("/api/jobs/cleanup", { older_than_days: Number(days.value) });
        dlg.close(); toast(`Удалено задач: ${res.deleted}`); refreshLive();
      } catch (e) { toast(e.message, { level: "crit" }); }
    });
  }

  const off = subscribe(renderList);
  renderList(live);
  return () => { off(); stopDetail?.stop(); };
}

// --- reports ------------------------------------------------------------------------------------
function metric(label, value, note, lvl) {
  return el("div", { class: "metric" }, el("div", { class: "metric-label" }, label), el("div", { class: "metric-value" }, value),
    note ? el("div", { class: "metric-note", "data-level": lvl || "" }, lvl === "ok" ? icon("check", { cls: "sm" }) : lvl ? icon("triangle-alert", { cls: "sm" }) : null, note) : null);
}

function reportCard(job) {
  if (job.tool === "loudness_report" && Array.isArray(job.report)) {
    return el("div", { class: "stack gap-4" }, job.report.map((r) => {
      const lufs = r.integrated_lufs;
      const tp = r.true_peak_dbtp;
      const dLufs = lufs !== null && r.target_lufs !== undefined ? lufs - r.target_lufs : null;
      const lufsLvl = dLufs === null ? "" : Math.abs(dLufs) <= 1 ? "ok" : "warn";
      const tpLvl = tp === null || r.tp_limit_dbtp === undefined ? "" : tp <= r.tp_limit_dbtp ? "ok" : "crit";
      return el("div", { class: "card stack" },
        el("div", { class: "card-head" }, el("h3", {}, "Громкость"), el("span", { class: "meta" }, r.role ? `роль: ${r.role}` : null)),
        el("div", { class: "metric-grid" },
          metric("Интегральная", lufs === null ? "—" : `${fmt.num(lufs, 1)} LUFS`, dLufs === null ? null : `цель ${fmt.num(r.target_lufs, 1)} · ${dLufs > 0 ? "+" : ""}${fmt.num(dLufs, 1)} дБ`, lufsLvl),
          metric("True peak", tp === null ? "—" : `${fmt.num(tp, 1)} dBTP`, r.tp_limit_dbtp !== undefined ? `предел ${fmt.num(r.tp_limit_dbtp, 1)}` : null, tpLvl),
          metric("PLR", r.plr_db === null ? "—" : `${fmt.num(r.plr_db, 1)} дБ`, "пик − громкость"),
          metric("LRA", r.lra_lu === null ? "—" : `${fmt.num(r.lra_lu, 1)} LU`, "диапазон громкости"),
          metric("Макс. кратковременная", r.max_short_term_lufs === null ? "—" : `${fmt.num(r.max_short_term_lufs, 1)} LUFS`)),
        r.verdicts?.length ? el("ul", { class: "verdicts" }, r.verdicts.map((v) => el("li", {}, v))) : null,
        el("p", { class: "hint" }, "Цифры — ориентир; решение — на слух."));
    }));
  }
  if (job.tool === "mix_compare" && job.report) {
    const r = job.report;
    const rows = [["Громкость, LUFS", "integrated_lufs"], ["True peak, dBTP", "true_peak_dbtp"], ["LRA, LU", "lra_lu"], ["PLR, дБ", "plr_db"]];
    const maxAbs = Math.max(6, ...(r.band_diff_db || []).map((d) => Math.abs(d)));
    return el("div", { class: "card stack" },
      el("div", { class: "card-head" }, el("h3", {}, "Микс против референса")),
      el("div", { class: "table-wrap" }, el("table", { class: "table" },
        el("thead", {}, el("tr", {}, el("th", {}, ""), el("th", { class: "num" }, "Микс"), el("th", { class: "num" }, "Референс"))),
        el("tbody", {}, rows.map(([label, key]) => el("tr", {}, el("td", {}, label),
          el("td", { class: "num" }, fmt.num(r.mix?.[key], 1)), el("td", { class: "num" }, fmt.num(r.reference?.[key], 1))))))),
      el("h4", {}, "Тональный баланс: разница с референсом"),
      el("div", { class: "stack gap-2" }, (r.bands || []).map((name, i) => {
        const d = r.band_diff_db[i];
        const fill = el("span", { class: "band-fill", "data-level": Math.abs(d) >= 2 ? "warn" : "" });
        const width = (Math.abs(d) / maxAbs) * 50;
        fill.style.left = d >= 0 ? "50%" : `${50 - width}%`;
        fill.style.width = `${width}%`;
        return el("div", { class: "band-row" }, el("span", { class: "secondary" }, name), el("div", { class: "band-track", "aria-hidden": "true" }, fill),
          el("span", { class: "band-value" }, `${d > 0 ? "+" : ""}${fmt.num(d, 1)} дБ`));
      })),
      r.hints?.length ? el("ul", { class: "verdicts" }, r.hints.map((h) => el("li", {}, h))) : el("p", { class: "secondary" }, "Заметных расхождений нет."),
      el("p", { class: "hint" }, "Сравнивайте на слух только после выравнивания громкости."));
  }
  return null;
}
