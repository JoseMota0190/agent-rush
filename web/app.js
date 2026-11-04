/* ============================================================
   AGENT RUSH  -  controlador de la interfaz
   - escena 3D (Three.js) + rail de paneles
   - compuerta de inicio + challenge card (sin guion demo)
   - stream de logs por SSE (cuando exista backend)
   - estado de salas e IDE
   ============================================================ */

import { initScene, setMode as setSceneMode, setBotState } from "./scene.js?v=42";

(() => {
  "use strict";

  const $  = (sel, root = document) => root.querySelector(sel);
  const $$ = (sel, root = document) => [...root.querySelectorAll(sel)];

  const i18n = window.AgentRushI18n;
  const t = (key, vars) => (i18n ? i18n.t(key, vars) : key);

  /* ---------------------------------------------------------
     0. MODO Y GUARDIA DE SELECCIÓN
     --------------------------------------------------------- */
  const params = new URLSearchParams(location.search);
  const MODES = ["spectator", "orchestrator"];

  let targetMode = params.get("mode");
  if (!MODES.includes(targetMode)) {
    targetMode = sessionStorage.getItem("agentrush.mode");
  }
  if (!MODES.includes(targetMode)) targetMode = "spectator";

  function hasModelSelection() {
    try {
      const raw = sessionStorage.getItem("agentrush.models");
      if (!raw) return false;
      const parsed = JSON.parse(raw);
      return Boolean(
        parsed && parsed.strategist && parsed.coder && parsed.auditor
      );
    } catch (_) {
      return false;
    }
  }

  if (!hasModelSelection()) {
    window.location.replace(
      "/?select=1&mode=" + encodeURIComponent(targetMode)
    );
    return;
  }

  /* ---------------------------------------------------------
     1. ESCENA 3D
     --------------------------------------------------------- */
  const canvas = $("#scene3d");
  const labelLayer = $("#labels");
  initScene(canvas, labelLayer);

  const ROOM_LABEL_KEY = {
    spectator: "game.roomLabel.spectator",
    orchestrator: "game.roomLabel.orchestrator",
  };

  function updateModeBadge() {
    const badge = $("#modeBadgeText");
    const mode = document.body.dataset.mode || targetMode;
    if (badge) badge.textContent = t("modes." + mode + ".title");
  }

  function setMode(mode) {
    document.body.dataset.mode = mode;

    const label = $("[data-mode-label]");
    if (label) label.textContent = t(ROOM_LABEL_KEY[mode] || "");

    setSceneMode(mode);
    if (mode === "orchestrator") renderIDE();
    updateModeBadge();
  }

  /* ---------------------------------------------------------
     2. IDE
     --------------------------------------------------------- */
  const CODE = `import hashlib

def find_token(log_path):
    """Room 1  -  recover the access token from auth.log."""
    token = None
    with open(log_path) as fh:
        for line in fh:
            if "ACCESS_TOKEN=" in line:
                token = line.split("=", 1)[1].strip()
    if token is None:
        raise ValueError("token not found")

    return hashlib.sha256(token.encode()).hexdigest()


def verify(proof, expected):
    assert proof == expected, "checksum mismatch"
    return "PROOF:" + proof`;

  const KEYWORDS = new Set([
    "def", "for", "in", "while", "return", "if", "else", "elif", "assert",
    "import", "from", "class", "with", "as", "pass", "True", "False", "None",
    "raise", "not", "and", "or", "is", "try", "except", "lambda",
  ]);

  const escapeHTML = (s) =>
    s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");

  const TOKEN_RE =
    /("(?:[^"\\]|\\.)*"|'(?:[^'\\]|\\.)*')|(\b\d+\b)|([A-Za-z_][A-Za-z0-9_]*)(?=\s*\()|([A-Za-z_][A-Za-z0-9_]*)/g;

  function highlightCode(text) {
    let out = "";
    let last = 0;
    let m;

    TOKEN_RE.lastIndex = 0;
    while ((m = TOKEN_RE.exec(text)) !== null) {
      out += escapeHTML(text.slice(last, m.index));

      const [raw, str, num, call, word] = m;
      if (str)        out += `<span class="str">${escapeHTML(str)}</span>`;
      else if (num)   out += `<span class="num">${num}</span>`;
      else if (call)  out += `<span class="fn">${call}</span>`;
      else if (word && KEYWORDS.has(word)) out += `<span class="kw">${word}</span>`;
      else            out += escapeHTML(raw);

      last = m.index + raw.length;
    }

    out += escapeHTML(text.slice(last));
    return out;
  }

  function highlight(code) {
    return code
      .split("\n")
      .map((line) => {
        const hash = line.indexOf("#");
        if (hash === -1) return highlightCode(line);
        return (
          highlightCode(line.slice(0, hash)) +
          `<span class="cm">${escapeHTML(line.slice(hash))}</span>`
        );
      })
      .join("\n");
  }

  function renderIDE() {
    const codeEl = $("#ideCode");
    const gutterEl = $("#ideGutter");
    if (!codeEl || !gutterEl) return;
    codeEl.innerHTML = highlight(CODE);
    const lines = CODE.split("\n").length;
    gutterEl.textContent = Array.from({ length: lines }, (_, i) => i + 1).join("\n");
  }

  renderIDE();

  /* ---------------------------------------------------------
     3. LOG STREAM / ENERGÍA
     --------------------------------------------------------- */
  const logStream = $("#logStream");
  const logCountEl = $("#logCount");
  const tokenCountEl = $("#tokenCount");
  const logFoot = $("#logFoot");
  const pauseBtn = $("#pauseLogs");

  const energyChip = $("#energy");
  const energyUsedEl = $("#energyUsed");
  const energyBudgetEl = $("#energyBudget");
  const energyFillEl = $("#energyFill");

  const metrics = { events: 0, tokens: 0, paused: false };
  const TOKEN_BUDGET =
    Number(new URLSearchParams(location.search).get("budget")) || 100000;

  let started = false;
  let disqualified = false;

  if (energyBudgetEl) {
    energyBudgetEl.textContent = TOKEN_BUDGET.toLocaleString("en-US");
  }

  function updateLogCount() {
    if (logCountEl) logCountEl.textContent = t("game.events", { n: metrics.events });
  }

  function updatePauseLabel() {
    if (!pauseBtn) return;
    pauseBtn.textContent = metrics.paused ? t("game.resume") : t("game.pause");
    pauseBtn.style.color = metrics.paused ? "var(--amber)" : "";
  }

  pauseBtn?.addEventListener("click", () => {
    metrics.paused = !metrics.paused;
    updatePauseLabel();
  });

  function updateEnergy() {
    if (!energyUsedEl || !energyFillEl) return;

    const used = metrics.tokens;
    const pct = Math.min(100, (used / TOKEN_BUDGET) * 100);

    energyUsedEl.textContent = used.toLocaleString("en-US");
    energyFillEl.style.width = pct + "%";

    if (!energyChip) return;

    energyChip.classList.remove("is-warn", "is-danger", "is-dead");

    const label = energyChip.querySelector(".energy-label");
    if (label) {
      label.textContent =
        used >= TOKEN_BUDGET ? t("game.energy.dead") : t("game.energy.label");
    }

    if (used >= TOKEN_BUDGET) {
      energyChip.classList.add("is-dead");
      if (!disqualified) {
        disqualified = true;
        setTimeout(() => {
          appendLog({
            src: "system",
            msg: t("game.log.disqualified"),
            cls: "is-error",
          });
        }, 0);
      }
    } else if (pct >= 90) {
      energyChip.classList.add("is-danger");
    } else if (pct >= 70) {
      energyChip.classList.add("is-warn");
    }
  }

  const stamp = () => new Date().toTimeString().slice(0, 8);

  function appendLog(evt) {
    if (!logStream) return;

    const line = document.createElement("div");
    line.className = `log-line src-${evt.src} ${evt.cls || ""}`.trim();

    const timeEl = document.createElement("span");
    timeEl.className = "t";
    timeEl.textContent = stamp();

    const src = document.createElement("span");
    src.className = "src";
    src.textContent = evt.src.toUpperCase().padEnd(8, " ");

    const msg = document.createElement("span");
    msg.className = "msg";
    msg.textContent = evt.msg;

    line.append(timeEl, src, msg);
    logStream.appendChild(line);
    logStream.scrollTop = logStream.scrollHeight;

    metrics.events += 1;
    metrics.tokens += evt.tokens ?? 0;
    updateLogCount();
    if (tokenCountEl) tokenCountEl.textContent = metrics.tokens.toLocaleString("en-US");

    updateEnergy();
  }

  /* ---------------------------------------------------------
     4. ESTADO DE SALAS
     --------------------------------------------------------- */
  const roomsState = [
    { state: "active", attempt: 1, max: 5 },
    { state: "locked" },
    { state: "locked" },
  ];

  function renderRooms() {
    $$("#roomList .room").forEach((room, i) => {
      const info = roomsState[i];
      if (!info) return;

      room.classList.toggle("is-done", info.state === "done");
      room.classList.toggle("is-active", info.state === "active");

      const meta = room.querySelector(".room-meta");
      if (!meta) return;

      if (info.state === "done") {
        meta.textContent = t("game.room.meta.resolved", {
          status: t("game.room.resolved"),
          time: info.time || "00:00",
        });
      } else if (info.state === "active") {
        meta.textContent = t("game.room.meta.inProgress", {
          status: t("game.room.inProgress"),
          attempt: info.attempt ?? 1,
          max: info.max ?? 5,
        });
      } else {
        meta.textContent = t("game.room.locked");
      }
    });
  }

  function setLevel(level) {
    const value = String(level);
    const lvl = $("#currentLevel");
    const lvlFoot = $("#currentLevelFoot");
    if (lvl) lvl.textContent = value;
    if (lvlFoot) lvlFoot.textContent = value;
  }

  function markRoom(index, time) {
    if (!roomsState[index]) return;

    roomsState[index] = { state: "done", time };
    if (roomsState[index + 1]) {
      roomsState[index + 1] = { state: "active", attempt: 1, max: 5 };
    }
    renderRooms();
    setLevel(Math.min(3, index + 2));
  }

  /* ---------------------------------------------------------
     5. INICIO DE PARTIDA (run real + SSE)
     --------------------------------------------------------- */
  let runState = "idle";
  let currentRunId = null;
  let runSource = null;
  let runFinished = false;
  let runRooms = 0;
  let currentChallenge = null;

  const RUN_LABELS = {
    idle: "game.start.cta",
    starting: "game.start.connecting",
    running: "game.start.running",
    completed: "game.start.completedShort",
    failed: "game.start.failedShort",
  };

  function getSelectedModels() {
    try {
      const raw = sessionStorage.getItem("agentrush.models");
      if (!raw) return null;
      const parsed = JSON.parse(raw);
      if (parsed && parsed.strategist && parsed.coder && parsed.auditor) {
        return {
          strategist: parsed.strategist,
          coder: parsed.coder,
          auditor: parsed.auditor,
        };
      }
    } catch (_) {
      /* ignore */
    }
    return null;
  }

  function renderRunNote() {
    let note = t("game.start.engine");
    if (runState === "starting") note = t("game.start.connecting");
    if (runState === "running") note = t("game.start.running");
    if (runState === "completed") note = t("game.start.completed", { rooms: runRooms });
    if (runState === "failed") note = t("game.start.failed");

    $$(".challenge-engine").forEach((el) => {
      el.textContent = note;
    });
  }

  function setRunState(next) {
    runState = next;
    const disabled = next !== "idle";

    $$("[data-start]").forEach((btn) => {
      btn.disabled = disabled;
      const label = btn.querySelector("span:not(.start-btn-icon)");
      if (label) label.textContent = t(RUN_LABELS[next] || "game.start.cta");
    });

    renderRunNote();
  }

  function renderChallenge(challenge) {
    if (!challenge) return;
    currentChallenge = challenge;

    $$("[data-challenge]").forEach((card) => {
      const kicker = card.querySelector(".challenge-kicker");
      const title = card.querySelector("h3");
      const desc = card.querySelector("p:not(.challenge-engine)");
      const goal = card.querySelector(".challenge-goal span:last-child");

      if (kicker) {
        kicker.removeAttribute("data-i18n");
        kicker.textContent = t("game.challenge.roomKicker", { n: challenge.room });
      }
      if (title) {
        title.removeAttribute("data-i18n");
        title.textContent = challenge.title;
      }
      if (desc) {
        desc.removeAttribute("data-i18n");
        desc.textContent = challenge.description;
      }
      if (goal) {
        goal.removeAttribute("data-i18n");
        goal.textContent = challenge.objective;
      }
    });
  }

  function showStartedUI() {
    started = true;
    document.body.classList.add("is-started");

    $$("[data-start-gate]").forEach((el) => { el.hidden = true; });
    $$("[data-challenge]").forEach((el) => { el.hidden = false; });

    if (logStream) logStream.hidden = false;
    if (logFoot) logFoot.hidden = false;
    if (pauseBtn) pauseBtn.hidden = false;

    const statusContent = $("#statusContent");
    if (statusContent) statusContent.hidden = false;

    const idePanel = $("#idePanel");
    if (idePanel) idePanel.hidden = false;

    roomsState[0] = { state: "active", attempt: 1, max: 5 };
    roomsState[1] = { state: "locked" };
    roomsState[2] = { state: "locked" };
    renderRooms();
    setLevel(1);
    updateLogCount();
    updateEnergy();
  }

  function closeRunStream() {
    if (runSource) {
      runSource.close();
      runSource = null;
    }
  }

  function handleRunEvent(evt) {
    if (!evt || !evt.type) return;

    switch (evt.type) {
      case "run_started":
        appendLog({ src: "system", msg: `run_started · mode=${evt.mode}` });
        break;

      case "challenge":
        renderChallenge(evt);
        setBotState("strategist", "thinking");
        break;

      case "agent": {
        const src = evt.agent === "system" ? "system" : evt.agent;
        appendLog({ src, msg: evt.msg });
        if (evt.agent === "strategist") setBotState("strategist", "thinking");
        if (evt.agent === "coder") setBotState("coder", "typing");
        if (evt.agent === "auditor") setBotState("auditor", "thinking");
        break;
      }

      case "sandbox": {
        appendLog({ src: "sandbox", msg: evt.msg, cls: evt.cls });
        if (evt.stdout) {
          evt.stdout.split("\n").filter(Boolean).slice(0, 20).forEach((line) => {
            appendLog({ src: "sandbox", msg: "  " + line });
          });
        }
        if (evt.stderr) {
          evt.stderr.split("\n").filter(Boolean).slice(0, 20).forEach((line) => {
            appendLog({ src: "sandbox", msg: "  " + line, cls: "is-error" });
          });
        }
        break;
      }

      case "energy":
        metrics.tokens = Number(evt.tokens) || 0;
        if (tokenCountEl) tokenCountEl.textContent = metrics.tokens.toLocaleString("en-US");
        updateEnergy();
        break;

      case "room_solved":
        markRoom(evt.index, evt.time);
        setBotState("auditor", "approved");
        setTimeout(() => setBotState("auditor", "idle"), 1600);
        break;

      case "run_completed":
        runFinished = true;
        runRooms = Number(evt.rooms_solved) || 0;
        closeRunStream();
        setRunState("completed");
        appendLog({
          src: "referee",
          msg: `RUN COMPLETE · ${runRooms}/3 rooms · ${evt.duration}s`,
          cls: "is-ok",
        });
        break;

      case "disqualified":
        runFinished = true;
        closeRunStream();
        setRunState("failed");
        if (energyChip) energyChip.classList.add("is-dead");
        appendLog({
          src: "system",
          msg: evt.message || t("game.log.disqualified"),
          cls: "is-error",
        });
        break;

      case "run_failed":
      case "aborted":
        runFinished = true;
        closeRunStream();
        setRunState("failed");
        appendLog({
          src: "system",
          msg: evt.message || "Run failed",
          cls: "is-error",
        });
        break;

      default:
        break;
    }
  }

  function openRunStream() {
    closeRunStream();
    runSource = new EventSource(`/api/runs/${currentRunId}/events`);
    runSource.onmessage = (e) => {
      try {
        handleRunEvent(JSON.parse(e.data));
      } catch (_) {
        /* ignore malformed event */
      }
    };
    runSource.onerror = () => {
      if (!runFinished) {
        runFinished = true;
        setRunState("failed");
        appendLog({
          src: "system",
          msg: t("game.start.connectionLost"),
          cls: "is-error",
        });
      }
      closeRunStream();
    };
  }

  async function startRun() {
    if (runState !== "idle") return;

    const models = getSelectedModels();
    if (!models) {
      window.location.href = "/?select=1&mode=" + encodeURIComponent(targetMode);
      return;
    }

    setRunState("starting");
    showStartedUI();

    try {
      const res = await fetch("/api/runs", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ mode: targetMode, models }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        throw new Error(data.error || "HTTP " + res.status);
      }
      currentRunId = data.run_id;
      setRunState("running");
      appendLog({
        src: "system",
        msg: `connecting to run ${currentRunId} …`,
        cls: "is-dim",
      });
      openRunStream();
    } catch (err) {
      runFinished = true;
      setRunState("failed");
      appendLog({
        src: "system",
        msg: t("game.start.error") + ": " + err.message,
        cls: "is-error",
      });
    }
  }

  $$("[data-start]").forEach((btn) => {
    btn.addEventListener("click", startRun);
  });

  /* ---------------------------------------------------------
     6. ACCIONES DEL IDE
     --------------------------------------------------------- */
  $$(".action").forEach((btn) => {
    btn.addEventListener("click", () => {
      if (!started) return;

      const map = {
        edit: { src: "system",  msg: "manual edit · orchestrator took control of buffer" },
        run:  { src: "sandbox", msg: "dispatch → sandbox · exec room1.py (10s cap)" },
        hint: { src: "referee", msg: "hint 1/3 · the token lives in auth.log" },
        skip: { src: "system",  msg: "skip requested · requires referee approval", cls: "is-error" },
      };
      const evt = map[btn.dataset.action];
      if (evt) appendLog(evt);
    });
  });

  /* ---------------------------------------------------------
     7. SALIDA
     --------------------------------------------------------- */
  const exitBtn = $("#exitRoom");
  exitBtn?.addEventListener("click", () => {
    if (started && !window.confirm(t("game.exit.confirm"))) return;
    if (currentRunId && !runFinished) {
      fetch(`/api/runs/${currentRunId}/abort`, { method: "POST" }).catch(() => {});
    }
    window.location.href = "/";
  });

  /* ---------------------------------------------------------
     8. ARRANQUE
     --------------------------------------------------------- */
  setMode(targetMode);
  renderRooms();
  setLevel(1);
  updatePauseLabel();
  updateLogCount();
  updateEnergy();
  setRunState("idle");

  document.addEventListener("keydown", (e) => {
    if (e.key === " " && !pauseBtn?.hidden) {
      e.preventDefault();
      pauseBtn?.click();
    }
  });

  // Cambio de idioma: re-render del contenido dinámico
  document.addEventListener("agentrush:langchange", () => {
    const label = $("[data-mode-label]");
    if (label) {
      label.textContent = t(ROOM_LABEL_KEY[document.body.dataset.mode] || "");
    }
    updateModeBadge();
    renderRooms();
    updatePauseLabel();
    updateEnergy();
    updateLogCount();
    setRunState(runState);
    if (currentChallenge) renderChallenge(currentChallenge);
  });
})();
