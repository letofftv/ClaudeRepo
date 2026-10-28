"use strict";
// Домашний пульт: интерфейс к API сервера. Без библиотек и сборки.

const GROUPS = { audio: "Аудио", video: "Видео", generation: "Генерация", system: "Система", other: "Прочее" };
const STATES = { queued: "в очереди", running: "идёт", done: "готово", failed: "ошибка", cancelled: "отменено" };
const STATE_CLASS = { done: "ok", failed: "bad", cancelled: "warn", running: "warn", queued: "" };
const RU_ACCESS = { yes: "из России работает", vpn: "нужен VPN", no: "из России недоступно", unknown: "доступ не проверен" };
const REPO_URL = "https://github.com/letofftv/ClaudeRepo/blob/main/";
const UPDATE_RESULT = {
  updated: "обновлён", "up-to-date": "свежая версия", "tests-failed": "новая версия не прошла тесты",
  error: "ошибка обновления", "local-changes": "в клоне правки — обновление стоит",
};

const state = { token: "", tab: "server", tools: [], catalog: null, resources: null, sets: null, jobId: null, timer: null };

// --- helpers ---------------------------------------------------------------
const $ = (sel, root = document) => root.querySelector(sel);
function el(tag, attrs = {}, ...children) {
  const node = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (v === null || v === undefined || v === false) continue;
    if (k === "class") node.className = v;
    else if (k === "style") node.style.cssText = v; // CSSOM is allowed by the page CSP, the attribute is not
    else if (k.startsWith("on")) node.addEventListener(k.slice(2), v);
    else node.setAttribute(k, v === true ? "" : v);
  }
  for (const c of children.flat()) {
    if (c === null || c === undefined || c === false) continue;
    node.append(c instanceof Node ? c : document.createTextNode(String(c)));
  }
  return node;
}
function storeGet(key) { try { return localStorage.getItem(key) || ""; } catch (e) { return ""; } }
function storeSet(key, value) { try { value ? localStorage.setItem(key, value) : localStorage.removeItem(key); } catch (e) { /* private mode */ } }
function fmtBytes(n) {
  if (n === null || n === undefined) return "—";
  const units = ["Б", "КБ", "МБ", "ГБ", "ТБ"];
  let i = 0;
  while (n >= 1024 && i < units.length - 1) { n /= 1024; i++; }
  return (i ? n.toFixed(1) : n) + " " + units[i];
}
function fmtTime(ts) { return ts ? new Date(ts * 1000).toLocaleString("ru-RU", { dateStyle: "short", timeStyle: "short" }) : "—"; }
function fmtDuration(s) {
  if (!s && s !== 0) return "—";
  const d = Math.floor(s / 86400), h = Math.floor(s % 86400 / 3600), m = Math.floor(s % 3600 / 60);
  return (d ? d + " д " : "") + (h ? h + " ч " : "") + m + " мин";
}
function toast(text) {
  const t = $("#toast");
  t.textContent = text;
  t.classList.remove("hidden");
  clearTimeout(toast.timer);
  toast.timer = setTimeout(() => t.classList.add("hidden"), 2600);
}
async function copyText(text) {
  try {
    await navigator.clipboard.writeText(text);
  } catch (e) { // http over VPN is not a secure context: fall back to a hidden textarea
    const ta = el("textarea", { style: "position:fixed;opacity:0" }, text);
    document.body.append(ta);
    ta.select();
    try { document.execCommand("copy"); } catch (e2) { /* ignore */ }
    ta.remove();
  }
  toast("Скопировано");
}
function codeBlock(text) {
  return el("div", { class: "code" },
    el("pre", {}, text),
    el("button", { class: "small ghost", type: "button", onclick: () => copyText(text) }, "Копировать"));
}

async function api(path, opts = {}) {
  const headers = Object.assign({ Authorization: "Bearer " + state.token }, opts.headers || {});
  let body = opts.body;
  if (body && !(body instanceof Blob) && typeof body !== "string") {
    body = JSON.stringify(body);
    headers["Content-Type"] = "application/json";
  }
  const res = await fetch(path, { method: opts.method || "GET", headers, body });
  if (res.status === 401) { showLogin("Токен не подошёл"); throw new Error("401"); }
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.error || res.statusText);
  return data;
}
async function fileLink(path, inline) {
  const data = await api("/api/link?path=" + encodeURIComponent(path));
  return inline ? data.inline_url : data.url;
}
async function download(path) {
  const a = el("a", { href: await fileLink(path, false), download: "" });
  document.body.append(a);
  a.click();
  a.remove();
}

