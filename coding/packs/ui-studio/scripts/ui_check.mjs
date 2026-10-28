#!/usr/bin/env node
// ui_check.mjs — headless UI audit: screenshots + hard checks for every page × viewport × theme.
//
//   node ui_check.mjs --url http://127.0.0.1:8787/ --routes "#/,#/server" --storage-json hub-token=SECRET
//   node ui_check.mjs --serve ../kit --routes gallery.html
//
// Checks (FAIL = must fix, WARN = look at it):
//   FAIL  horizontal scroll on the page, JS errors, CSP violations, failed same-origin requests,
//         text contrast below WCAG 2 (4.5:1, large text 3:1), buttons/links/inputs without a name,
//         images without alt, tap targets under 24×24 px (WCAG 2.5.8)
//   WARN  tap targets under 44×44 px on phones, text under 12 px, no h1, missing <html lang>
// Writes PNG screenshots, report.json, report.md and index.html (screenshot grid) to --out.
// Exit code 1 when anything FAILs (or WARNs with --fail-on warn), 2 when Playwright is missing.
//
// Options: --viewports phone,tablet,desktop  --themes light,dark  --wait "<css selector>"
//          --settle 700 (ms after load)  --out ui-report  --fail-on fail|warn
//          --storage key=value (raw localStorage)  --storage-json key=value (JSON-encoded)
//          --browser /path/to/chrome  --channel chrome  --axe [path/to/axe.min.js]  --full (full-page shots)
import { createRequire } from "node:module";
import { execSync } from "node:child_process";
import fs from "node:fs";
import http from "node:http";
import path from "node:path";

const require = createRequire(import.meta.url);
const VIEWPORTS = {
  phone: { width: 390, height: 844, isMobile: true, hasTouch: true },
  tablet: { width: 820, height: 1180, isMobile: true, hasTouch: true },
  desktop: { width: 1366, height: 900, isMobile: false, hasTouch: false },
};
const MIME = { ".html": "text/html; charset=utf-8", ".js": "text/javascript; charset=utf-8", ".mjs": "text/javascript; charset=utf-8",
  ".css": "text/css; charset=utf-8", ".svg": "image/svg+xml", ".json": "application/json", ".png": "image/png",
  ".jpg": "image/jpeg", ".woff2": "font/woff2" };

function parseArgs(argv) {
  const opts = { routes: [""], viewports: ["phone", "desktop"], themes: ["light", "dark"], out: "ui-report",
    settle: 700, failOn: "fail", storage: [], full: false };
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    const next = () => argv[++i];
    if (a === "--url") opts.url = next();
    else if (a === "--serve") opts.serve = next();
    else if (a === "--routes") opts.routes = next().split(",").map((s) => s.trim());
    else if (a === "--viewports") opts.viewports = next().split(",");
    else if (a === "--themes") opts.themes = next().split(",");
    else if (a === "--out") opts.out = next();
    else if (a === "--wait") opts.wait = next();
    else if (a === "--settle") opts.settle = Number(next());
    else if (a === "--fail-on") opts.failOn = next();
    else if (a === "--storage") opts.storage.push([next(), false]);
    else if (a === "--storage-json") opts.storage.push([next(), true]);
    else if (a === "--browser") opts.browser = next();
    else if (a === "--channel") opts.channel = next();
    else if (a === "--axe") opts.axe = argv[i + 1] && !argv[i + 1].startsWith("--") ? next() : "auto";
    else if (a === "--full") opts.full = true;
    else if (a === "--help" || a === "-h") { console.log(fs.readFileSync(new URL(import.meta.url), "utf8").split("\n").slice(1, 21).join("\n")); process.exit(0); }
  }
  if (!opts.url && !opts.serve) { console.error("Нужен --url или --serve (см. --help)"); process.exit(2); }
  return opts;
}

function loadPlaywright() {
  const tries = [() => require("playwright"), () => require("@playwright/test")];
  try {
    const root = execSync("npm root -g", { stdio: ["ignore", "pipe", "ignore"] }).toString().trim();
    tries.push(() => require(path.join(root, "playwright")));
  } catch (e) { /* npm not available */ }
  for (const t of tries) { try { return t(); } catch (e) { /* next */ } }
  console.error("Playwright не найден. Поставить: npm i -g playwright && npx playwright install chromium\n" +
    "(или указать готовый браузер: --browser /путь/к/chrome либо --channel chrome)");
  process.exit(2);
}

