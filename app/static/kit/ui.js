// ui-studio kit — DOM helpers, formatting, API, router, polling, theme, toasts, dialogs.
// Plain ES module, no build step, CSP-safe: no innerHTML with data, no inline styles in markup.

const SVG_NS = "http://www.w3.org/2000/svg";
let spriteUrl = "kit/icons.svg";

// --- DOM -------------------------------------------------------------------------------
export const $ = (sel, root = document) => root.querySelector(sel);
export const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));

/** el("button", {class: "btn", onclick: fn, "aria-label": "…"}, "Текст", child, [more]) */
export function el(tag, attrs = {}, ...children) {
  const node = document.createElement(tag);
  setAttrs(node, attrs);
  append(node, children);
  return node;
}

export function svgEl(tag, attrs = {}, ...children) {
  const node = document.createElementNS(SVG_NS, tag);
  for (const [k, v] of Object.entries(attrs)) if (v !== null && v !== undefined && v !== false) node.setAttribute(k, v);
  append(node, children);
  return node;
}

function setAttrs(node, attrs) {
  for (const [k, v] of Object.entries(attrs || {})) {
    if (v === null || v === undefined || v === false) continue;
    if (k === "class") node.className = v;
    else if (k === "style") setStyle(node, v); // CSSOM properties pass a strict CSP; style="" does not
    else if (k.startsWith("on") && typeof v === "function") node.addEventListener(k.slice(2), v);
    else if (k === "value" && "value" in node) node.value = v;
    else node.setAttribute(k, v === true ? "" : v);
  }
}

/** Set inline styles through CSSOM properties: {width: "40%"} or "width: 40%; color: red". */
export function setStyle(node, styles) {
  const pairs = typeof styles === "string"
    ? styles.split(";").map((d) => d.split(":")).filter((p) => p.length >= 2).map(([k, ...v]) => [k.trim(), v.join(":").trim()])
    : Object.entries(styles);
  for (const [k, v] of pairs) node.style.setProperty(k.replace(/[A-Z]/g, (c) => "-" + c.toLowerCase()), v);
}

function append(node, children) {
  for (const c of children.flat(Infinity)) {
    if (c === null || c === undefined || c === false) continue;
    node.append(c instanceof Node ? c : document.createTextNode(String(c)));
  }
}

/** Replace children, skipping null/false (replaceChildren would print them as text). */
export function mount(root, ...children) {
  root.replaceChildren();
  append(root, children);
  return root;
}

export function setIconSprite(url) { spriteUrl = url; }

/** <svg class="icon"><use href="sprite#name"></use></svg>; decorative unless a label is given. */
export function icon(name, { cls = "", label } = {}) {
  const svg = svgEl("svg", { class: `icon ${cls}`.trim(), viewBox: "0 0 24 24" });
  if (label) { svg.setAttribute("role", "img"); svg.setAttribute("aria-label", label); }
  else svg.setAttribute("aria-hidden", "true");
  svg.append(svgEl("use", { href: `${spriteUrl}#${name}` }));
  return svg;
}

// --- formatting (Russian locale) ---------------------------------------------------------
const NBSP = " ";
const nf = (digits) => new Intl.NumberFormat("ru-RU", { maximumFractionDigits: digits, minimumFractionDigits: 0 });
const BYTE_UNITS = ["Б", "КБ", "МБ", "ГБ", "ТБ"];
const timeFmt = new Intl.DateTimeFormat("ru-RU", { hour: "2-digit", minute: "2-digit" });
const clockFmt = new Intl.DateTimeFormat("ru-RU", { hour: "2-digit", minute: "2-digit", second: "2-digit" });
const dateFmt = new Intl.DateTimeFormat("ru-RU", { day: "numeric", month: "short" });

