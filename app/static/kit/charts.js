// ui-studio kit — charts for live dashboards.
// sparkline() and meter() are dependency-free SVG/DOM; timeChart() wraps uPlot
// (kit/vendor/uplot, MIT) loaded as a classic <script> before the modules.
// Rules from the dataviz method: 2px lines, ~10% area wash, hairline solid grid,
// one y-axis per chart, legend for 2+ series, crosshair tooltip listing every
// series (value first), and a table view so no value is hover-only.
import { el, svgEl, fmt, token } from "./ui.js";

/** Sparkline: de-emphasis line + wash, accent dot on the latest value. */
export function sparkline(values, { min = 0, max = null, height = 32, width = 120, limit = null } = {}) {
  const pts = values.map((v, i) => [i, v]).filter(([, v]) => v !== null && v !== undefined);
  const svg = svgEl("svg", { viewBox: `0 0 ${width} ${height}`, preserveAspectRatio: "none", "aria-hidden": "true" });
  if (pts.length < 2) return svg;
  const hi = max ?? Math.max(...pts.map(([, v]) => v), min + 1e-9);
  const span = hi - min || 1;
  const x = (i) => (i / (values.length - 1)) * width;
  const y = (v) => height - 2 - ((Math.min(Math.max(v, min), hi) - min) / span) * (height - 4);
  const line = pts.map(([i, v]) => `${x(i).toFixed(1)},${y(v).toFixed(1)}`).join(" ");
  if (limit !== null && limit <= hi) {
    svg.append(svgEl("line", { class: "spark-limit", x1: 0, x2: width, y1: y(limit), y2: y(limit) }));
  }
  svg.append(svgEl("polygon", { class: "spark-area", points: `${x(pts[0][0])},${height} ${line} ${x(pts[pts.length - 1][0])},${height}` }));
  svg.append(svgEl("polyline", { class: "spark-line", points: line, "vector-effect": "non-scaling-stroke" }));
  const [li, lv] = pts[pts.length - 1];
  svg.append(svgEl("circle", { class: "spark-dot", cx: x(li), cy: y(lv), r: 3, "vector-effect": "non-scaling-stroke" }));
  return svg;
}

/** Meter: severity rides on the fill; returns the element (update with setMeter). */
export function meter(pct, lvl = "ok", { size = "", label = "" } = {}) {
  const fill = el("span", { class: "meter-fill" });
  const m = el("div", { class: `meter ${size}`.trim(), role: "meter", "aria-valuemin": 0, "aria-valuemax": 100 },
    fill);
  if (label) m.setAttribute("aria-label", label);
  setMeter(m, pct, lvl);
  return m;
}

export function setMeter(m, pct, lvl = "ok") {
  const fill = m.firstElementChild;
  const v = pct === null || pct === undefined ? 0 : Math.max(0, Math.min(100, pct));
  fill.style.width = `${v}%`;
  fill.dataset.level = lvl === "ok" ? "" : lvl;
  m.setAttribute("aria-valuenow", Math.round(v));
}

function rgba(hex, alpha) {
  const h = hex.replace("#", "");
  if (h.length !== 6) return hex;
  const [r, g, b] = [0, 2, 4].map((i) => parseInt(h.slice(i, i + 2), 16));
  return `rgba(${r}, ${g}, ${b}, ${alpha})`;
}

