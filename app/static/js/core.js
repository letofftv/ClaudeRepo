// Shared state and flows of the hub UI: API, live data, files, tools, sheets.
import { el, icon, mount, createApi, poll, toast, fmt } from "../kit/ui.js";

export const api = createApi({
  tokenKey: "hub-token",
  onUnauthorized: () => window.dispatchEvent(new Event("hub:unauthorized")),
});

// --- live data: one poller for metrics + jobs, views subscribe ------------------------
const subscribers = new Set();
export const live = { metrics: null, jobs: [], lastOk: 0, error: null, history: null, ui: null };
let poller = null;
const HIST_KEYS = ["cpu", "mem", "swap", "gpu", "vram", "gpu_temp", "rx", "tx", "dr", "dw"];

export function startLive() {
  if (poller) return;
  poller = poll(async () => {
    try {
      const [metrics, jobs] = await Promise.all([api.get("/api/metrics"), api.get("/api/jobs")]);
      live.metrics = metrics;
      live.jobs = jobs;
      live.lastOk = Date.now();
      live.error = null;
      appendPoint(live.history, pointOf(metrics), 900);
    } catch (e) {
      live.error = e;
    }
    for (const fn of subscribers) {
      try { fn(live); } catch (e) { console.error(e); }
    }
  }, 3000);
}

export function stopLive() { if (poller) { poller.stop(); poller = null; } }
export function refreshLive() { if (poller) poller.now(); }
export function subscribe(fn) {
  subscribers.add(fn);
  if (live.lastOk || live.error) fn(live);
  return () => subscribers.delete(fn);
}
export const isStale = () => !live.lastOk || Date.now() - live.lastOk > 15000;

export function pointOf(m) {
  if (!m || !m.time) return null;
  const g = (m.gpus || [])[0] || {};
  return { t: m.time, cpu: m.cpu?.percent, mem: m.memory?.pct, swap: m.swap?.pct, gpu: g.util, vram: g.mem_pct,
    gpu_temp: g.temp_c, rx: m.net?.rx_bps, tx: m.net?.tx_bps, dr: m.disk_io?.read_bps, dw: m.disk_io?.write_bps };
}

/** Append a live point to columnar history, dropping what falls out of the window (seconds). */
export function appendPoint(series, point, window) {
  if (!series || !point) return false;
  const last = series.t[series.t.length - 1];
  if (last && point.t - last < 1) return false;
  series.t.push(point.t);
  for (const k of HIST_KEYS) (series[k] ||= []).push(point[k] ?? null);
  const cutoff = point.t - window;
  while (series.t.length && series.t[0] < cutoff) { series.t.shift(); for (const k of HIST_KEYS) series[k]?.shift(); }
  return true;
}

export async function ensureHistory() {
  if (!live.history) live.history = (await api.get("/api/metrics/history?range=15m")).series;
  return live.history;
}

export async function uiConfig() {
  if (!live.ui) live.ui = await api.get("/api/ui");
  return live.ui;
}

// --- health helpers ------------------------------------------------------------------------
export const LEVEL = {
  ok: { title: "Всё в порядке", icon: "circle-check" },
  warn: { title: "Есть замечания", icon: "triangle-alert" },
  crit: { title: "Есть проблемы", icon: "circle-alert" },
  unknown: { title: "Нет данных", icon: "hourglass" },
};
const ORDER = { crit: 3, warn: 2, info: 1, ok: 0 };

/** Worst alert level whose id starts with one of the prefixes ("ok" when none). */
export function alertLevel(m, ...prefixes) {
  let worst = "ok";
  for (const a of m?.alerts || []) {
    if (prefixes.some((p) => a.id === p || a.id.startsWith(p + ":")) && ORDER[a.level] > ORDER[worst]) worst = a.level;
  }
  return worst === "info" ? "ok" : worst;
}