// --- login & tabs ----------------------------------------------------------
function showLogin(message) {
  $("#main").classList.add("hidden");
  $("#login").classList.remove("hidden");
  $("#login-error").textContent = message || "";
  stopTimer();
}
async function enter() {
  try {
    await api("/api/status");
  } catch (e) {
    if (e.message !== "401") showLogin("Сервер не отвечает: " + e.message);
    return;
  }
  $("#login").classList.add("hidden");
  $("#main").classList.remove("hidden");
  switchTab(state.tab);
}
$("#login-form").addEventListener("submit", (ev) => {
  ev.preventDefault();
  state.token = $("#token").value.trim();
  storeSet("hub-token", state.token);
  enter();
});
$("#logout").addEventListener("click", () => {
  state.token = "";
  storeSet("hub-token", "");
  showLogin("");
});
$("#tabs").addEventListener("click", (ev) => {
  const tab = ev.target.closest("button")?.dataset.tab;
  if (tab) switchTab(tab);
});
function stopTimer() { clearInterval(state.timer); state.timer = null; }
function switchTab(tab) {
  state.tab = tab;
  storeSet("hub-tab", tab);
  for (const b of document.querySelectorAll("#tabs button")) b.classList.toggle("active", b.dataset.tab === tab);
  for (const p of document.querySelectorAll("[data-panel]")) p.classList.toggle("hidden", p.dataset.panel !== tab);
  stopTimer();
  const loaders = { server: loadServer, tools: loadTools, jobs: loadJobs, files: loadFiles, catalog: loadCatalog, resources: loadResources, sets: loadSets };
  loaders[tab]().catch((e) => e.message !== "401" && toast(e.message));
  if (tab === "server") state.timer = setInterval(() => loadServer().catch(() => {}), 10000);
  if (tab === "jobs") state.timer = setInterval(() => loadJobs(true).catch(() => {}), 2500);
}

// --- server ----------------------------------------------------------------
function statCard(label, value, sub, ratio) {
  return el("div", { class: "card" },
    el("div", { class: "label" }, label),
    el("div", { class: "value" }, value),
    sub ? el("div", { class: "muted" }, sub) : null,
    ratio !== undefined ? el("div", { class: "bar" }, el("span", { style: `width:${Math.min(100, Math.round(ratio * 100))}%` })) : null);
}
function jobRow(job) {
  return el("tr", {},
    el("td", {}, el("a", { href: "#", onclick: (e) => { e.preventDefault(); state.jobId = job.id; switchTab("jobs"); } }, job.title)),
    el("td", {}, el("span", { class: "tag " + (STATE_CLASS[job.state] || "") }, STATES[job.state] || job.state)),
    el("td", { class: "num" }, fmtTime(job.created)));
}
async function loadServer() {
  const s = await api("/api/status");
  const mem = s.memory || {};
  const cards = [
    statCard("Сервер", s.host || "—", s.system),
    statCard("Нагрузка", s.load ? s.load.map((x) => x.toFixed(2)).join(" · ") : "—", `${s.cpu_count} потоков`,
      s.load ? s.load[0] / (s.cpu_count || 1) : undefined),
    statCard("Память", mem.total ? fmtBytes(mem.total - mem.available) : "—", mem.total ? "из " + fmtBytes(mem.total) : "",
      mem.total ? 1 - mem.available / mem.total : undefined),
    statCard("Диск рабочей папки", fmtBytes(s.disk.free) + " свободно", "из " + fmtBytes(s.disk.total), 1 - s.disk.free / s.disk.total),
  ];
  for (const g of s.gpus || []) {
    cards.push(statCard("Видеокарта", g.name, `${g.mem_used_mb} / ${g.mem_total_mb} МБ · ${g.util_percent}% · ${g.temp_c}°C · драйвер ${g.driver}`,
      Number(g.mem_used_mb) / Number(g.mem_total_mb)));
  }
  if (!(s.gpus || []).length) cards.push(statCard("Видеокарта", "не видна", "nvidia-smi не найден"));
  cards.push(statCard("Инструменты", `${s.tools_available} из ${s.tools_total}`, s.ffmpeg ? "ffmpeg есть" : "ffmpeg не найден!"));
  cards.push(statCard("Работает", fmtDuration(s.uptime_s), "с последнего запуска системы"));
  const repo = s.repo || {};
  const upd = s.update;
  const updText = upd ? `${UPDATE_RESULT[upd.result] || upd.result} · проверено ${fmtTime(upd.time)}` : "обновлятор не настроен";
  cards.push(statCard("Версия пульта", s.version + (repo.commit ? " · " + repo.commit : ""),
    (repo.date ? "от " + new Date(repo.date).toLocaleDateString("ru-RU") + " · " : "") + updText));
  if (upd && !["updated", "up-to-date"].includes(upd.result)) {
    cards.push(statCard("Обновление остановлено", UPDATE_RESULT[upd.result] || upd.result, upd.message));
  }
  $("#server-cards").replaceChildren(...cards);
  $("#server-jobs").replaceChildren(s.jobs.length
    ? el("table", {}, el("tbody", {}, s.jobs.map(jobRow)))
    : el("p", { class: "muted" }, "Задач ещё не было."));
}