function serveDir(dir) {
  const root = path.resolve(dir);
  const server = http.createServer((req, res) => {
    const rel = decodeURIComponent(new URL(req.url, "http://x").pathname).replace(/^\/+/, "") || "index.html";
    const file = path.resolve(root, rel);
    if (!file.startsWith(root) || !fs.existsSync(file) || fs.statSync(file).isDirectory()) { res.writeHead(404); res.end("not found"); return; }
    res.writeHead(200, { "Content-Type": MIME[path.extname(file)] || "application/octet-stream",
      "Content-Security-Policy": "default-src 'self'; img-src 'self' data: blob:; style-src 'self'; script-src 'self'" });
    fs.createReadStream(file).pipe(res);
  });
  return new Promise((resolve) => server.listen(0, "127.0.0.1", () => resolve({ server, url: `http://127.0.0.1:${server.address().port}/` })));
}

// Runs inside the page. Keep it self-contained: it is serialized by Playwright.
function audit({ phone }) {
  const fails = [], warns = [];
  const vw = document.documentElement.clientWidth;
  const describe = (n) => {
    let s = n.tagName.toLowerCase();
    if (n.id) s += "#" + n.id;
    if (typeof n.className === "string" && n.className.trim()) s += "." + n.className.trim().split(/\s+/).slice(0, 3).join(".");
    const text = (n.textContent || "").trim().replace(/\s+/g, " ").slice(0, 40);
    return text ? `${s} «${text}»` : s;
  };
  const visible = (n) => {
    const r = n.getBoundingClientRect();
    if (!r.width || !r.height) return false;
    for (let e = n; e && e.nodeType === 1; e = e.parentElement) {
      const s = getComputedStyle(e);
      if (s.display === "none" || s.visibility === "hidden" || parseFloat(s.opacity) < 0.05) return false;
    }
    return true;
  };
  // 1. horizontal scroll
  if (document.documentElement.scrollWidth > vw + 1) {
    const offenders = [];
    for (const n of document.body.querySelectorAll("*")) {
      const r = n.getBoundingClientRect();
      if (r.width && r.right > vw + 1 && getComputedStyle(n).position !== "fixed") offenders.push(`${describe(n)} → ${Math.round(r.right)}px`);
      if (offenders.length >= 6) break;
    }
    fails.push({ check: "overflow", msg: `горизонтальная прокрутка: ширина ${document.documentElement.scrollWidth}px при окне ${vw}px`, items: offenders });
  }
  // 2. contrast of visible text
  const parse = (c) => { const m = c.match(/rgba?\(([^)]+)\)/); if (!m) return null; const p = m[1].split(/[\s,/]+/).filter(Boolean).map(Number); return [p[0], p[1], p[2], p.length > 3 ? p[3] : 1]; };
  const lin = (v) => { v /= 255; return v <= 0.04045 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4; };
  const lum = (c) => 0.2126 * lin(c[0]) + 0.7152 * lin(c[1]) + 0.0722 * lin(c[2]);
  const blend = (top, bottom) => { const a = top[3]; return [top[0] * a + bottom[0] * (1 - a), top[1] * a + bottom[1] * (1 - a), top[2] * a + bottom[2] * (1 - a), 1]; };
  const background = (n) => {
    const layers = [];
    for (let e = n; e && e.nodeType === 1; e = e.parentElement) {
      const s = getComputedStyle(e);
      if (s.backgroundImage && s.backgroundImage !== "none") return null; // text over images/gradients: judge by eye
      const c = parse(s.backgroundColor);
      if (c && c[3] > 0) { layers.push(c); if (c[3] >= 1) break; }
    }
    let base = [255, 255, 255, 1];
    const root = parse(getComputedStyle(document.documentElement).backgroundColor);
    if (root && root[3] > 0) base = root;
    for (let i = layers.length - 1; i >= 0; i--) base = blend(layers[i], base);
    return base;
  };
  const seen = new Set();
  const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT, { acceptNode: (t) => t.textContent.trim() ? NodeFilter.FILTER_ACCEPT : NodeFilter.FILTER_REJECT });
  let contrastFails = 0;
  while (walker.nextNode()) {
    const n = walker.currentNode.parentElement;
    if (!n || seen.has(n) || !visible(n) || n.closest("[disabled], [aria-disabled='true'], .visually-hidden, svg, option")) continue;
    seen.add(n);
    const s = getComputedStyle(n);
    const fg = parse(s.color);
    const bg = background(n);
    if (!fg || !bg) continue;
    const color = fg[3] < 1 ? blend(fg, bg) : fg;
    const [hi, lo] = [lum(color), lum(bg)].sort((a, b) => b - a);
    const ratio = (hi + 0.05) / (lo + 0.05);
    const size = parseFloat(s.fontSize);
    const large = size >= 24 || (size >= 18.66 && Number(s.fontWeight) >= 700);
    const need = large ? 3 : 4.5;
    if (ratio < need - 0.01 && contrastFails < 25) {
      contrastFails++;
      fails.push({ check: "contrast", msg: `${describe(n)}: ${ratio.toFixed(2)}:1, нужно ${need}:1 (${s.color} на rgb(${bg.slice(0, 3).map(Math.round).join(", ")}))` });
    }
    if (size < 12 && n.textContent.trim().length > 2) warns.push({ check: "font-size", msg: `${describe(n)}: шрифт ${size}px` });
  }
  // 3. names, labels, alt
  const nameOf = (n) => (n.getAttribute("aria-label") || n.getAttribute("title") || n.textContent || "").trim()
    || (n.getAttribute("aria-labelledby") && document.getElementById(n.getAttribute("aria-labelledby"))?.textContent.trim())
    || [...n.querySelectorAll("img[alt], svg[aria-label]")].map((i) => i.getAttribute("alt") || i.getAttribute("aria-label")).join(" ").trim();
  for (const n of document.querySelectorAll("button, a[href], [role='button'], [role='tab'], summary")) {
    if (visible(n) && !nameOf(n)) fails.push({ check: "name", msg: `${describe(n)}: у кнопки или ссылки нет текста или aria-label` });
  }
  for (const n of document.querySelectorAll("input:not([type=hidden]):not([type=checkbox]):not([type=radio]), select, textarea")) {
    if (!visible(n)) continue;
    const labelled = n.getAttribute("aria-label") || n.getAttribute("aria-labelledby") || n.closest("label")
      || (n.id && document.querySelector(`label[for="${CSS.escape(n.id)}"]`)) || n.getAttribute("title");
    if (!labelled) fails.push({ check: "label", msg: `${describe(n)}: у поля нет подписи (label или aria-label)` });
  }
  for (const n of document.querySelectorAll("input[type=checkbox], input[type=radio]")) {
    if (visible(n) && !(n.closest("label") || n.getAttribute("aria-label") || (n.id && document.querySelector(`label[for="${CSS.escape(n.id)}"]`))))
      fails.push({ check: "label", msg: `${describe(n)}: у переключателя нет подписи` });
  }
  for (const n of document.querySelectorAll("img")) if (visible(n) && !n.hasAttribute("alt")) fails.push({ check: "alt", msg: `${describe(n)}: нет alt` });
  // 4. tap targets
  for (const n of document.querySelectorAll("a[href], button, input:not([type=hidden]), select, textarea, summary, [role='button'], [role='tab']")) {
    if (!visible(n)) continue;
    const s = getComputedStyle(n);
    if (n.tagName === "A" && s.display === "inline") continue; // links inside running text are exempt
    const r = n.getBoundingClientRect();
    const target = (n.tagName === "INPUT" && (n.type === "checkbox" || n.type === "radio")) ? (n.closest("label") || n).getBoundingClientRect() : r;
    if (target.width < 24 || target.height < 24) fails.push({ check: "target", msg: `${describe(n)}: ${Math.round(target.width)}×${Math.round(target.height)}px, нужно не меньше 24×24` });
    else if (phone && (target.width < 44 || target.height < 44)) warns.push({ check: "target", msg: `${describe(n)}: ${Math.round(target.width)}×${Math.round(target.height)}px — на телефоне лучше 44×44` });
  }
  // 5. document-level
  if (!document.documentElement.lang) warns.push({ check: "lang", msg: "нет <html lang>" });
  const h1 = [...document.querySelectorAll("h1")].filter(visible).length;
  if (!h1) warns.push({ check: "h1", msg: "на экране нет заголовка h1" });
  return { fails, warns, title: document.title, height: document.documentElement.scrollHeight };
}