export function alertItem(a) {
  const ic = a.level === "crit" ? "circle-alert" : a.level === "warn" ? "triangle-alert" : "info";
  const since = Math.max(0, Date.now() / 1000 - a.since);
  return el("div", { class: "alert", "data-level": a.level },
    icon(ic),
    el("div", { class: "grow" },
      el("div", { class: "alert-title" }, a.title),
      el("div", { class: "alert-meta" }, `с ${fmt.time(a.since)}${since > 60 ? ` · ${fmt.duration(since)}` : ""}`)));
}

/** GPU readiness for the next heavy job: reasons it should wait, or none. */
export function gpuReadiness(m) {
  const g = (m?.gpus || [])[0];
  if (!g) return { level: "warn", title: "Видеокарта не видна", text: m?.gpu_error || "nvidia-smi не найден на сервере" };
  const reasons = [];
  const free = g.mem_total_mb && g.mem_used_mb !== null ? g.mem_total_mb - g.mem_used_mb : null;
  if (free !== null && free < 1024) reasons.push(`свободно ${fmt.num(free, 0)} МБ видеопамяти`);
  if (g.temp_c !== null && g.temp_c >= 80) reasons.push(`температура ${fmt.temp(g.temp_c)}`);
  const running = (m.jobs && m.jobs.running) || 0;
  if (running) reasons.push(running === 1 ? "идёт задача пульта" : `идут задачи пульта: ${running}`);
  const work = (m.disks || []).find((d) => d.workdir);
  if (work && work.free < 30 * 1024 ** 3) reasons.push(`на рабочем диске ${fmt.bytes(work.free)}`);
  const facts = [free !== null ? `${fmt.bytes(free * 1024 ** 2)} видеопамяти свободно` : null,
    g.temp_c !== null ? fmt.temp(g.temp_c) : null, g.util !== null ? `загрузка ${fmt.pct(g.util)}` : null].filter(Boolean).join(" · ");
  return reasons.length
    ? { level: "warn", title: "Видеокарту лучше не нагружать", text: reasons.join(" · ") }
    : { level: "ok", title: "Видеокарта свободна", text: facts };
}

// --- files and tools ------------------------------------------------------------------------
const EXT = {
  audio: ["wav", "mp3", "flac", "aif", "aiff", "m4a", "aac", "ogg", "opus", "wma"],
  video: ["mp4", "mov", "mkv", "webm", "avi", "m4v", "mxf", "mts"],
  image: ["png", "jpg", "jpeg", "webp", "gif", "bmp", "tif", "tiff"],
  subtitles: ["srt", "ass", "vtt"],
  text: ["txt", "json", "md", "csv", "log", "xml", "edl"],
};
export const TYPE_ICON = { audio: "file-audio", video: "file-video", image: "image", subtitles: "captions", text: "file-text", other: "file" };
export const TYPE_LABEL = { audio: "аудио", video: "видео", image: "картинка", subtitles: "субтитры", text: "текст", other: "файл" };
export function fileType(name) {
  const ext = String(name).split(".").pop().toLowerCase();
  return Object.keys(EXT).find((t) => EXT[t].includes(ext)) || "other";
}
export const basename = (p) => String(p).split("/").pop();

export const GROUPS = { audio: "Аудио", video: "Видео", generation: "Генерация", system: "Система" };
const TOOL_ICON = {
  loudness_report: "audio-waveform", mix_compare: "sliders-horizontal", loudnorm: "music", to_wav48: "file-audio",
  to_wav16_mono: "file-audio", silence_detect: "search", transcode_x264: "film", transcode_nvenc: "zap",
  vertical_9x16: "video", burn_subtitles: "captions", contact_sheet: "layers", thumbnail: "image", trim: "scissors",
  gif_preview: "image", auto_editor_cut: "scissors", auto_editor_premiere: "file-video", scene_detect: "film",
  upscale_video2x: "sparkles", stems: "layers", tts: "audio-waveform", whisper: "captions", sd_image: "sparkles",
  update_now: "refresh-cw",
};
const GROUP_ICON = { audio: "music", video: "video", generation: "sparkles", system: "settings" };
export const toolIcon = (idOrTool) => {
  const t = typeof idOrTool === "string" ? { id: idOrTool } : idOrTool;
  return TOOL_ICON[t.id] || GROUP_ICON[t.group] || "wrench";
};