// --- tools -----------------------------------------------------------------
async function loadTools() {
  state.tools = await api("/api/tools");
  renderTools();
}
function renderTools() {
  const group = $("#tool-group").value;
  const onlyAvail = $("#tool-available").checked;
  const list = state.tools.filter((t) => (!group || t.group === group) && (!onlyAvail || t.available));
  $("#tool-list").replaceChildren(...list.map((t) => el("div", { class: "card tool" },
    el("h4", {}, t.title),
    el("p", {}, t.description),
    el("div", { class: "foot" },
      el("span", { class: "tag " + (t.available ? "ok" : "bad"), title: t.reason }, t.available ? GROUPS[t.group] || t.group : t.reason),
      el("button", { class: "small", disabled: !t.available, onclick: () => openRun(t) }, "Запустить")))));
}
$("#tool-group").addEventListener("change", renderTools);
$("#tool-available").addEventListener("change", renderTools);

async function openRun(tool) {
  const files = tool.params.some((p) => p.type === "file") ? await api("/api/files?scope=all") : [];
  $("#run-title").textContent = tool.title;
  $("#run-desc").textContent = tool.description;
  $("#run-error").textContent = "";
  const fields = tool.params.map((p) => {
    const id = "param-" + p.name;
    let input;
    if (p.type === "choice") {
      input = el("select", { id, name: p.name }, p.choices.map((c) => el("option", { value: c, selected: String(p.default) === c }, c)));
    } else if (p.type === "text") {
      input = el("textarea", { id, name: p.name, required: p.required }, p.default || "");
    } else if (p.type === "file") {
      input = el("select", { id, name: p.name, required: p.required },
        el("option", { value: "" }, files.length ? "— выберите файл —" : "— сначала загрузите файл во вкладке «Файлы» —"),
        files.map((f) => el("option", { value: f.path }, `${f.path} (${fmtBytes(f.size)})`)));
    } else if (p.type === "number") {
      input = el("input", { id, name: p.name, type: "number", value: p.default, min: p.min, max: p.max, step: p.integer ? 1 : "any", required: p.required });
    } else {
      input = el("input", { id, name: p.name, type: "text", value: p.default || "", required: p.required, maxlength: p.max_length || 500 });
    }
    return el("div", { class: "field" }, el("label", { for: id }, p.label || p.name), input);
  });
  $("#run-fields").replaceChildren(...(fields.length ? fields : [el("p", { class: "muted" }, "Параметров нет.")]));
  const dialog = $("#run-dialog");
  dialog.dataset.tool = tool.id;
  dialog.showModal();
}
$("#run-form").addEventListener("submit", async (ev) => {
  if (ev.submitter && ev.submitter.value === "cancel") return;
  ev.preventDefault();
  const dialog = $("#run-dialog");
  const params = {};
  for (const input of $("#run-fields").querySelectorAll("[name]")) params[input.name] = input.value;
  $("#run-submit").disabled = true;
  try {
    const job = await api("/api/jobs", { method: "POST", body: { tool: dialog.dataset.tool, params } });
    dialog.close();
    state.jobId = job.id;
    toast("Задача запущена");
    switchTab("jobs");
  } catch (e) {
    $("#run-error").textContent = e.message;
  } finally {
    $("#run-submit").disabled = false;
  }
});

