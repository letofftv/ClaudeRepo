// Запуск: загрузка файла → подсказки по типу → форма; все инструменты и файлы.
import { el, icon, mount, fmt, confirmDialog, toast } from "../../kit/ui.js";
import { api, getTools, runSheet, suggestSheet, pickFiles, uploadFiles, download, fileType, TYPE_ICON, TYPE_LABEL, GROUPS, toolIcon } from "../core.js";

export const title = "Запуск";

export function render(main, params, query) {
  let tab = query.tab === "files" ? "files" : "tools";
  let group = "";
  let search = "";
  const seg = el("div", { class: "seg", role: "group", "aria-label": "Что показать" });
  const body = el("div", { class: "mt-4" });
  const drop = el("div", { class: "dropzone" },
    icon("upload", { cls: "xl" }),
    el("strong", {}, "Перетащите файлы в окно"),
    el("span", { class: "small" }, "или выберите — после загрузки пульт предложит подходящие действия"),
    el("button", { class: "btn mt-2", type: "button", onclick: () => pickFiles() }, icon("upload", { cls: "sm" }), "Выбрать файлы"));
  drop.addEventListener("dragover", (e) => { e.preventDefault(); drop.classList.add("over"); });
  drop.addEventListener("dragleave", () => drop.classList.remove("over"));
  drop.addEventListener("drop", () => drop.classList.remove("over")); // the window-wide handler uploads

  mount(main, drop,
    el("div", { class: "row between wrap mt-6" }, seg), body);

  function renderSeg() {
    mount(seg, [["tools", "Инструменты"], ["files", "Файлы"]].map(([k, label]) => el("button", {
      type: "button", "aria-pressed": String(k === tab),
      onclick: () => { tab = k; history.replaceState(null, "", `#/run${k === "files" ? "?tab=files" : ""}`); renderSeg(); show(); },
    }, label)));
  }

  async function showTools() {
    const tools = await getTools();
    const searchBox = el("div", { class: "search" }, icon("search"),
      el("input", { class: "input", type: "search", placeholder: "Найти инструмент", "aria-label": "Найти инструмент", value: search }));
    const input = searchBox.querySelector("input");
    const chips = el("div", { class: "chips", role: "group", "aria-label": "Группа" });
    const grid = el("div", { class: "grid-auto mt-4" });
    const unavailable = el("div", { class: "mt-6" });
    const draw = () => {
      mount(chips, [["", "Все"], ...Object.entries(GROUPS)].map(([k, label]) => el("button", {
        class: "chip", type: "button", "aria-pressed": String(k === group), onclick: () => { group = k; draw(); } }, label)));
      const q = search.trim().toLowerCase();
      const match = (t) => (!group || t.group === group) && (!q || `${t.title} ${t.description}`.toLowerCase().includes(q));
      const ok = tools.filter((t) => t.available && match(t));
      const off = tools.filter((t) => !t.available && match(t));
      mount(grid, ok.length ? ok.map(toolCard) : el("p", { class: "secondary" }, "Ничего не нашлось."));
      mount(unavailable, off.length ? el("details", { class: "card" },
        el("summary", {}, `Недоступны на этом сервере: ${off.length}`),
        el("div", { class: "list mt-2" }, off.map((t) => el("div", { class: "list-item" }, icon(toolIcon(t)),
          el("span", { class: "list-item-main" }, el("span", { class: "list-item-title" }, t.title), el("span", { class: "list-item-sub" }, t.reason)))))) : null);
    };
    input.addEventListener("input", () => { search = input.value; draw(); });
    mount(body, el("div", { class: "cluster" }, searchBox, chips), grid, unavailable);
    draw();
  }

  function toolCard(t) {
    return el("div", { class: "card tool-card" },
      el("div", { class: "tool-head" }, icon(toolIcon(t)), el("h4", {}, t.title)),
      el("p", {}, t.description),
      el("div", { class: "tool-foot" }, el("span", { class: "badge" }, GROUPS[t.group] || t.group),
        el("button", { class: "btn sm", type: "button", onclick: () => runSheet(t) }, icon("play", { cls: "sm" }), "Запустить")));
  }

  async function showFiles() {
    const files = await api.get("/api/files");
    mount(body, files.length ? el("div", { class: "card flush list" }, files.map((f) => {
      const type = fileType(f.name);
      return el("div", { class: "list-item" }, icon(TYPE_ICON[type]),
        el("span", { class: "list-item-main" }, el("span", { class: "list-item-title" }, f.name),
          el("span", { class: "list-item-sub" }, `${TYPE_LABEL[type]} · ${fmt.bytes(f.size)} · ${fmt.when(f.mtime)}`)),
        el("span", { class: "inline-actions" },
          el("button", { class: "btn sm", type: "button", onclick: () => suggestSheet(f) }, "Что сделать"),
          el("button", { class: "btn ghost sm icon-only", type: "button", "aria-label": `Скачать ${f.name}`, onclick: () => download(f.path) }, icon("download", { cls: "sm" })),
          el("button", { class: "btn ghost sm icon-only", type: "button", "aria-label": `Удалить ${f.name}`, onclick: async () => {
            if (!(await confirmDialog(`Удалить ${f.name} из рабочей папки? Результаты задач останутся.`, { title: "Удалить файл", okText: "Удалить", danger: true }))) return;
            try { await api.del("/api/files/" + encodeURIComponent(f.name)); toast("Файл удалён"); showFiles(); } catch (e) { toast(e.message, { level: "crit" }); }
          } }, icon("trash-2", { cls: "sm" }))));
    })) : el("div", { class: "card empty" }, icon("inbox"), el("h3", {}, "Файлов нет"),
      el("p", {}, "Загруженные файлы появятся здесь. Результаты задач — в разделе «Задачи»."),
      el("button", { class: "btn", type: "button", onclick: () => pickFiles(uploadFiles) }, "Загрузить файл")));
  }

  function show() {
    (tab === "files" ? showFiles() : showTools()).catch((e) => mount(body, el("div", { class: "alert", "data-level": "crit" }, icon("circle-alert"), e.message)));
  }

  const onFiles = () => { if (tab === "files") showFiles(); };
  window.addEventListener("hub:files", onFiles);
  renderSeg();
  show();
  return () => window.removeEventListener("hub:files", onFiles);
}