let toolsCache = null;
export async function getTools(force = false) {
  if (!toolsCache || force) toolsCache = await api.get("/api/tools");
  return toolsCache;
}
export const firstFileParam = (tool) => tool.params.find((p) => p.type === "file");

export function suggestionsFor(tools, name) {
  const type = fileType(name);
  return tools.filter((t) => t.available && (firstFileParam(t)?.accept || []).includes(type));
}

export async function fileLink(path, inline = false) {
  const d = await api.get("/api/link?path=" + encodeURIComponent(path));
  return inline ? d.inline_url : d.url;
}

export async function download(path) {
  try {
    const a = el("a", { href: await fileLink(path), download: "" });
    document.body.append(a);
    a.click();
    a.remove();
  } catch (e) { toast(e.message, { level: "crit" }); }
}

/** Inline preview for media and text results; null when there is nothing to show. */
export async function mediaPreview(path) {
  const type = fileType(path);
  if (!["image", "video", "audio", "subtitles", "text"].includes(type)) return null;
  const url = await fileLink(path, true);
  if (type === "image") return el("img", { class: "media", src: url, alt: basename(path) });
  if (type === "video") return el("video", { class: "media", src: url, controls: true, playsinline: true, preload: "metadata" });
  if (type === "audio") return el("audio", { class: "media", src: url, controls: true, preload: "metadata" });
  const res = await fetch(url);
  return el("pre", { class: "log" }, (await res.text()).slice(0, 20000));
}

// --- sheets (bottom sheet on phones, dialog on desktop) -----------------------------------------
export function openSheet({ title, subtitle = "", body, actions = [], onClose }) {
  const dlg = el("dialog", { class: "sheet", "aria-label": title });
  const close = el("button", { class: "btn subtle icon-only", type: "button", "aria-label": "Закрыть", onclick: () => dlg.close() }, icon("x"));
  mount(dlg,
    el("div", { class: "sheet-head" },
      el("div", { class: "grow stack gap-1" }, el("h3", {}, title), subtitle ? el("p", { class: "secondary small" }, subtitle) : null),
      close),
    el("div", { class: "sheet-body" }, body),
    actions.length ? el("div", { class: "sheet-actions" }, actions) : null);
  dlg.addEventListener("close", () => { dlg.remove(); if (onClose) onClose(); });
  dlg.addEventListener("click", (e) => { if (e.target === dlg) dlg.close(); }); // tap on the backdrop
  document.body.append(dlg);
  dlg.showModal();
  return dlg;
}

// --- upload → «что сделать с файлом» → форма запуска ----------------------------------------------
export async function uploadFiles(fileList, { suggest = true } = {}) {
  const files = Array.from(fileList || []);
  if (!files.length) return [];
  const rows = files.map((f) => {
    const bar = el("span");
    const label = el("span", { class: "small secondary" }, `${f.name} · ${fmt.bytes(f.size)}`);
    return { f, bar, label, node: el("div", { class: "stack gap-1" }, label, el("div", { class: "progress" }, bar)) };
  });
  const dlg = openSheet({ title: files.length > 1 ? `Загрузка: ${files.length} файла` : "Загрузка файла", body: el("div", { class: "stack" }, rows.map((r) => r.node)) });
  const done = [];
  for (const r of rows) {
    try {
      const info = await api.upload("/api/files/" + encodeURIComponent(r.f.name), r.f, (p) => { r.bar.style.width = `${Math.round(p * 100)}%`; });
      r.bar.style.width = "100%";
      done.push(info);
    } catch (e) {
      r.label.textContent = `${r.f.name}: ${e.message}`;
      r.label.className = "small error-text";
    }
  }
  if (done.length) {
    dlg.close();
    toast(done.length > 1 ? `Загружено файлов: ${done.length}` : `Загружено: ${done[0].name}`);
    window.dispatchEvent(new Event("hub:files"));
    if (suggest) suggestSheet(done[done.length - 1]);
  }
  return done;
}

