/* AGENT RUSH — LEADERBOARD (sin dependencias) */
(() => {
  "use strict";

  const $ = (id) => document.getElementById(id);
  const i18n = window.AgentRushI18n;
  const t = (key, vars) => (i18n ? i18n.t(key, vars) : key);

  let cached = null;

  async function fetchLeaderboard() {
    try {
      const res = await fetch("/api/leaderboard");
      if (!res.ok) throw new Error("HTTP " + res.status);
      return await res.json();
    } catch (err) {
      console.error("Leaderboard fetch falló:", err);
      return null;
    }
  }

  function formatTokens(tokens) {
    return Number(tokens || 0).toLocaleString("en-US");
  }

  function buildEmptyState() {
    const box = document.createElement("div");
    box.className = "lb-empty";

    const icon = document.createElement("div");
    icon.className = "lb-empty-icon";
    icon.setAttribute("aria-hidden", "true");
    icon.innerHTML =
      '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">' +
      '<path d="M7 3h10M7 21h10M8 3c0 4 3 5 4 6-1 1-4 2-4 6M16 3c0 4-3 5-4 6 1 1 4 2 4 6"/>' +
      "</svg>";

    const title = document.createElement("div");
    title.className = "lb-empty-title";
    title.textContent = t("lb.empty.title");

    const text = document.createElement("p");
    text.className = "lb-empty-text";
    text.textContent = t("lb.empty.text");

    box.append(icon, title, text);
    return box;
  }

  function renderPanel(mode, data, container) {
    container.innerHTML = "";

    const rows = Array.isArray(data.rows) ? data.rows : [];

    const panel = document.createElement("div");
    panel.className = "landing-lb-panel";

    const head = document.createElement("div");
    head.className = "landing-lb-head";

    const title = document.createElement("h3");
    title.className = "landing-lb-title";
    title.textContent = t("lb.mode." + mode);

    const badge = document.createElement("span");
    badge.className =
      "landing-lb-badge " + (rows.length ? "is-live" : "is-waiting");
    badge.textContent = rows.length ? t("lb.badge.live") : t("lb.badge.waiting");

    head.append(title, badge);
    panel.appendChild(head);

    if (rows.length === 0) {
      panel.appendChild(buildEmptyState());
      container.appendChild(panel);
      return;
    }

    const table = document.createElement("table");
    table.className = "lb-table";

    const thead = document.createElement("thead");
    const headRow = document.createElement("tr");
    ["rank", "squad", "time", "tokens", "status"].forEach((key) => {
      const th = document.createElement("th");
      th.textContent = t("lb.headers." + key);
      headRow.appendChild(th);
    });
    thead.appendChild(headRow);
    table.appendChild(thead);

    const tbody = document.createElement("tbody");
    rows.forEach((row) => {
      const tr = document.createElement("tr");
      tr.className =
        "lb-row " +
        (row.success ? "ok-row" : "error-row") +
        (row.rank === 1 ? " top" : "");

      const cells = [
        [row.rank, ""],
        [row.squad, "squad"],
        [row.time, "mono"],
        [formatTokens(row.tokens), "mono"],
      ];

      cells.forEach(([value, cls]) => {
        const td = document.createElement("td");
        if (cls) td.className = cls;
        td.textContent = value;
        tr.appendChild(td);
      });

      const statusTd = document.createElement("td");
      const status = document.createElement("span");
      status.className =
        "status-badge " + (row.success ? "success" : "error");
      status.textContent = row.success
        ? t("lb.status.ok")
        : t("lb.status.error");
      statusTd.appendChild(status);
      tr.appendChild(statusTd);

      tbody.appendChild(tr);
    });
    table.appendChild(tbody);
    panel.appendChild(table);

    container.appendChild(panel);
  }

  function renderError(slot, message) {
    slot.innerHTML = "";

    const panel = document.createElement("div");
    panel.className = "landing-lb-panel";

    const head = document.createElement("div");
    head.className = "landing-lb-head";
    const title = document.createElement("h3");
    title.className = "landing-lb-title";
    title.textContent = t("lb.error.title");
    head.appendChild(title);

    const body = document.createElement("div");
    body.className = "lb-error";
    body.textContent = message;

    panel.append(head, body);
    slot.appendChild(panel);
  }

  function renderAll(data) {
    const slot = $("leaderboards-slot");
    if (!slot) return;

    const modes = [];
    if (data.spectator) modes.push(["spectator", data.spectator]);
    if (data.orchestrator) modes.push(["orchestrator", data.orchestrator]);
    if (modes.length === 0 && data.mode) modes.push([data.mode, data]);

    slot.innerHTML = "";

    const grid = document.createElement("div");
    grid.className = "landing-leaderboards-grid";
    if (modes.length === 1) grid.classList.add("is-single");

    modes.forEach(([mode, modeData]) => {
      const wrapper = document.createElement("div");
      wrapper.className = "landing-lb-panel-wrapper";

      const container = document.createElement("div");
      container.className = "landing-lb-table-container";

      wrapper.appendChild(container);
      grid.appendChild(wrapper);
      renderPanel(mode, modeData, container);
    });

    slot.appendChild(grid);
  }

  async function init() {
    const slot = $("leaderboards-slot");
    if (!slot) return;

    const data = await fetchLeaderboard();
    if (!data) {
      renderError(slot, t("lb.error.load"));
      return;
    }

    cached = data;
    renderAll(data);
  }

  document.addEventListener("agentrush:langchange", () => {
    if (cached) {
      renderAll(cached);
      return;
    }
    const slot = $("leaderboards-slot");
    if (slot) renderError(slot, t("lb.error.load"));
  });

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