export const fmt = {
  num(v, digits = 1) { return v === null || v === undefined || Number.isNaN(v) ? "—" : nf(digits).format(v); },
  pct(v, digits = 0) { return v === null || v === undefined ? "—" : `${nf(digits).format(v)}${NBSP}%`; },
  bytes(n, digits = 1) {
    if (n === null || n === undefined) return "—";
    let i = 0;
    while (Math.abs(n) >= 1024 && i < BYTE_UNITS.length - 1) { n /= 1024; i++; }
    return `${nf(i ? digits : 0).format(n)}${NBSP}${BYTE_UNITS[i]}`;
  },
  rate(bps) { return bps === null || bps === undefined ? "—" : `${fmt.bytes(bps)}/с`; },
  temp(c) { return c === null || c === undefined ? "—" : `${nf(0).format(c)}${NBSP}°C`; },
  duration(s) {
    if (s === null || s === undefined) return "—";
    s = Math.max(0, Math.round(s));
    const d = Math.floor(s / 86400), h = Math.floor((s % 86400) / 3600), m = Math.floor((s % 3600) / 60);
    if (d) return `${d}${NBSP}д ${h}${NBSP}ч`;
    if (h) return `${h}${NBSP}ч ${m}${NBSP}мин`;
    if (m) return `${m}${NBSP}мин`;
    return `${s}${NBSP}с`;
  },
  ago(ts, now = Date.now() / 1000) {
    if (!ts) return "—";
    const d = Math.round(now - ts);
    if (d < 5) return "только что";
    if (d < 60) return `${d}${NBSP}с назад`;
    if (d < 3600) return `${Math.floor(d / 60)}${NBSP}мин назад`;
    if (d < 86400) return `${Math.floor(d / 3600)}${NBSP}ч назад`;
    return fmt.when(ts);
  },
  when(ts) {
    if (!ts) return "—";
    const date = new Date(ts * 1000);
    const today = new Date();
    const yesterday = new Date(Date.now() - 86400000);
    if (date.toDateString() === today.toDateString()) return `сегодня, ${timeFmt.format(date)}`;
    if (date.toDateString() === yesterday.toDateString()) return `вчера, ${timeFmt.format(date)}`;
    return `${dateFmt.format(date)}, ${timeFmt.format(date)}`;
  },
  time(ts) { return ts ? timeFmt.format(new Date(ts * 1000)) : "—"; },
  clock(ts) { return ts ? clockFmt.format(new Date(ts * 1000)) : "—"; },
};

/** "ok" | "warn" | "crit" for a value against thresholds (higher is worse unless invert). */
export function level(value, warn, crit, invert = false) {
  if (value === null || value === undefined) return "unknown";
  if (invert) return value <= crit ? "crit" : value <= warn ? "warn" : "ok";
  return value >= crit ? "crit" : value >= warn ? "warn" : "ok";
}

// --- storage ------------------------------------------------------------------------------
export const store = {
  get(key, fallback = null) {
    try { const raw = localStorage.getItem(key); return raw === null ? fallback : JSON.parse(raw); } catch (e) { return fallback; }
  },
  set(key, value) {
    try { value === null || value === undefined ? localStorage.removeItem(key) : localStorage.setItem(key, JSON.stringify(value)); } catch (e) { /* private mode */ }
  },
};

// --- API ------------------------------------------------------------------------------------
export class ApiError extends Error {
  constructor(message, status) { super(message); this.status = status; }
}