const rangeFmt = {
  seconds: new Intl.DateTimeFormat("ru-RU", { hour: "2-digit", minute: "2-digit", second: "2-digit" }),
  short: new Intl.DateTimeFormat("ru-RU", { hour: "2-digit", minute: "2-digit" }),
  day: new Intl.DateTimeFormat("ru-RU", { day: "numeric", month: "short" }),
  long: new Intl.DateTimeFormat("ru-RU", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" }),
};

/** Axis labels that never repeat: seconds for dense ticks, dates for multi-day spans. */
function timeTicks(splits) {
  const step = splits.length > 1 ? splits[1] - splits[0] : 60;
  const f = step < 60 ? rangeFmt.seconds : step >= 86400 ? rangeFmt.day : rangeFmt.short;
  return splits.map((v) => f.format(new Date(v * 1000)));
}

/**
 * Time-series chart. series: [{label, color: "--series-1", format: v => "…"}].
 * Returns {update(times, ...columns), setStale(bool), destroy(), element}.
 * Falls back to a message when uPlot is not loaded.
 */
export function timeChart(container, { series, height = 180, yMin = 0, yMax = null, format = (v) => fmt.num(v) }) {
  const wrap = el("div", { class: "chart" });
  const tip = el("div", { class: "chart-tip", role: "presentation" });
  const legend = el("div", { class: "chart-legend" });
  const empty = el("div", { class: "chart-empty" }, "Данных пока нет");
  wrap.append(tip, empty);
  container.append(wrap, legend);
  let data = [[], ...series.map(() => [])];
  let plot = null;

  const colors = () => series.map((s) => token(s.color) || "#888888");

  function renderLegend() {
    const cs = colors();
    legend.replaceChildren(...(series.length > 1 ? series.map((s, i) => {
      const key = el("span", { class: "key" });
      key.style.background = cs[i];
      return el("span", {}, key, s.label);
    }) : []));
  }

  function build() {
    if (plot) { plot.destroy(); plot = null; }
    renderLegend();
    if (!window.uPlot) { empty.textContent = "Графики недоступны: не загружен uPlot"; return; }
    const cs = colors();
    const grid = token("--grid") || "#ddd";
    const muted = token("--muted") || "#888";
    const font = `12px ${token("--font") || "system-ui"}`;
    const width = Math.max(200, wrap.clientWidth || container.clientWidth || 300);
    const opts = {
      width, height,
      padding: [8, 4, 0, 0],
      legend: { show: false },
      cursor: { drag: { x: false, y: false }, points: { size: 8, width: 2, fill: (u, i) => cs[i - 1], stroke: () => token("--surface") } },
      scales: {
        x: { time: true },
        y: {
          range: (u, min, max) => {
            const lo = yMin ?? Math.min(0, min ?? 0);
            const hi = Math.max(yMax ?? 0, (max ?? 0) * (yMax === null ? 1.1 : 1));
            return [lo, hi > lo ? hi : lo + 1]; // flat zero data still gets a sane axis
          },
        },
      },
      axes: [
        { stroke: muted, font, size: 28, space: 72, grid: { stroke: grid, width: 1 }, ticks: { stroke: grid, width: 1, size: 4 },
          values: (u, splits) => timeTicks(splits) },
        { stroke: muted, font, gap: 6, grid: { stroke: grid, width: 1 }, ticks: { show: false },
          size: (u, values) => Math.max(44, Math.max(0, ...(values || []).map((v) => String(v).length)) * 7 + 16),
          values: (u, splits) => splits.map((v) => format(v)) },
      ],
      series: [{}, ...series.map((s, i) => ({
        label: s.label, stroke: cs[i], width: 2, fill: series.length === 1 ? rgba(cs[i], 0.1) : undefined,
        points: { show: false }, spanGaps: false,
      }))],
      hooks: { setCursor: [showTip] },
    };
    plot = new window.uPlot(opts, data, wrap);
    wrap.append(tip);
  }

  function showTip(u) {
    const idx = u.cursor.idx;
    if (idx === null || idx === undefined || u.cursor.left < 0) { tip.classList.remove("on"); return; }
    const cs = colors();
    const rows = series.map((s, i) => {
      const key = el("span", { class: "key" });
      key.style.background = cs[i];
      const v = u.data[i + 1][idx];
      return el("div", { class: "tip-row" }, el("span", { class: "tip-value" }, v === null || v === undefined ? "—" : (s.format || format)(v)),
        el("span", { class: "tip-label" }, key, s.label));
    });
    const ts = u.data[0];
    const tf = ts.length > 1 && ts[1] - ts[0] < 60 ? rangeFmt.seconds : rangeFmt.long;
    tip.replaceChildren(el("div", { class: "tip-time" }, tf.format(new Date(ts[idx] * 1000))), ...rows);
    tip.classList.add("on");
    const over = u.over;
    const x = over.offsetLeft + u.cursor.left;
    const tw = tip.offsetWidth;
    tip.style.left = `${x + 14 + tw > wrap.clientWidth ? x - tw - 14 : x + 14}px`;
    tip.style.top = `${over.offsetTop + 6}px`;
  }

  const resize = new ResizeObserver(() => {
    if (plot) plot.setSize({ width: Math.max(200, wrap.clientWidth), height });
  });
  resize.observe(wrap);
  const onTheme = () => build();
  window.addEventListener("themechange", onTheme);
  build();

  return {
    element: wrap,
    update(times, ...columns) {
      data = [times, ...columns];
      empty.hidden = times.length > 1;
      if (plot) plot.setData(data);
    },
    setStale(on) { wrap.classList.toggle("stale", on); },
    data() { return data; },
    destroy() { resize.disconnect(); window.removeEventListener("themechange", onTheme); if (plot) plot.destroy(); wrap.remove(); legend.remove(); },
  };
}

/** Table twin of a chart: up to `rows` evenly spaced points, newest first. */
export function chartTable(times, columns, series, { rows = 12, format = (v) => fmt.num(v) } = {}) {
  const n = times.length;
  const step = Math.max(1, Math.ceil(n / rows));
  const picks = [];
  for (let i = n - 1; i >= 0; i -= step) picks.push(i);
  return el("div", { class: "table-wrap" }, el("table", { class: "table" },
    el("thead", {}, el("tr", {}, el("th", {}, "Время"), series.map((s) => el("th", { class: "num" }, s.label)))),
    el("tbody", {}, picks.map((i) => el("tr", {},
      el("td", { class: "num" }, rangeFmt.long.format(new Date(times[i] * 1000))),
      columns.map((col, c) => el("td", { class: "num" }, col[i] === null || col[i] === undefined ? "—" : (series[c].format || format)(col[i]))))))));
}
