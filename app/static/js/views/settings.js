// Настройки: тема, обновления, место, выход.
import { el, icon, mount, fmt, toast, getTheme, setTheme } from "../../kit/ui.js";
import { api, live, getTools, refreshLive } from "../core.js";

export const title = "Настройки";

export function render(main) {
  const seg = el("div", { class: "seg", role: "group", "aria-label": "Тема оформления" });
  const drawSeg = () => mount(seg, [["auto", "Как в системе"], ["light", "Светлая"], ["dark", "Тёмная"]].map(([k, label]) =>
    el("button", { type: "button", "aria-pressed": String(getTheme() === k), onclick: () => { setTheme(k); drawSeg(); } }, label)));
  drawSeg();
  const updateBox = el("div");
  const usageBox = el("p", { class: "secondary small" }, "Считаем…");
  mount(main, el("div", { class: "stack gap-4" },
      el("div", { class: "card stack" }, el("h3", {}, "Оформление"), seg),
      el("div", { class: "card stack" }, el("h3", {}, "Версия и обновления"), updateBox),
      el("div", { class: "card stack" }, el("h3", {}, "Место под задачи"), usageBox, el("a", { class: "btn ghost", href: "#/jobs" }, "Открыть задачи")),
      el("div", { class: "card stack" }, el("h3", {}, "Вход"),
        el("p", { class: "secondary small" }, "Токен хранится только в этом браузере. «Выйти» стирает его — понадобится ввести снова."),
        el("button", { class: "btn danger", type: "button", onclick: () => { api.setToken(""); window.dispatchEvent(new Event("hub:unauthorized")); } },
          icon("log-out", { cls: "sm" }), "Выйти")),
      el("div", { class: "card stack" }, el("h3", {}, "О пульте"),
        el("p", { class: "secondary small" }, "Домашний пульт — часть репозитория ClaudeRepo. Интерфейс собран пакетом ui-studio («создатель интерфейсов»)."),
        el("div", { class: "link-row" },
          el("a", { href: "https://github.com/letofftv/ClaudeRepo/blob/main/app/README.md", target: "_blank", rel: "noopener noreferrer" }, "Описание пульта"),
          el("a", { href: "https://github.com/letofftv/ClaudeRepo/blob/main/app/CHANGELOG.md", target: "_blank", rel: "noopener noreferrer" }, "Что нового"),
          el("a", { href: "https://github.com/letofftv/ClaudeRepo/tree/main/coding/packs/ui-studio", target: "_blank", rel: "noopener noreferrer" }, "ui-studio")))));

  api.get("/api/jobs/usage").then((u) => { usageBox.textContent = `${u.jobs} задач · ${u.files} файлов · ${fmt.bytes(u.bytes)}`; })
    .catch((e) => { usageBox.textContent = e.message; });

  Promise.all([getTools(), api.get("/api/metrics")]).then(([tools, m]) => {
    const tool = tools.find((t) => t.id === "update_now");
    const u = m.update;
    mount(updateBox,
      el("dl", { class: "kv" },
        el("dt", {}, "Версия"), el("dd", {}, `${m.version}${m.repo?.commit ? ` · ${m.repo.commit}` : ""}`),
        el("dt", {}, "Последняя проверка"), el("dd", {}, u ? fmt.ago(u.time) : "обновлятор не настроен"),
        u?.message ? el("dt", {}, "Итог") : null, u?.message ? el("dd", {}, u.message) : null),
      tool && tool.available
        ? el("button", { class: "btn ghost", type: "button", onclick: async () => {
          try { await api.post("/api/jobs", { tool: "update_now", params: {} }); toast("Проверка обновлений запущена"); refreshLive(); }
          catch (e) { toast(e.message, { level: "crit" }); }
        } }, icon("refresh-cw", { cls: "sm" }), "Обновить сейчас")
        : el("p", { class: "hint" }, tool ? `Кнопка недоступна: ${tool.reason}` : "Автообновление ставится по app/deploy/server-prompt.md."));
  }).catch((e) => mount(updateBox, el("p", { class: "error-text" }, e.message)));
  return null;
}