/** Bearer-token JSON client. onUnauthorized() is called on 401. */
export function createApi({ tokenKey = "token", onUnauthorized = () => {} } = {}) {
  let token = store.get(tokenKey, "");
  async function request(method, path, body, headers = {}) {
    const h = { Authorization: `Bearer ${token}`, ...headers };
    let payload = body;
    if (body !== undefined && !(body instanceof Blob) && typeof body !== "string") {
      payload = JSON.stringify(body);
      h["Content-Type"] = "application/json";
    }
    let res;
    try { res = await fetch(path, { method, headers: h, body: payload }); }
    catch (e) { throw new ApiError("Нет связи с сервером", 0); }
    if (res.status === 401) { onUnauthorized(); throw new ApiError("Нужен токен", 401); }
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new ApiError(data.error || res.statusText || `Ошибка ${res.status}`, res.status);
    return data;
  }
  return {
    get token() { return token; },
    setToken(t) { token = t || ""; store.set(tokenKey, token || null); },
    get: (p) => request("GET", p),
    post: (p, b = {}) => request("POST", p, b),
    put: (p, b) => request("PUT", p, b),
    del: (p) => request("DELETE", p),
    /** PUT a file with progress (fetch has no upload progress, so XHR). */
    upload(path, file, onProgress = () => {}) {
      return new Promise((resolve, reject) => {
        const xhr = new XMLHttpRequest();
        xhr.open("PUT", path);
        xhr.setRequestHeader("Authorization", `Bearer ${token}`);
        xhr.upload.onprogress = (e) => { if (e.lengthComputable) onProgress(e.loaded / e.total); };
        xhr.onload = () => {
          let data = {};
          try { data = JSON.parse(xhr.responseText || "{}"); } catch (e) { /* not JSON */ }
          if (xhr.status === 401) onUnauthorized();
          if (xhr.status >= 200 && xhr.status < 300) resolve(data);
          else reject(new ApiError(data.error || `Ошибка ${xhr.status}`, xhr.status));
        };
        xhr.onerror = () => reject(new ApiError("Связь оборвалась", 0));
        xhr.send(file);
      });
    },
  };
}

