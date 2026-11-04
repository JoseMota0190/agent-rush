/* AGENT RUSH — PRE-GAME WIZARD (sin dependencias, script clásico) */
(() => {
  "use strict";

  const i18n = window.AgentRushI18n;
  const t = (key, vars) => (i18n ? i18n.t(key, vars) : key);

  const AGENTS = ["strategist", "coder", "auditor"];

  const overlay = document.getElementById("wizard");
  if (!overlay) return;

  const stepEl = document.getElementById("wizard-step");
  const titleEl = document.getElementById("wizard-title");
  const closeBtn = document.getElementById("wizard-close");
  const backBtn = document.getElementById("wizard-back");
  const submitBtn = document.getElementById("wizard-submit");
  const errorEl = document.getElementById("wizard-error");
  const requiredEl = document.getElementById("wizard-required");
  const modeChipEl = document.getElementById("wizard-mode-chip");

  const modePane = overlay.querySelector('[data-pane="mode"]');
  const modelsPane = overlay.querySelector('[data-pane="models"]');
  const footEl = overlay.querySelector(".wizard-foot");
  const modeBtns = [...overlay.querySelectorAll(".wizard-mode")];

  const presetSelect = document.getElementById("wiz-preset");
  const selects = {
    strategist: document.getElementById("wiz-strategist"),
    coder: document.getElementById("wiz-coder"),
    auditor: document.getElementById("wiz-auditor"),
  };

  const state = {
    step: 1,
    mode: null,
    locked: false,
    loaded: false,
    loading: false,
    models: [],
    agents: {},
    presets: {},
  };

  /* ---------------------------------------------------------
     Datos
     --------------------------------------------------------- */
  async function getJSON(url) {
    const res = await fetch(url);
    if (!res.ok) throw new Error("HTTP " + res.status);
    return res.json();
  }

  function readSavedModels() {
    try {
      const raw = window.sessionStorage.getItem("agentrush.models");
      if (!raw) return null;
      const parsed = JSON.parse(raw);
      return parsed && typeof parsed === "object" ? parsed : null;
    } catch (_) {
      return null;
    }
  }

  async function loadData() {
    if (state.loaded || state.loading) return;

    state.loading = true;
    setError("");

    try {
      const [modelsRes, agentsRes, presetsRes] = await Promise.all([
        getJSON("/api/models"),
        getJSON("/api/agents"),
        getJSON("/api/presets"),
      ]);

      state.models = Array.isArray(modelsRes.models) ? modelsRes.models : [];
      state.agents = agentsRes.agents && typeof agentsRes.agents === "object"
        ? agentsRes.agents
        : {};
      state.presets = presetsRes.presets && typeof presetsRes.presets === "object"
        ? presetsRes.presets
        : {};
      state.loaded = true;

      fillSelects();
    } catch (err) {
      setError(t("wizard.error"));
    } finally {
      state.loading = false;
      render();
    }
  }

  function setError(message) {
    if (!errorEl) return;
    errorEl.textContent = message || "";
    errorEl.hidden = !message;
  }

  function addOption(select, value, label) {
    if (!select) return;
    const opt = document.createElement("option");
    opt.value = value;
    opt.textContent = label;
    select.appendChild(opt);
  }

  function fillSelects() {
    const saved = readSavedModels();
    const firstModel = state.models[0] ? state.models[0].id : "";

    // Preset opcional
    if (presetSelect) {
      presetSelect.innerHTML = "";
      addOption(presetSelect, "", t("models.placeholder"));
      for (const name of Object.keys(state.presets)) {
        addOption(presetSelect, name, name);
      }
      presetSelect.value = "";
      presetSelect.disabled = state.models.length === 0;
    }

    for (const agent of AGENTS) {
      const select = selects[agent];
      if (!select) continue;

      select.innerHTML = "";
      addOption(select, "", t("models.placeholder"));

      for (const model of state.models) {
        addOption(select, model.id, model.id);
      }

      const savedValue = saved && saved[agent];
      const agentValue = state.agents[agent] && state.agents[agent].model_id;
      const value = [savedValue, agentValue, firstModel].find(
        (candidate) => candidate && state.models.some((m) => m.id === candidate)
      );

      select.value = value || "";
      select.disabled = state.models.length === 0;
    }

    refreshValidation();
  }

  /* ---------------------------------------------------------
     Render
     --------------------------------------------------------- */
  function refreshValidation() {
    const values = AGENTS.map((agent) => (selects[agent] ? selects[agent].value : ""));
    const complete = state.mode !== null && values.every(Boolean);

    if (submitBtn) submitBtn.disabled = !complete;
    if (requiredEl) requiredEl.hidden = complete || state.step !== 2;
  }

  function showLoadingSelects() {
    if (presetSelect) {
      presetSelect.innerHTML = "";
      addOption(presetSelect, "", t("wizard.loading"));
    }
    for (const agent of AGENTS) {
      const select = selects[agent];
      if (!select) continue;
      select.innerHTML = "";
      addOption(select, "", t("wizard.loading"));
    }
  }

  function render() {
    if (modePane) modePane.hidden = state.step !== 1;
    if (modelsPane) modelsPane.hidden = state.step !== 2;
    if (footEl) footEl.hidden = state.step !== 2;

    if (titleEl) {
      titleEl.textContent = t(
        state.step === 1 ? "wizard.title.mode" : "wizard.title.models"
      );
    }
    if (stepEl) {
      stepEl.textContent = t("wizard.step", { n: state.step });
    }

    if (modeChipEl) {
      if (state.mode) {
        modeChipEl.textContent = t("wizard.modeChip", {
          mode: t("modes." + state.mode + ".title"),
        });
        modeChipEl.hidden = false;
      } else {
        modeChipEl.hidden = true;
      }
    }

    if (backBtn) {
      backBtn.hidden = !(state.step === 2 && !state.locked);
    }

    refreshValidation();

    // Traduce etiquetas estáticas del modal (no el título dinámico)
    if (i18n && i18n.apply) i18n.apply(overlay);
  }

  function focusFirst() {
    if (state.step === 1) {
      modeBtns[0] && modeBtns[0].focus();
    } else if (presetSelect) {
      presetSelect.focus();
    }
  }

  /* ---------------------------------------------------------
     Abrir / cerrar
     --------------------------------------------------------- */
  function open(mode) {
    if (mode) {
      state.locked = true;
      state.mode = mode;
      state.step = 2;
    } else {
      state.locked = false;
      state.mode = null;
      state.step = 1;
    }

    overlay.hidden = false;
    document.body.classList.add("wizard-open");

    if (!state.loaded) showLoadingSelects();

    render();
    focusFirst();

    if (!state.loaded) loadData();
  }

  function close() {
    overlay.hidden = true;
    document.body.classList.remove("wizard-open");
    setError("");
  }

  function chooseMode(mode) {
    if (!mode) return;
    state.mode = mode;
    state.step = 2;
    render();
    focusFirst();
  }

  /* ---------------------------------------------------------
     Presets
     --------------------------------------------------------- */
  function applyPreset(name) {
    const preset = state.presets[name];
    if (!preset) return;

    for (const agent of AGENTS) {
      const select = selects[agent];
      const value = preset[agent];
      if (!select || !value) continue;

      if (![...select.options].some((opt) => opt.value === value)) {
        addOption(select, value, value);
      }
      select.value = value;
    }

    refreshValidation();
  }

  /* ---------------------------------------------------------
     Submit
     --------------------------------------------------------- */
  function submit() {
    const values = {
      mode: state.mode,
      strategist: selects.strategist ? selects.strategist.value : "",
      coder: selects.coder ? selects.coder.value : "",
      auditor: selects.auditor ? selects.auditor.value : "",
    };

    if (!values.mode || AGENTS.some((agent) => !values[agent])) {
      refreshValidation();
      return;
    }

    try {
      window.sessionStorage.setItem("agentrush.models", JSON.stringify(values));
      window.sessionStorage.setItem("agentrush.mode", values.mode);
    } catch (_) {
      /* ignore */
    }

    // Persistir como defaults para la próxima selección (no bloquea la navegación)
    fetch("/api/agents", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      keepalive: true,
      body: JSON.stringify({
        agents: {
          strategist: values.strategist,
          coder: values.coder,
          auditor: values.auditor,
        },
      }),
    }).catch(() => {});

    window.location.href = "/game.html?mode=" + encodeURIComponent(values.mode);
  }

  /* ---------------------------------------------------------
     Eventos
     --------------------------------------------------------- */
  document.querySelectorAll("[data-wizard-mode]").forEach((el) => {
    el.addEventListener("click", (e) => {
      e.preventDefault();
      open(el.getAttribute("data-wizard-mode"));
    });
  });

  const enterGame = document.getElementById("enter-game");
  if (enterGame) {
    enterGame.addEventListener("click", (e) => {
      e.preventDefault();
      open(null);
    });
  }

  modeBtns.forEach((btn) => {
    btn.addEventListener("click", () => chooseMode(btn.getAttribute("data-mode")));
  });

  if (backBtn) {
    backBtn.addEventListener("click", () => {
      if (state.locked) return;
      state.step = 1;
      state.mode = null;
      render();
      focusFirst();
    });
  }

  if (closeBtn) closeBtn.addEventListener("click", close);

  overlay.addEventListener("click", (e) => {
    if (e.target === overlay) close();
  });

  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && !overlay.hidden) close();
  });

  if (presetSelect) {
    presetSelect.addEventListener("change", () => applyPreset(presetSelect.value));
  }

  for (const agent of AGENTS) {
    const select = selects[agent];
    if (select) select.addEventListener("change", refreshValidation);
  }

  if (submitBtn) submitBtn.addEventListener("click", submit);

  document.addEventListener("agentrush:langchange", () => {
    if (overlay.hidden) return;

    // Re-traducir opciones dinámicas
    if (presetSelect && presetSelect.options.length) {
      presetSelect.options[0].textContent = t("models.placeholder");
    }
    for (const agent of AGENTS) {
      const select = selects[agent];
      if (select && select.options.length) {
        select.options[0].textContent = t("models.placeholder");
      }
    }
    render();
  });

  /* ---------------------------------------------------------
     Auto-abrir desde el redirect de la sala (?select=1)
     --------------------------------------------------------- */
  const qs = new URLSearchParams(location.search);
  if (qs.get("select") === "1") {
    const mode = qs.get("mode");
    open(["spectator", "orchestrator"].includes(mode) ? mode : null);
  }
})();