export function pickFiles(onPicked = uploadFiles) {
  const input = el("input", { type: "file", multiple: true, class: "visually-hidden", "aria-hidden": "true", tabindex: "-1" });
  input.addEventListener("change", () => { onPicked(input.files); input.remove(); });
  document.body.append(input);
  input.click();
}

export async function suggestSheet(file) {
  const tools = await getTools();
  const list = suggestionsFor(tools, file.name);
  const type = fileType(file.name);
  const dlg = openSheet({
    title: "Что сделать с файлом?",
    subtitle: `${file.name} · ${TYPE_LABEL[type]}`,
    body: list.length
      ? el("div", { class: "card flush list" }, list.map((t) => el("button", {
        class: "list-item", type: "button",
        onclick: () => { dlg.close(); runSheet(t, { [firstFileParam(t).name]: file.path }); },
      }, icon(toolIcon(t)), el("span", { class: "list-item-main" }, el("span", { class: "list-item-title" }, t.title),
        el("span", { class: "list-item-sub" }, t.description)), icon("chevron-right", { cls: "sm" }))))
      : el("div", { class: "empty" }, icon("inbox"), el("h3", {}, "Подходящих инструментов нет"),
        el("p", {}, "Для такого типа файла на сервере пока ничего не настроено.")),
    actions: [el("a", { class: "btn ghost", href: "#/run", onclick: () => dlg.close() }, "Все инструменты")],
  });
}

function fileField(p, preset, files) {
  const accept = p.accept || [];
  const fits = files.filter((f) => !accept.length || accept.includes(fileType(f.name)));
  const jobTitle = (path) => {
    const id = path.split("/")[1];
    return live.jobs.find((j) => j.id === id)?.title || "результат задачи";
  };
  const uploaded = fits.filter((f) => f.path.startsWith("inputs/"));
  const results = fits.filter((f) => f.path.startsWith("jobs/"));
  const select = el("select", { class: "input", required: p.required || null },
    el("option", { value: "" }, fits.length ? "— выберите файл —" : "— нет подходящих файлов —"),
    uploaded.length ? el("optgroup", { label: "Загруженные" }, uploaded.map((f) =>
      el("option", { value: f.path, selected: f.path === preset || null }, `${f.name} · ${fmt.bytes(f.size)}`))) : null,
    results.length ? el("optgroup", { label: "Результаты задач" }, results.slice(0, 60).map((f) =>
      el("option", { value: f.path, selected: f.path === preset || null }, `${f.name} · ${jobTitle(f.path)}`))) : null);
  if (preset && !fits.some((f) => f.path === preset)) select.append(el("option", { value: preset, selected: true }, basename(preset)));
  const hint = accept.length ? `Подходит: ${accept.map((a) => TYPE_LABEL[a] || a).join(", ")}` : "";
  return { select, hint };
}