async function main() {
  const opts = parseArgs(process.argv.slice(2));
  const { chromium } = loadPlaywright();
  let served = null;
  let base = opts.url;
  if (opts.serve) { served = await serveDir(opts.serve); base = served.url; }
  fs.mkdirSync(opts.out, { recursive: true });
  const browser = await chromium.launch({ executablePath: opts.browser || process.env.UI_CHECK_BROWSER || undefined, channel: opts.channel });
  const runs = [];
  for (const vpName of opts.viewports) {
    const vp = VIEWPORTS[vpName];
    if (!vp) { console.error(`неизвестный размер: ${vpName}`); continue; }
    for (const theme of opts.themes) {
      const context = await browser.newContext({ viewport: { width: vp.width, height: vp.height }, isMobile: vp.isMobile,
        hasTouch: vp.hasTouch, colorScheme: theme, locale: "ru-RU", deviceScaleFactor: 1 });
      await context.addInitScript(({ storage }) => {
        window.__uiCheck = { csp: [] };
        document.addEventListener("securitypolicyviolation", (e) => window.__uiCheck.csp.push(`${e.violatedDirective}: ${e.blockedURI || e.sample || "inline"}`));
        for (const [k, v] of storage) { try { localStorage.setItem(k, v); } catch (e) { /* opaque origin */ } }
      }, { storage: opts.storage.map(([kv, asJson]) => { const i = kv.indexOf("="); const k = kv.slice(0, i); const v = kv.slice(i + 1); return [k, asJson ? JSON.stringify(v) : v]; }) });
      for (const route of opts.routes) {
        const page = await context.newPage();
        const errors = [];
        const origin = new URL(base).origin;
        page.on("pageerror", (e) => errors.push(`JS: ${e.message}`));
        page.on("console", (m) => { if (m.type() === "error") errors.push(`console: ${m.text()}`); });
        page.on("response", (r) => { if (r.status() >= 400 && r.url().startsWith(origin)) errors.push(`HTTP ${r.status()}: ${r.url().slice(origin.length)}`); });
        page.on("requestfailed", (r) => { if (r.url().startsWith(origin)) errors.push(`запрос не прошёл: ${r.url().slice(origin.length)} (${r.failure()?.errorText})`); });
        const url = route.startsWith("http") ? route : new URL(route, base).toString();
        await page.goto(url, { waitUntil: "networkidle" }).catch((e) => errors.push(`загрузка: ${e.message}`));
        if (opts.wait) await page.waitForSelector(opts.wait, { timeout: 10000 }).catch(() => errors.push(`не дождался ${opts.wait}`));
        await page.waitForTimeout(opts.settle);
        const result = await page.evaluate(audit, { phone: vpName === "phone" });
        const csp = await page.evaluate(() => window.__uiCheck?.csp || []);
        const shotName = `${(route || "root").replace(/[^a-z0-9]+/gi, "_").replace(/^_|_$/g, "") || "root"}-${vpName}-${theme}.png`;
        await page.screenshot({ path: path.join(opts.out, shotName), fullPage: opts.full });
        const fails = [...errors.map((msg) => ({ check: "errors", msg })), ...csp.map((msg) => ({ check: "csp", msg })), ...result.fails];
        runs.push({ route, viewport: vpName, theme, url, screenshot: shotName, title: result.title, fails, warns: result.warns });
        await page.close();
      }
      await context.close();
    }
  }
  if (opts.axe) {
    let axePath = opts.axe;
    if (axePath === "auto") { try { axePath = require.resolve("axe-core/axe.min.js"); } catch (e) { axePath = null; } }
    if (axePath && fs.existsSync(axePath)) {
      const context = await browser.newContext({ bypassCSP: true, locale: "ru-RU", viewport: { width: 1366, height: 900 } });
      await context.addInitScript(({ storage }) => { for (const [k, v] of storage) { try { localStorage.setItem(k, v); } catch (e) { /* ignore */ } } },
        { storage: opts.storage.map(([kv, asJson]) => { const i = kv.indexOf("="); return [kv.slice(0, i), asJson ? JSON.stringify(kv.slice(i + 1)) : kv.slice(i + 1)]; }) });
      for (const route of opts.routes) {
        const page = await context.newPage();
        await page.goto(new URL(route, base).toString(), { waitUntil: "networkidle" });
        await page.waitForTimeout(opts.settle);
        await page.addScriptTag({ path: axePath });
        const violations = await page.evaluate(async () => (await window.axe.run(document, { resultTypes: ["violations"] })).violations
          .map((v) => ({ id: v.id, impact: v.impact, help: v.help, nodes: v.nodes.length })));
        const run = runs.find((r) => r.route === route && r.viewport === "desktop") || runs.find((r) => r.route === route);
        for (const v of violations) (v.impact === "critical" || v.impact === "serious" ? run.fails : run.warns).push({ check: "axe", msg: `${v.id} (${v.impact}): ${v.help} — ${v.nodes} эл.` });
        await page.close();
      }
      await context.close();
    } else console.error("axe-core не найден: npm i axe-core (или --axe путь/к/axe.min.js) — проверка axe пропущена");
  }
  await browser.close();
  if (served) served.server.close();

  // reports
  fs.writeFileSync(path.join(opts.out, "report.json"), JSON.stringify(runs, null, 2));
  const totalFails = runs.reduce((n, r) => n + r.fails.length, 0);
  const totalWarns = runs.reduce((n, r) => n + r.warns.length, 0);
  const md = [`# Проверка интерфейса`, "", `${base} — ${runs.length} снимков, FAIL: ${totalFails}, WARN: ${totalWarns}`, "",
    "| Страница | Размер | Тема | FAIL | WARN | Снимок |", "|---|---|---|---|---|---|",
    ...runs.map((r) => `| ${r.route || "/"} | ${r.viewport} | ${r.theme} | ${r.fails.length} | ${r.warns.length} | ${r.screenshot} |`), ""];
  for (const r of runs) {
    if (!r.fails.length && !r.warns.length) continue;
    md.push(`## ${r.route || "/"} · ${r.viewport} · ${r.theme}`, "");
    for (const f of r.fails) md.push(`- FAIL [${f.check}] ${f.msg}${f.items ? "\n  - " + f.items.join("\n  - ") : ""}`);
    const warnCounts = {};
    for (const w of r.warns) { warnCounts[w.check] = (warnCounts[w.check] || 0) + 1; if (warnCounts[w.check] <= 5) md.push(`- WARN [${w.check}] ${w.msg}`); }
    for (const [check, n] of Object.entries(warnCounts)) if (n > 5) md.push(`- WARN [${check}] … и ещё ${n - 5}`);
    md.push("");
  }
  fs.writeFileSync(path.join(opts.out, "report.md"), md.join("\n"));
  const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
  fs.writeFileSync(path.join(opts.out, "index.html"), `<!doctype html><meta charset="utf-8"><title>Проверка интерфейса</title>
<style>body{font:14px system-ui;margin:16px;background:#f6f6f4}figure{display:inline-block;margin:8px;vertical-align:top;background:#fff;padding:8px;border-radius:8px}img{width:260px;display:block;border:1px solid #ddd}.f{color:#b3261e}</style>
<h1>Проверка интерфейса: FAIL ${totalFails}, WARN ${totalWarns}</h1>
${runs.map((r) => `<figure><a href="${esc(r.screenshot)}"><img src="${esc(r.screenshot)}" alt="${esc(r.route)} ${r.viewport} ${r.theme}"></a><figcaption>${esc(r.route || "/")} · ${r.viewport} · ${r.theme}<br><span class="${r.fails.length ? "f" : ""}">FAIL ${r.fails.length}</span> · WARN ${r.warns.length}</figcaption></figure>`).join("\n")}`);
  console.log(md.slice(0, 6 + runs.length).join("\n"));
  for (const r of runs) for (const f of r.fails) console.log(`FAIL ${r.route || "/"} ${r.viewport}/${r.theme} [${f.check}] ${f.msg}`);
  console.log(`\nОтчёт: ${path.join(opts.out, "report.md")} · снимки: ${opts.out}/`);
  const failed = totalFails > 0 || (opts.failOn === "warn" && totalWarns > 0);
  process.exit(failed ? 1 : 0);
}

main().catch((e) => { console.error(e); process.exit(2); });
