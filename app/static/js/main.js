// Домашний пульт: вход, оболочка, навигация, роутер, живой статус в шапке.
import { $, el, icon, mount, fmt, createRouter, initTheme, setIconSprite, onDropFiles } from "../kit/ui.js";
import { api, live, startLive, stopLive, refreshLive, subscribe, isStale, uploadFiles, LEVEL } from "./core.js";
import * as overview from "./views/overview.js";
import * as server from "./views/server.js";
import * as run from "./views/run.js";
import * as jobs from "./views/jobs.js";
import * as library from "./views/library.js";
import * as settings from "./views/settings.js";

setIconSprite("/static/kit/icons.svg");
initTheme();

const NAV = [
  { path: "/", view: overview, icon: "house", label: "Обзор" },
  { path: "/server", view: server, icon: "server", label: "Сервер" },
  { path: "/run", view: run, icon: "plus", label: "Запуск", primary: true },
  { path: "/jobs", view: jobs, icon: "list-checks", label: "Задачи" },
  { path: "/library", view: library, icon: "library", label: "Библиотека" },
];

let cleanup = null;
let started = false;

function renderNav(current) {
  const running = (live.jobs || []).filter((j) => j.state === "running" || j.state === "queued").length;
  mount($("#nav"),
    el("div", { class: "app-brand" }, icon("gauge"), "Домашний пульт"),
    NAV.map((n) => el("a", {
      class: `nav-item${n.primary ? " primary" : ""}`, href: `#${n.path}`,
      "aria-current": current === n.path ? "page" : null,
    }, icon(n.icon), el("span", {}, n.label),
    n.path === "/jobs" && running ? el("span", { class: "badge nav-count", "data-level": "info", "aria-label": `идёт задач: ${running}` }, String(running)) : null)),
    el("div", { class: "nav-foot" }, el("a", { class: "nav-item", href: "#/settings", "aria-current": current === "/settings" ? "page" : null },
      icon("settings"), el("span", {}, "Настройки"))));
}

let currentPath = "/";
function show(path, view, params, query) {
  if (cleanup) { try { cleanup(); } catch (e) { console.error(e); } cleanup = null; }
  currentPath = path;
  renderNav(path);
  $("#page-title").textContent = view.title;
  document.title = `${view.title} · Домашний пульт`;
  const main = $("#main");
  window.scrollTo(0, 0);
  cleanup = view.render(main, params, query) || null;
  main.focus({ preventScroll: true });
}

const router = createRouter([
  ["/", (p, q) => show("/", overview, p, q)],
  ["/server", (p, q) => show("/server", server, p, q)],
  ["/run", (p, q) => show("/run", run, p, q)],
  ["/jobs", (p, q) => show("/jobs", jobs, p, q)],
  ["/jobs/:id", (p, q) => show("/jobs", jobs, p, q)],
  ["/library", (p, q) => show("/library", library, p, q)],
  ["/settings", (p, q) => show("/settings", settings, p, q)],
]);

// header: health pill + connection banner, live on every poll
function renderHealth(state) {
  const pill = $("#health-pill");
  const m = state.metrics;
  const stale = isStale();
  const lvl = stale ? "unknown" : (m?.status || "unknown");
  const problems = (m?.alerts || []).filter((a) => a.level !== "info").length;
  const text = stale ? "Нет связи" : lvl === "ok" ? "В порядке" : lvl === "warn" ? `Замечания: ${problems}` : lvl === "crit" ? `Проблемы: ${problems}` : "…";
  pill.dataset.level = lvl;
  pill.setAttribute("aria-label", `Состояние сервера: ${stale ? "нет связи" : LEVEL[lvl]?.title || text}`);
  mount(pill, el("span", { class: "dot", "data-level": lvl }), el("span", {}, text));
  const banner = $("#conn-banner");
  if (stale && started) {
    banner.hidden = false;
    mount(banner, icon("wifi"),
      el("span", { class: "grow" }, state.error && state.error.status !== 401 ? `${state.error.message}. ` : "Нет свежих данных. ",
        live.lastOk ? el("span", {}, "Последние — ", el("span", { "data-ago": live.lastOk / 1000 }, fmt.ago(live.lastOk / 1000)), ". ") : null,
        "Проверьте VPN и сервер."),
      el("button", { class: "btn ghost sm", type: "button", onclick: () => refreshLive() }, icon("refresh-cw", { cls: "sm" }), "Повторить"));
  } else {
    banner.hidden = true;
  }
  if (state.jobs) renderNavCount();
}

let lastRunning = -1;
function renderNavCount() {
  const running = (live.jobs || []).filter((j) => j.state === "running" || j.state === "queued").length;
  if (running !== lastRunning) { lastRunning = running; renderNav(currentPath); }
}

// relative times tick every second without refetching
setInterval(() => {
  for (const node of document.querySelectorAll("[data-ago]")) node.textContent = fmt.ago(Number(node.dataset.ago));
  if (started) renderHealth(live);
}, 1000);

function showLogin(message = "") {
  stopLive();
  started = false;
  if (cleanup) { cleanup(); cleanup = null; }
  $("#app").hidden = true;
  $("#login").hidden = false;
  $("#login-error").textContent = message;
  $("#token").focus();
}

async function enter() {
  try {
    await api.get("/api/ui");
  } catch (e) {
    showLogin(e.status === 401 ? (api.token ? "Токен не подошёл" : "") : `Сервер не отвечает: ${e.message}`);
    return;
  }
  $("#login").hidden = true;
  $("#app").hidden = false;
  started = true;
  startLive();
  router.run();
}

$("#login-form").addEventListener("submit", (e) => {
  e.preventDefault();
  api.setToken($("#token").value.trim());
  enter();
});
window.addEventListener("hub:unauthorized", () => showLogin(api.token ? "Токен не подошёл" : ""));
mount($("#settings-link"), icon("settings"));
subscribe(renderHealth);
onDropFiles((files) => { if (started) uploadFiles(files); });

if (api.token) enter(); else showLogin();