// --- router (hash based: deep links and the back button work) ---------------------------------
/** routes: [["/", fn], ["/jobs/:id", fn]]; fn(params, query, path). */
export function createRouter(routes, { onChange } = {}) {
  const compiled = routes.map(([pattern, handler]) => {
    const keys = [];
    const re = new RegExp("^" + pattern.replace(/:[^/]+/g, (m) => { keys.push(m.slice(1)); return "([^/]+)"; }) + "/?$");
    return { pattern, handler, re, keys };
  });
  function parse() {
    const raw = location.hash.replace(/^#/, "") || "/";
    const [path, qs = ""] = raw.split("?");
    return { path, query: Object.fromEntries(new URLSearchParams(qs)) };
  }
  function run() {
    const { path, query } = parse();
    for (const r of compiled) {
      const m = path.match(r.re);
      if (m) {
        const params = Object.fromEntries(r.keys.map((k, i) => [k, decodeURIComponent(m[i + 1])]));
        if (onChange) onChange(r.pattern, params, query);
        return r.handler(params, query, path);
      }
    }
    if (onChange) onChange(compiled[0].pattern, {}, {});
    return compiled[0].handler({}, {}, "/");
  }
  window.addEventListener("hashchange", run);
  return {
    run,
    go(path) { if (location.hash === "#" + path) run(); else location.hash = path; },
    /** Update the query string without re-running the route. */
    replaceQuery(query) {
      const { path } = parse();
      const qs = new URLSearchParams(Object.entries(query).filter(([, v]) => v !== "" && v !== null && v !== undefined)).toString();
      history.replaceState(null, "", `#${path}${qs ? "?" + qs : ""}`);
    },
  };
}

// --- polling that sleeps while the tab is hidden --------------------------------------------------
export function poll(fn, ms) {
  let timer = null;
  let stopped = false;
  let running = false;
  async function tick() {
    if (stopped || running) return;
    if (document.hidden) { timer = setTimeout(tick, ms); return; }
    running = true;
    try { await fn(); } catch (e) { /* the caller shows its own error state */ }
    running = false;
    if (!stopped) timer = setTimeout(tick, ms);
  }
  const onVisible = () => { if (!document.hidden && !stopped) { clearTimeout(timer); tick(); } };
  document.addEventListener("visibilitychange", onVisible);
  tick();
  return {
    stop() { stopped = true; clearTimeout(timer); document.removeEventListener("visibilitychange", onVisible); },
    now() { clearTimeout(timer); tick(); },
  };
}

// --- theme: auto / light / dark, remembered per browser ----------------------------------------------
const THEME_KEY = "ui-theme";
export function initTheme() {
  applyTheme(store.get(THEME_KEY, "auto"));
  matchMedia("(prefers-color-scheme: dark)").addEventListener("change", () => window.dispatchEvent(new Event("themechange")));
}
export function getTheme() { return store.get(THEME_KEY, "auto"); }
export function setTheme(mode) { store.set(THEME_KEY, mode); applyTheme(mode); }
function applyTheme(mode) {
  if (mode === "light" || mode === "dark") document.documentElement.setAttribute("data-theme", mode);
  else document.documentElement.removeAttribute("data-theme");
  window.dispatchEvent(new Event("themechange"));
}

/** Read a design token (CSS custom property) as a string. */
export function token(name) { return getComputedStyle(document.documentElement).getPropertyValue(name).trim(); }

// --- toasts and dialogs ---------------------------------------------------------------------------------
export function toast(text, { level: lvl = "info", timeout = 2800 } = {}) {
  let box = $(".toasts");
  if (!box) { box = el("div", { class: "toasts", role: "status", "aria-live": "polite" }); document.body.append(box); }
  const t = el("div", { class: "toast", "data-level": lvl }, text);
  box.append(t);
  setTimeout(() => t.remove(), timeout);
}

/** Promise<boolean>; destructive actions get danger:true. */
export function confirmDialog(text, { title = "Подтвердите", okText = "Да", cancelText = "Отмена", danger = false } = {}) {
  return new Promise((resolve) => {
    const ok = el("button", { class: danger ? "btn danger" : "btn", value: "ok" }, okText);
    const dlg = el("dialog", { class: "sheet", "aria-labelledby": "confirm-title" },
      el("form", { method: "dialog" },
        el("div", { class: "sheet-head" }, el("h3", { id: "confirm-title" }, title)),
        el("div", { class: "sheet-body" }, el("p", {}, text)),
        el("div", { class: "sheet-actions" }, el("button", { class: "btn ghost", value: "cancel" }, cancelText), ok)));
    dlg.addEventListener("close", () => { resolve(dlg.returnValue === "ok"); dlg.remove(); });
    document.body.append(dlg);
    dlg.showModal();
    ok.focus();
  });
}

export async function copyText(text) {
  try { await navigator.clipboard.writeText(text); }
  catch (e) { // plain HTTP inside a VPN is not a secure context
    const ta = el("textarea", { class: "visually-hidden" }, text);
    document.body.append(ta);
    ta.select();
    try { document.execCommand("copy"); } catch (e2) { /* nothing else to try */ }
    ta.remove();
  }
  toast("Скопировано");
}

/** Code block with a copy button. */
export function codeBlock(text) {
  return el("div", { class: "code" }, el("pre", {}, text),
    el("button", { class: "btn ghost sm", type: "button", onclick: () => copyText(text) }, icon("copy", { cls: "sm" }), "Копировать"));
}

/** Window-wide drag & drop of files with an overlay. */
export function onDropFiles(handler, { text = "Отпустите, чтобы загрузить" } = {}) {
  const overlay = el("div", { class: "drop-overlay", "aria-hidden": "true" },
    el("div", { class: "drop-box" }, icon("upload", { cls: "xl" }), text));
  document.body.append(overlay);
  let depth = 0;
  const hasFiles = (e) => Array.from(e.dataTransfer?.types || []).includes("Files");
  window.addEventListener("dragenter", (e) => { if (!hasFiles(e)) return; depth++; overlay.classList.add("on"); });
  window.addEventListener("dragover", (e) => { if (hasFiles(e)) e.preventDefault(); });
  window.addEventListener("dragleave", (e) => { if (!hasFiles(e)) return; depth = Math.max(0, depth - 1); if (!depth) overlay.classList.remove("on"); });
  window.addEventListener("drop", (e) => {
    if (!hasFiles(e)) return;
    e.preventDefault(); depth = 0; overlay.classList.remove("on");
    if (e.dataTransfer.files.length) handler(Array.from(e.dataTransfer.files));
  });
}