// --- jobs ------------------------------------------------------------------
async function loadJobs(quiet) {
  const jobs = await api("/api/jobs");
  $("#job-list").replaceChildren(...(jobs.length ? jobs.map((j) => el("button", {
    class: "item" + (j.id === state.jobId ? " active" : ""),
    onclick: () => { state.jobId = j.id; loadJobs(); },
  }, el("div", {}, j.title), el("div", { class: "sub" },
    el("span", { class: "tag " + (STATE_CLASS[j.state] || "") }, STATES[j.state] || j.state), " ", fmtTime(j.created)))) : [el("p", { class: "muted" }, "Задач ещё нет.")]));
  if (!state.jobId) return;
  const current = jobs.find((j) => j.id === state.jobId);
  if (quiet && current && !["queued", "running"].includes(current.state) && $("#job-detail").dataset.final === state.jobId) return;
  await renderJob(state.jobId);
}
async function renderJob(id) {
  const job = await api("/api/jobs/" + encodeURIComponent(id));
  const detail = $("#job-detail");
  const running = ["queued", "running"].includes(job.state);
  detail.dataset.final = running ? "" : id;
  const params = Object.entries(job.params || {}).map(([k, v]) => el("tr", {}, el("th", {}, k), el("td", { class: "mono" }, String(v).slice(0, 300))));
  const files = job.files.map((f) => el("tr", {},
    el("td", {}, f.name),
    el("td", { class: "num" }, fmtBytes(f.size)),
    el("td", {}, el("button", { class: "small ghost", onclick: () => preview(f.path, detail) }, "Показать"), " ",
      el("button", { class: "small", onclick: () => download(f.path).catch((e) => toast(e.message)) }, "Скачать"))));
  // replaceChildren would print a null argument as text, so skipped parts are filtered out
  detail.replaceChildren(...[
    el("div", { class: "row" }, el("h3", { style: "margin:0;flex:1" }, job.title),
      el("span", { class: "tag " + (STATE_CLASS[job.state] || "") }, STATES[job.state] || job.state),
      running ? el("button", { class: "small ghost", onclick: async () => { await api(`/api/jobs/${id}/cancel`, { method: "POST" }); loadJobs(); } }, "Отменить") : null),
    el("p", { class: "muted" }, `Создана ${fmtTime(job.created)} · завершена ${fmtTime(job.finished)}` + (job.returncode !== null ? ` · код ${job.returncode}` : "")),
    job.error ? el("p", { class: "error" }, job.error) : null,
    params.length ? el("table", {}, el("tbody", {}, params)) : null,
    el("h4", {}, "Результаты"),
    files.length ? el("table", {}, el("tbody", {}, files)) : el("p", { class: "muted" }, running ? "Пока нет — задача идёт." : "Файлов нет (результат может быть в логе)."),
    el("div", { class: "preview", id: "preview" }),
    el("h4", {}, "Лог"),
    el("pre", { class: "log" }, job.log || "—")].filter(Boolean));
  const log = detail.querySelector("pre.log");
  log.scrollTop = log.scrollHeight;
}
async function preview(path, root) {
  const box = $("#preview", root);
  const url = await fileLink(path, true);
  const ext = path.split(".").pop().toLowerCase();
  let node;
  if (["png", "jpg", "jpeg", "gif", "webp"].includes(ext)) node = el("img", { src: url, alt: path });
  else if (["mp4", "webm", "mov", "m4v"].includes(ext)) node = el("video", { src: url, controls: true, playsinline: true });
  else if (["wav", "mp3", "flac", "ogg", "m4a", "aac", "opus"].includes(ext)) node = el("audio", { src: url, controls: true });
  else if (["txt", "srt", "vtt", "log", "json", "csv", "md", "ass"].includes(ext)) {
    const res = await fetch(url);
    node = el("pre", {}, (await res.text()).slice(0, 20000));
  } else node = el("p", { class: "muted" }, "Предпросмотр для этого типа нет — скачайте файл.");
  box.replaceChildren(node);
}

