/* AGENT RUSH — VULTR MODEL CATALOG (solo lectura, sin dependencias) */
(() => {
  "use strict";

  const i18n = window.AgentRushI18n;
  const t = (key, vars) => (i18n ? i18n.t(key, vars) : key);

  const grid = document.getElementById("model-catalog");
  const countEl = document.getElementById("model-count");

  const state = { status: "loading", models: [] };

  function render() {
    if (!grid) return;

    grid.className = "vultr-model-grid";
    grid.innerHTML = "";

    if (state.status === "loading") {
      grid.textContent = t("models.catalog.loading");
      grid.classList.add("is-message");
      if (countEl) countEl.textContent = "";
      return;
    }

    if (state.status === "error") {
      grid.textContent = t("models.catalog.error");
      grid.classList.add("is-message", "is-error");
      if (countEl) countEl.textContent = "";
      return;
    }

    if (countEl) {
      countEl.textContent = t("models.catalog.count", { n: state.models.length });
    }

    for (const model of state.models) {
      const card = document.createElement("div");
      card.className = "vultr-model";

      const bullet = document.createElement("span");
      bullet.className = "vultr-model-bullet";
      bullet.setAttribute("aria-hidden", "true");

      const body = document.createElement("div");
      body.className = "vultr-model-body";

      const top = document.createElement("div");
      top.className = "vultr-model-top";

      const idEl = document.createElement("div");
      idEl.className = "vultr-model-id";
      idEl.textContent = model.id;

      const tag = document.createElement("span");
      tag.className = "vultr-model-tag";
      tag.textContent = t("models.catalog.chat");

      top.append(idEl, tag);
      body.appendChild(top);

      if (model.description) {
        const descEl = document.createElement("div");
        descEl.className = "vultr-model-desc";
        descEl.textContent = model.description;
        body.appendChild(descEl);
      }

      card.append(bullet, body);
      grid.appendChild(card);
    }
  }

  async function load() {
    if (!grid) return;

    state.status = "loading";
    render();

    try {
      const res = await fetch("/api/models");
      if (!res.ok) throw new Error("HTTP " + res.status);
      const data = await res.json();
      state.models = Array.isArray(data.models) ? data.models : [];
      state.status = "ready";
    } catch (err) {
      state.models = [];
      state.status = "error";
    }

    render();
  }

  document.addEventListener("agentrush:langchange", render);

  load();
})();
