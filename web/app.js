/* ============================================================
   AGENT RUSH  -  controlador de la interfaz
   - escena 3D (Three.js) + rail de paneles
   - compuerta de inicio + challenge card (sin guion demo)
   - stream de logs por SSE con filtros y detalles expandibles
   - estado de salas, IDE, energía y estados de misión reales
   ============================================================ */

import {
  initScene,
  setMode as setSceneMode,
  setBotState,
  setEnvironmentState,
} from "./scene.js?v=1762400080";

(() => {
  "use strict";

  const $ = (sel, root = document) => root.querySelector(sel);
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

    const tag = $("#logsModeTag");
    if (tag) tag.textContent = t("game.logs.tag." + mode);
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
    String(s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;");

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
    return String(code)
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

  let currentCode = CODE;
  let currentFilename = "room1.py";

  function renderIDE() {
    const codeEl = $("#ideCode");
    const gutterEl = $("#ideGutter");
    if (!codeEl || !gutterEl) return;
    codeEl.innerHTML = highlight(currentCode);
    const lines = currentCode.split("\n").length;
    gutterEl.textContent = Array.from({ length: lines }, (_, i) => i + 1).join("\n");
  }

  function updateIDE(code, filename) {
    if (!code) return;
    currentCode = code;
    if (filename) currentFilename = filename;

    const badge = $(".panel-ide .badge");
    if (badge) badge.textContent = currentFilename;

    renderIDE();
  }

  renderIDE();

  /* ---------------------------------------------------------
     3. LOG STREAM / ENERGÍA / FILTROS / MISIÓN
     --------------------------------------------------------- */
  const logStream = $("#logStream");
  const logCountEl = $("#logCount");
  const tokenCountEl = $("#tokenCount");
  const logFoot = $("#logFoot");
  const logEmpty = $("#logEmpty");
  const pauseBtn = $("#pauseLogs");
  const missionEl = $("#missionState");
  const runIdChip = $("#runIdChip");
  const filterBtns = $$(".log-filter");
  const successPanel = $("#missionSuccess");
  const successRoomsEl = $("#successRooms");
  const successTokensEl = $("#successTokens");
  const successTimeEl = $("#successTime");

  const energyChip = $("#energy");
  const energyUsedEl = $("#energyUsed");
  const energyBudgetEl = $("#energyBudget");
  const energyFillEl = $("#energyFill");

  const metrics = { events: 0, tokens: 0, paused: false };
  const TOKEN_BUDGET =
    Number(new URLSearchParams(location.search).get("budget")) || 100000;

  let started = false;
  let disqualified = false;
  let activeFilter = "all";
  let currentMissionState = "ready";

  if (energyBudgetEl) {
    energyBudgetEl.textContent = TOKEN_BUDGET.toLocaleString("en-US");
  }

  const MISSION_KEYS = {
    ready: "game.mission.ready",
    active: "game.mission.active",
    audit: "game.mission.audit",
    unlocked: "game.mission.unlocked",
    failed: "game.mission.failed",
    aborted: "game.mission.aborted",
    disqualified: "game.mission.disqualified",
  };

  function setMissionState(state) {
    currentMissionState = state;
    if (!missionEl) return;
    missionEl.dataset.state = state;
    missionEl.textContent = t(MISSION_KEYS[state] || MISSION_KEYS.ready);
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
            kind: "audit",
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

  function stamp(ts) {
    const date = ts ? new Date(Number(ts) * 1000) : new Date();
    return date.toTimeString().slice(0, 8);
  }

  function inferKind(evt) {
    if (evt.kind) return evt.kind;
    if (evt.src === "sandbox") return "execution";
    if (evt.src === "auditor" || evt.src === "referee") return "audit";
    if (evt.src === "coder") return "code";
    return "chat";
  }

  function setFilter(filter) {
    activeFilter = filter;
    filterBtns.forEach((btn) => {
      const active = btn.dataset.filter === filter;
      btn.classList.toggle("is-active", active);
      btn.setAttribute("aria-pressed", String(active));
    });

    if (!logStream) return;
    $$(".log-line", logStream).forEach((line) => {
      line.classList.toggle(
        "hidden-by-filter",
        filter !== "all" && line.dataset.kind !== filter
      );
    });
  }

  filterBtns.forEach((btn) => {
    btn.addEventListener("click", () => setFilter(btn.dataset.filter || "all"));
  });

  function appendLog(evt) {
    if (!logStream) return;

    const kind = inferKind(evt);
    const nearBottom =
      logStream.scrollHeight - logStream.scrollTop - logStream.clientHeight < 90;

    const line = document.createElement("div");
    line.className = `log-line src-${evt.src} type-${kind} ${evt.cls || ""}`.trim();
    line.dataset.kind = kind;
    if (activeFilter !== "all" && kind !== activeFilter) {
      line.classList.add("hidden-by-filter");
    }

    const timeEl = document.createElement("span");
    timeEl.className = "t";
    timeEl.textContent = stamp(evt.ts);

    const src = document.createElement("span");
    src.className = "src";
    src.textContent = String(evt.src || "system").toUpperCase();

    const msg = document.createElement("span");
    msg.className = "msg";

    const badge = document.createElement("span");
    badge.className = "log-badge";
    badge.textContent = t("game.events.type." + kind);
    msg.append(badge, document.createTextNode(evt.msg || ""));

    line.append(timeEl, src, msg);

    if (evt.code) {
      const details = document.createElement("details");
      details.className = "log-details";
      const summary = document.createElement("summary");
      summary.textContent =
        t("game.logs.codeSummary") +
        (evt.filename ? " · " + evt.filename : "");
      const pre = document.createElement("pre");
      pre.textContent = evt.code;
      details.append(summary, pre);
      line.appendChild(details);
    }

    if (evt.stdout || evt.stderr) {
      const details = document.createElement("details");
      details.className = "log-details";
      const summary = document.createElement("summary");
      summary.textContent = t("game.logs.execSummary");
      const pre = document.createElement("pre");
      const chunks = [];
      if (evt.stdout) chunks.push(evt.stdout.replace(/\s+$/, ""));
      if (evt.stderr) chunks.push(evt.stderr.replace(/\s+$/, ""));
      pre.textContent = chunks.filter(Boolean).join("\n");
      details.append(summary, pre);
      line.appendChild(details);
    }

    if (evt.exitCode != null) {
      const exit = document.createElement("span");
      const ok = Number(evt.exitCode) === 0;
      exit.className = "log-exit " + (ok ? "is-ok" : "is-error");
      exit.textContent = t("game.logs.exit", { code: evt.exitCode });
      line.appendChild(exit);
    }

    logStream.appendChild(line);
    if (nearBottom || metrics.events === 0) {
      logStream.scrollTop = logStream.scrollHeight;
    }

    metrics.events += 1;
    metrics.tokens += Number(evt.tokens) || 0;
    updateLogCount();
    if (tokenCountEl) tokenCountEl.textContent = metrics.tokens.toLocaleString("en-US");
    if (logEmpty) logEmpty.hidden = true;

    updateEnergy();
  }

  /* ---------------------------------------------------------
     4. ESTADO DE SALAS
     --------------------------------------------------------- */
  const roomsState = [
    { state: "active", attempt: 1, max: 3 },
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
          max: info.max ?? 3,
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
      roomsState[index + 1] = { state: "active", attempt: 1, max: 3 };
    }
    renderRooms();
    setLevel(Math.min(3, index + 2));
  }

  /* ---------------------------------------------------------
     5. VISTA MÓVIL (ROOM / LOGS)
     --------------------------------------------------------- */
  const viewTabs = $("#viewTabs");

  function setMobileView(view) {
    const safe = view === "logs" ? "logs" : "room";
    document.body.dataset.mobileView = safe;
    if (!viewTabs) return;
    $$(".view-tab", viewTabs).forEach((btn) => {
      const active = btn.dataset.view === safe;
      btn.classList.toggle("is-active", active);
      btn.setAttribute("aria-pressed", String(active));
    });
  }

  viewTabs?.addEventListener("click", (e) => {
    const btn = e.target.closest(".view-tab");
    if (!btn) return;
    setMobileView(btn.dataset.view);
  });

  setMobileView("room");

  /* ---------------------------------------------------------
     6. INICIO DE PARTIDA (run real + SSE)
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

    if (next === "idle") {
      setMissionState("ready");
      setEnvironmentState("ready");
    } else if (next === "starting" || next === "running") {
      if (!["audit", "unlocked", "failed", "aborted", "disqualified"].includes(currentMissionState)) {
        setMissionState("active");
      }
      setEnvironmentState("active");
    } else if (next === "completed") {
      setMissionState("unlocked");
      setEnvironmentState("unlocked");
    } else if (next === "failed") {
      setMissionState("failed");
      setEnvironmentState("ready");
    }

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
    if (successPanel) successPanel.hidden = true;

    if (logStream) logStream.hidden = false;
    if (logFoot) logFoot.hidden = false;
    if (pauseBtn) pauseBtn.hidden = false;
    if (logEmpty) logEmpty.hidden = metrics.events > 0;

    const statusPanel = $("#statusPanel");
    if (statusPanel) statusPanel.hidden = false;

    const statusContent = $("#statusContent");
    if (statusContent) statusContent.hidden = false;

    const idePanel = $("#idePanel");
    if (idePanel) idePanel.hidden = false;

    roomsState[0] = { state: "active", attempt: 1, max: 3 };
    roomsState[1] = { state: "locked" };
    roomsState[2] = { state: "locked" };
    renderRooms();
    setLevel(1);
    setMissionState("active");
    setEnvironmentState("active");
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
        if (runIdChip) {
          runIdChip.textContent = "RUN · " + String(evt.run_id || "").toUpperCase();
        }
        if (successPanel) successPanel.hidden = true;
        setMissionState("active");
        setEnvironmentState("active");
        appendLog({
          src: "system",
          msg: `run_started · mode=${evt.mode}`,
          kind: "chat",
          ts: evt.ts,
        });
        break;

      case "challenge":
        renderChallenge(evt);
        setMissionState("active");
        setEnvironmentState("active");
        setBotState("strategist", "thinking");
        break;

      case "agent": {
        const src = evt.agent === "system" ? "system" : evt.agent;
        const kind =
          src === "coder" ? "code" :
          src === "auditor" || src === "referee" ? "audit" : "chat";

        appendLog({
          src,
          msg: evt.msg,
          kind,
          code: evt.code,
          filename: evt.filename,
          ts: evt.ts,
          tokens: evt.tokens,
        });

        if (src === "strategist") setBotState("strategist", "thinking");
        if (src === "coder") {
          setBotState("coder", "typing");
          setBotState("strategist", "idle");
          setMissionState("active");
          if (evt.code) updateIDE(evt.code, evt.filename);
        }
        if (src === "auditor") {
          setBotState("auditor", "thinking");
          setMissionState("audit");
        }
        if (src === "referee") {
          setBotState("auditor", "approved");
          setMissionState("audit");
        }
        break;
      }

      case "sandbox": {
        appendLog({
          src: "sandbox",
          msg: evt.msg,
          kind: "execution",
          stdout: evt.stdout,
          stderr: evt.stderr,
          exitCode: evt.exit_code,
          cls: evt.cls,
          ts: evt.ts,
        });
        if (evt.room) {
          const info = roomsState[Number(evt.room) - 1];
          if (info) {
            info.attempt = Number(evt.attempt) || info.attempt || 1;
            info.max = Number(evt.max_attempts) || info.max || 3;
            renderRooms();
          }
        }
        setMissionState("audit");
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
        setMissionState("audit");
        setEnvironmentState("active");
        setTimeout(() => setBotState("auditor", "idle"), 1600);
        break;

      case "run_completed":
        runFinished = true;
        runRooms = Number(evt.rooms_solved) || 0;
        closeRunStream();
        setRunState("completed");
        setBotState("strategist", "idle");
        setBotState("coder", "idle");
        setBotState("auditor", "approved");
        appendLog({
          src: "referee",
          msg: `RUN COMPLETE · ${runRooms}/3 rooms · ${evt.duration}s`,
          kind: "audit",
          cls: "is-ok",
          ts: evt.ts,
        });
        if (successPanel && successRoomsEl && successTokensEl && successTimeEl) {
          const roomsSolved = Number(evt.rooms_solved) || 0;
          const tokens = Number(evt.tokens) || metrics.tokens || 0;
          const duration = Number(evt.duration) || 0;
          const mm = String(Math.floor(duration / 60)).padStart(2, "0");
          const ss = String(Math.floor(duration % 60)).padStart(2, "0");
          successRoomsEl.textContent = `${roomsSolved}/3`;
          successTokensEl.textContent = tokens.toLocaleString("en-US");
          successTimeEl.textContent = `${mm}:${ss}`;
          successPanel.hidden = false;
        }
        break;

      case "disqualified":
        runFinished = true;
        closeRunStream();
        setRunState("failed");
        setMissionState("disqualified");
        setEnvironmentState("ready");
        if (energyChip) energyChip.classList.add("is-dead");
        if (successPanel) successPanel.hidden = true;
        appendLog({
          src: "system",
          msg: evt.message || t("game.log.disqualified"),
          kind: "audit",
          cls: "is-error",
          ts: evt.ts,
        });
        break;

      case "run_failed":
        runFinished = true;
        closeRunStream();
        setRunState("failed");
        setMissionState("failed");
        setBotState("coder", "error");
        if (successPanel) successPanel.hidden = true;
        appendLog({
          src: "system",
          msg: evt.message || "Run failed",
          kind: "audit",
          cls: "is-error",
          ts: evt.ts,
        });
        break;

      case "aborted":
        runFinished = true;
        closeRunStream();
        setRunState("failed");
        setMissionState("aborted");
        setBotState("coder", "error");
        if (successPanel) successPanel.hidden = true;
        appendLog({
          src: "system",
          msg: evt.message || "Run aborted",
          kind: "audit",
          cls: "is-error",
          ts: evt.ts,
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
        setMissionState("failed");
        appendLog({
          src: "system",
          msg: t("game.start.connectionLost"),
          kind: "audit",
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
    setMobileView("logs");

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
        kind: "chat",
        cls: "is-dim",
      });
      openRunStream();
    } catch (err) {
      runFinished = true;
      setRunState("failed");
      setMissionState("failed");
      appendLog({
        src: "system",
        msg: t("game.start.error") + ": " + err.message,
        kind: "audit",
        cls: "is-error",
      });
    }
  }

  $$("[data-start]").forEach((btn) => {
    btn.addEventListener("click", startRun);
  });

  /* ---------------------------------------------------------
     7. ACCIONES DEL IDE
     --------------------------------------------------------- */
  $$(".action").forEach((btn) => {
    btn.addEventListener("click", () => {
      if (!started) return;

      const map = {
        edit: { src: "system", msg: "manual edit · orchestrator took control of buffer", kind: "chat" },
        run:  { src: "sandbox", msg: "dispatch → sandbox · exec room1.py (10s cap)", kind: "execution" },
        hint: { src: "referee", msg: "hint 1/3 · the token lives in auth.log", kind: "audit" },
        skip: { src: "system", msg: "skip requested · requires referee approval", kind: "audit", cls: "is-error" },
      };
      const evt = map[btn.dataset.action];
      if (evt) appendLog(evt);
    });
  });

  /* ---------------------------------------------------------
     8. SALIDA
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
     9. ARRANQUE
     --------------------------------------------------------- */
  setMode(targetMode);
  renderRooms();
  setLevel(1);
  updatePauseLabel();
  updateLogCount();
  updateEnergy();
  setRunState("idle");
  setMissionState("ready");
  setEnvironmentState("ready");
  setFilter("all");

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
    setMissionState(currentMissionState);
    if (currentChallenge) renderChallenge(currentChallenge);
  });
})();