// --- files -----------------------------------------------------------------
async function loadFiles() {
  const files = await api("/api/files");
  $("#file-list").replaceChildren(files.length ? el("table", {},
    el("thead", {}, el("tr", {}, el("th", {}, "Файл"), el("th", {}, "Размер"), el("th", {}, "Загружен"), el("th", {}, ""))),
    el("tbody", {}, files.map((f) => el("tr", {},
      el("td", {}, f.name),
      el("td", { class: "num" }, fmtBytes(f.size)),
      el("td", { class: "num" }, fmtTime(f.mtime)),
      el("td", {},
        el("button", { class: "small ghost", onclick: () => download(f.path).catch((e) => toast(e.message)) }, "Скачать"), " ",
        el("button", { class: "small ghost", onclick: async () => {
          if (!confirm("Удалить " + f.name + "?")) return;
          await api("/api/files/" + encodeURIComponent(f.name), { method: "DELETE" });
          loadFiles();
        } }, "Удалить"))))))
    : el("p", { class: "muted" }, "Рабочая папка пуста. Загрузите аудио, видео или субтитры — их можно будет выбрать в инструментах."));
}
function uploadOne(file) {
  return new Promise((resolve, reject) => {
    const row = el("div", { class: "muted" }, file.name + ": 0%");
    $("#upload-progress").append(row);
    const xhr = new XMLHttpRequest();
    xhr.open("PUT", "/api/files/" + encodeURIComponent(file.name));
    xhr.setRequestHeader("Authorization", "Bearer " + state.token);
    xhr.upload.onprogress = (e) => { if (e.lengthComputable) row.textContent = `${file.name}: ${Math.round(e.loaded / e.total * 100)}%`; };
    xhr.onload = () => {
      if (xhr.status === 201) { row.remove(); resolve(); } else { row.textContent = `${file.name}: ошибка ${xhr.status}`; reject(new Error(xhr.statusText)); }
    };
    xhr.onerror = () => { row.textContent = `${file.name}: обрыв связи`; reject(new Error("network")); };
    xhr.send(file);
  });
}
async function uploadAll(fileList) {
  for (const f of fileList) await uploadOne(f).catch(() => {});
  loadFiles();
}
$("#file-input").addEventListener("change", (e) => uploadAll(e.target.files));
const drop = $("#drop");
drop.addEventListener("dragover", (e) => { e.preventDefault(); drop.classList.add("over"); });
drop.addEventListener("dragleave", () => drop.classList.remove("over"));
drop.addEventListener("drop", (e) => { e.preventDefault(); drop.classList.remove("over"); uploadAll(e.dataTransfer.files); });

// --- catalog ---------------------------------------------------------------
async function loadCatalog() {
  if (!state.catalog) {
    state.catalog = await api("/api/catalog");
    const dirSel = $("#cat-direction");
    for (const [k, v] of Object.entries(state.catalog.directions)) dirSel.append(el("option", { value: k }, v));
    const stSel = $("#cat-status");
    for (const s of state.catalog.statuses) stSel.append(el("option", { value: s }, s));
    stSel.value = "взять";
  }
  renderCatalog();
}
function renderCatalog() {
  const c = state.catalog;
  const q = $("#cat-search").value.trim().toLowerCase();
  const dir = $("#cat-direction").value;
  const st = $("#cat-status").value;
  const items = c.items.filter((i) => (!dir || i.direction === dir) && (!st || i.status === st) &&
    (!q || (i.name + " " + i.summary + " " + i.install).toLowerCase().includes(q)));
  $("#cat-packs").replaceChildren(...c.packs.map((p) => el("div", { class: "entry" },
    el("div", { class: "head" }, el("strong", {}, "Свой пакет: " + p.name), el("span", { class: "tag ok" }, "готов к установке")),
    el("p", {}, p.description), codeBlock(p.install))));
  $("#cat-count").textContent = `Показано ${items.length} из ${c.items.length}`;
  $("#cat-list").replaceChildren(...items.slice(0, 300).map((i) => el("div", { class: "entry" },
    el("div", { class: "head" },
      el("strong", {}, i.name),
      el("span", { class: "tag" }, i.direction_title),
      i.status ? el("span", { class: "tag " + ({ "взять": "ok", "отклонено": "bad", "не нужно": "bad" }[i.status] || "warn") }, i.status) : null),
    i.summary ? el("p", {}, i.summary) : null,
    el("p", {},
      i.url ? el("a", { href: i.url, target: "_blank", rel: "noopener noreferrer" }, "Источник") : null,
      i.url && i.card ? " · " : null,
      i.card ? el("a", { href: REPO_URL + i.card, target: "_blank", rel: "noopener noreferrer" }, "Карточка с оценкой") : null),
    i.install ? codeBlock(i.install) : null)));
}
for (const id of ["#cat-search", "#cat-direction", "#cat-status"]) $(id).addEventListener("input", () => state.catalog && renderCatalog());