function fieldFor(p, preset, files) {
  const id = `f-${p.name}-${Math.random().toString(36).slice(2, 7)}`;
  let control;
  let hint = "";
  if (p.type === "file") {
    ({ select: control, hint } = fileField(p, preset, files));
  } else if (p.type === "choice") {
    control = el("select", { class: "input" }, p.choices.map((c) => el("option", { value: c, selected: String(preset ?? p.default) === c || null }, c)));
  } else if (p.type === "number") {
    control = el("input", { class: "input", type: "number", inputmode: "decimal", value: preset ?? p.default ?? "",
      min: p.min, max: p.max, step: p.integer ? 1 : "any", required: p.required || null });
    if (p.min !== undefined && p.max !== undefined) hint = `от ${fmt.num(p.min, 2)} до ${fmt.num(p.max, 2)}`;
  } else if (p.type === "text") {
    control = el("textarea", { class: "input", required: p.required || null }, preset ?? p.default ?? "");
  } else {
    control = el("input", { class: "input", type: "text", value: preset ?? p.default ?? "", maxlength: p.max_length || 500,
      required: p.required || null, autocomplete: "off" });
  }
  control.id = id;
  const node = el("div", { class: "field" }, el("label", { for: id }, p.label || p.name), control, hint ? el("span", { class: "hint" }, hint) : null);
  return { name: p.name, node, value: () => control.value };
}

/** Form for one tool in a sheet; on success opens the new job. */
export async function runSheet(tool, preset = {}) {
  const files = tool.params.some((p) => p.type === "file") ? await api.get("/api/files?scope=all") : [];
  const fields = tool.params.map((p) => fieldFor(p, preset[p.name], files));
  const formId = `run-${tool.id}`;
  const error = el("p", { class: "error-text", role: "alert" });
  const form = el("form", { class: "stack gap-4", id: formId },
    fields.length ? fields.map((f) => f.node) : el("p", { class: "secondary" }, "Параметров нет — можно запускать."), error);
  const submit = el("button", { class: "btn", type: "submit", form: formId }, icon("play", { cls: "sm" }), "Запустить");
  const dlg = openSheet({
    title: tool.title, subtitle: tool.description, body: form,
    actions: [el("button", { class: "btn ghost", type: "button", onclick: () => dlg.close() }, "Отмена"), submit],
  });
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    if (!form.reportValidity()) return;
    const params = Object.fromEntries(fields.map((f) => [f.name, f.value()]));
    submit.setAttribute("aria-busy", "true");
    submit.disabled = true;
    try {
      const job = await api.post("/api/jobs", { tool: tool.id, params });
      dlg.close();
      toast("Задача запущена");
      refreshLive();
      location.hash = `#/jobs/${job.id}`;
    } catch (err) {
      error.textContent = err.message;
    } finally {
      submit.removeAttribute("aria-busy");
      submit.disabled = false;
    }
  });
}

// --- jobs ------------------------------------------------------------------------------------------
export const JOB_STATE = {
  queued: { text: "в очереди", level: "info", icon: "hourglass" },
  running: { text: "идёт", level: "info", icon: "activity" },
  done: { text: "готово", level: "ok", icon: "circle-check" },
  failed: { text: "ошибка", level: "crit", icon: "circle-x" },
  cancelled: { text: "отменено", level: "warn", icon: "x" },
};

export function stateBadge(state) {
  const s = JOB_STATE[state] || { text: state, level: "", icon: "info" };
  return el("span", { class: "badge", "data-level": s.level }, icon(s.icon, { cls: "sm" }), s.text);
}

export function progressText(p) {
  if (!p) return "идёт…";
  return `${fmt.num(p.percent, 0)} %${p.eta_s !== undefined ? ` · ещё ≈ ${fmt.duration(p.eta_s)}` : ""}`;
}

export function jobRow(job, { current = false } = {}) {
  const running = job.state === "running";
  const bar = el("span");
  if (running && job.progress) bar.style.width = `${job.progress.percent}%`;
  return el("a", { class: "list-item", href: `#/jobs/${job.id}`, "aria-current": current ? "true" : null },
    icon(toolIcon(job.tool)),
    el("span", { class: "list-item-main" },
      el("span", { class: "list-item-title" }, job.title),
      running
        ? el("span", { class: "list-item-sub" }, progressText(job.progress))
        : el("span", { class: "list-item-sub" }, job.error || fmt.when(job.finished || job.created)),
      running ? el("span", { class: job.progress ? "progress" : "progress indeterminate" }, bar) : null),
    stateBadge(job.state));
}
