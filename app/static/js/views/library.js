// Библиотека: каталог находок, бесплатные ресурсы, стартовые наборы — один поиск.
import { el, icon, mount, codeBlock } from "../../kit/ui.js";
import { api } from "../core.js";

export const title = "Библиотека";

const REPO = "https://github.com/letofftv/ClaudeRepo/blob/main/";
const RU = { yes: ["из России работает", "ok"], vpn: ["нужен VPN", "warn"], no: ["из России недоступно", "crit"], unknown: ["доступ не проверен", ""] };
const STATUS_LEVEL = { "взять": "ok", "попробовать": "info", "отклонено": "crit", "не нужно": "crit" };
const cache = {};

const load = async (key, path) => (cache[key] ||= await api.get(path));

export function render(main, params, query) {
  let tab = ["catalog", "resources", "sets"].includes(query.tab) ? query.tab : "catalog";
  let q = query.q || "";
  const filters = { direction: "", status: "взять", category: "", ru: false, local: false };
  const seg = el("div", { class: "seg", role: "group", "aria-label": "Раздел библиотеки" });
  const input = el("input", { class: "input", type: "search", placeholder: "Поиск по библиотеке", "aria-label": "Поиск по библиотеке", value: q });
  const filterBox = el("div", { class: "mt-3" });
  const count = el("p", { class: "small muted mt-3" });
  const list = el("div", { class: "stack gap-3 mt-3" });
  mount(main, el("div", { class: "cluster" }, seg, el("div", { class: "search" }, icon("search"), input)), filterBox, count, list);

  const keepUrl = () => {
    const qs = new URLSearchParams({ tab, ...(q ? { q } : {}) }).toString();
    history.replaceState(null, "", `#/library?${qs}`);
  };
  function renderSeg() {
    mount(seg, [["catalog", "Каталог"], ["resources", "Ресурсы"], ["sets", "Наборы"]].map(([k, label]) => el("button", {
      type: "button", "aria-pressed": String(k === tab), onclick: () => { tab = k; keepUrl(); renderSeg(); show(); } }, label)));
  }
  input.addEventListener("input", () => { q = input.value; keepUrl(); draw(); });

  let draw = () => {};
  async function show() {
    mount(list, el("div", { class: "skeleton" }), el("div", { class: "skeleton" }));
    try {
      if (tab === "catalog") await showCatalog();
      else if (tab === "resources") await showResources();
      else await showSets();
    } catch (e) {
      mount(list, el("div", { class: "alert", "data-level": "crit" }, icon("circle-alert"), e.message));
    }
  }

  async function showCatalog() {
    const c = await load("catalog", "/api/catalog");
    const dir = el("select", { class: "input", "aria-label": "Направление" }, el("option", { value: "" }, "Все направления"),
      Object.entries(c.directions).map(([k, v]) => el("option", { value: k, selected: k === filters.direction || null }, v)));
    const st = el("select", { class: "input", "aria-label": "Статус" }, el("option", { value: "" }, "Любой статус"),
      c.statuses.map((s) => el("option", { value: s, selected: s === filters.status || null }, s)));
    dir.addEventListener("change", () => { filters.direction = dir.value; draw(); });
    st.addEventListener("change", () => { filters.status = st.value; draw(); });
    mount(filterBox, el("div", { class: "grid-2" }, dir, st));
    draw = () => {
      const needle = q.trim().toLowerCase();
      const items = c.items.filter((i) => (!filters.direction || i.direction === filters.direction) && (!filters.status || i.status === filters.status)
        && (!needle || `${i.name} ${i.summary} ${i.install}`.toLowerCase().includes(needle)));
      count.textContent = `Показано ${items.length} из ${c.items.length}`;
      mount(list,
        !needle && !filters.direction ? c.packs.map((p) => el("div", { class: "card stack entry" },
          el("div", { class: "entry-head" }, el("strong", {}, `Свой пакет: ${p.name}`), el("span", { class: "badge", "data-level": "ok" }, "готов к установке")),
          el("p", {}, p.description), codeBlock(p.install))) : null,
        items.slice(0, 200).map((i) => el("div", { class: "card stack gap-2 entry" },
          el("div", { class: "entry-head" }, el("strong", {}, i.name), el("span", { class: "badge" }, i.direction_title),
            i.status ? el("span", { class: "badge", "data-level": STATUS_LEVEL[i.status] || "warn" }, i.status) : null),
          i.summary ? el("p", {}, i.summary) : null,
          el("div", { class: "link-row" },
            i.url ? el("a", { href: i.url, target: "_blank", rel: "noopener noreferrer" }, "Источник") : null,
            i.card ? el("a", { href: REPO + i.card, target: "_blank", rel: "noopener noreferrer" }, "Карточка с оценкой") : null),
          i.install ? codeBlock(i.install) : null)),
        items.length ? null : el("div", { class: "card empty" }, icon("search"), el("h3", {}, "Ничего не нашлось"), el("p", {}, "Попробуйте другой запрос или «Любой статус».")));
    };
    draw();
  }

  async function showResources() {
    const r = await load("resources", "/api/resources");
    const cats = r.categories || {};
    const cat = el("select", { class: "input", "aria-label": "Категория" }, el("option", { value: "" }, "Все категории"),
      Object.entries(cats).map(([k, v]) => el("option", { value: k, selected: k === filters.category || null }, v)));
    const ru = el("button", { class: "chip", type: "button", "aria-pressed": String(filters.ru) }, "Работает из России");
    const local = el("button", { class: "chip", type: "button", "aria-pressed": String(filters.local) }, "Локально");
    cat.addEventListener("change", () => { filters.category = cat.value; draw(); });
    ru.addEventListener("click", () => { filters.ru = !filters.ru; ru.setAttribute("aria-pressed", String(filters.ru)); draw(); });
    local.addEventListener("click", () => { filters.local = !filters.local; local.setAttribute("aria-pressed", String(filters.local)); draw(); });
    mount(filterBox, el("div", { class: "cluster" }, el("div", { class: "grow" }, cat), ru, local),
      r.note ? el("details", { class: "mt-3" }, el("summary", {}, "Как собраны данные"), el("p", { class: "small secondary" }, r.note)) : null);
    draw = () => {
      const needle = q.trim().toLowerCase();
      const items = (r.items || []).filter((i) => (!filters.category || i.category === filters.category || (i.also || []).includes(filters.category))
        && (!filters.ru || i.ru_access === "yes") && (!filters.local || i.kind === "local")
        && (!needle || JSON.stringify(i).toLowerCase().includes(needle))).sort((a, b) => (a.skip ? 1 : 0) - (b.skip ? 1 : 0));
      const picks = (r.picks || []).filter((p) => !filters.category || p.category === filters.category);
      count.textContent = `Показано ${items.length} из ${(r.items || []).length}`;
      mount(list,
        picks.length && !needle ? el("div", { class: "card stack gap-2" }, el("h3", {}, "Лучшее по категориям"),
          picks.map((p) => el("p", { class: "small" }, el("strong", {}, `${cats[p.category] || p.category}. `), p.text))) : null,
        items.map((i) => {
          const [ruText, ruLvl] = RU[i.ru_access] || RU.unknown;
          return el("div", { class: "card stack gap-2 entry" },
            el("div", { class: "entry-head" }, i.url ? el("a", { href: i.url, target: "_blank", rel: "noopener noreferrer" }, el("strong", {}, i.name)) : el("strong", {}, i.name),
              el("span", { class: "badge" }, cats[i.category] || i.category),
              i.kind === "local" ? el("span", { class: "badge", "data-level": "ok" }, "локально") : null,
              el("span", { class: "badge", "data-level": ruLvl }, ruText),
              i.commercial === false ? el("span", { class: "badge", "data-level": "warn" }, "только некоммерчески") : null,
              i.skip ? el("span", { class: "badge", "data-level": "crit" }, "не подходит") : null),
            i.free ? el("p", {}, `Бесплатно: ${i.free}`) : null,
            i.license ? el("p", {}, `Лицензия: ${i.license}`) : null,
            i.notes ? el("p", {}, i.notes) : null);
        }),
        items.length ? null : el("div", { class: "card empty" }, icon("search"), el("h3", {}, "Ничего не нашлось")));
    };
    draw();
  }

  async function showSets() {
    const s = await load("sets", "/api/starter-sets");
    mount(filterBox, el("p", { class: "small secondary" }, "Команды для мака выполняются в терминале мака, для сервера — на сервере. Чужие навыки перед установкой — через SkillSpector."));
    draw = () => {
      const needle = q.trim().toLowerCase();
      const sets = (s.sets || []).filter((x) => !needle || JSON.stringify(x).toLowerCase().includes(needle));
      count.textContent = `Наборов: ${sets.length}`;
      mount(list, sets.map((x) => el("div", { class: "card stack gap-3" },
        el("div", { class: "entry-head" }, el("strong", {}, x.title), x.where ? el("span", { class: "badge" }, x.where) : null),
        x.description ? el("p", { class: "secondary small" }, x.description) : null,
        (x.steps || []).map((step) => el("div", { class: "stack gap-2" },
          el("p", { class: "small" }, el("strong", {}, step.title), step.note ? ` — ${step.note}` : ""),
          step.commands ? codeBlock(step.commands) : null)))));
    };
    draw();
  }

  renderSeg();
  show();
  return null;
}