// --- resources -------------------------------------------------------------
async function loadResources() {
  if (!state.resources) {
    state.resources = await api("/api/resources");
    const sel = $("#res-category");
    for (const [k, v] of Object.entries(state.resources.categories || {})) sel.append(el("option", { value: k }, v));
    $("#res-note").textContent = state.resources.note || "";
  }
  renderResources();
}
function renderResources() {
  const r = state.resources;
  const q = $("#res-search").value.trim().toLowerCase();
  const cat = $("#res-category").value;
  const ru = $("#res-ru").checked;
  const local = $("#res-local").checked;
  const items = (r.items || []).filter((i) => (!cat || i.category === cat || (i.also || []).includes(cat)) &&
    (!ru || i.ru_access === "yes") && (!local || i.kind === "local") &&
    (!q || JSON.stringify(i).toLowerCase().includes(q)))
    .sort((a, b) => (a.skip ? 1 : 0) - (b.skip ? 1 : 0));
  const cats = r.categories || {};
  const picks = (r.picks || []).filter((p) => !cat || p.category === cat);
  $("#res-picks").replaceChildren(...(picks.length && !q ? [el("div", { class: "entry" },
    el("div", { class: "head" }, el("strong", {}, "Лучшее по категориям")),
    picks.map((p) => el("p", {}, el("b", {}, (cats[p.category] || p.category) + ". "), p.text)))] : []));
  $("#res-list").replaceChildren(...(items.length ? items.map((i) => el("div", { class: "entry" },
    el("div", { class: "head" },
      el("strong", {}, i.url ? el("a", { href: i.url, target: "_blank", rel: "noopener noreferrer" }, i.name) : i.name),
      el("span", { class: "tag" }, cats[i.category] || i.category),
      i.kind === "local" ? el("span", { class: "tag ok" }, "локально") : null,
      i.ru_access ? el("span", { class: "tag " + ({ yes: "ok", vpn: "warn", no: "bad" }[i.ru_access] || "") }, RU_ACCESS[i.ru_access] || i.ru_access) : null,
      i.commercial === false ? el("span", { class: "tag warn" }, "только некоммерчески") : null,
      i.skip ? el("span", { class: "tag bad" }, "не подходит") : null),
    i.free ? el("p", {}, "Бесплатно: " + i.free) : null,
    i.license ? el("p", {}, "Лицензия: " + i.license) : null,
    i.attribution ? el("p", {}, "Указание автора: " + i.attribution) : null,
    i.platform ? el("p", {}, "Где работает: " + i.platform) : null,
    i.notes ? el("p", {}, i.notes) : null,
    i.run ? codeBlock(i.run) : null)) : [el("p", { class: "muted" }, "Ничего не найдено.")]));
}
for (const id of ["#res-search", "#res-category", "#res-ru", "#res-local"]) $(id).addEventListener("input", () => state.resources && renderResources());

// --- starter sets ----------------------------------------------------------
async function loadSets() {
  if (!state.sets) state.sets = await api("/api/starter-sets");
  $("#set-list").replaceChildren(...(state.sets.sets || []).map((s) => el("div", { class: "entry" },
    el("div", { class: "head" }, el("strong", {}, s.title), s.where ? el("span", { class: "tag" }, s.where) : null),
    s.description ? el("p", {}, s.description) : null,
    (s.steps || []).map((step) => el("div", {},
      el("p", {}, step.title + (step.note ? " — " + step.note : "")),
      step.commands ? codeBlock(step.commands) : null)))));
}

// --- start -----------------------------------------------------------------
state.token = storeGet("hub-token");
state.tab = storeGet("hub-tab") || "server";
if (state.token) enter(); else showLogin("");
