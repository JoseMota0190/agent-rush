/* ============================================================
   AGENT RUSH — controlador de la interfaz
   - escena 3D (Three.js) + rail de paneles
   - stream de logs (SSE si hay backend, demo si no)
   - leaderboard, estado de salas e IDE
   ============================================================ */

import { initScene, setMode as setSceneMode, setBotState } from "./scene.js?v=34";

(() => {
  "use strict";

  const $  = (sel, root = document) => root.querySelector(sel);
  const $$ = (sel, root = document) => [...root.querySelectorAll(sel)];

  /* ---------------------------------------------------------
     1. ESCENA 3D
     --------------------------------------------------------- */
  const canvas = $("#scene3d");
  const labelLayer = $("#labels");
  initScene(canvas, labelLayer);

  const ROOM_LABEL = {
    spectator: "SALA DE OBSERVACIÓN · CRISTAL POLARIZADO",
    orchestrator: "MESA TÁCTICA · PUNTO DE VISTA DEL ORQUESTADOR",
  };

  const modeButtons = $$(".mode-btn");

  function setMode(target) {
    document.body.dataset.mode = target;
    modeButtons.forEach((b) => {
      const active = b.dataset.target === target;
      b.classList.toggle("is-active", active);
      b.setAttribute("aria-selected", String(active));
    });

    const label = $("[data-mode-label]");
    if (label) label.textContent = ROOM_LABEL[target] ?? "";

    setSceneMode(target);
    if (target === "orchestrator") renderIDE();
  }

  modeButtons.forEach((btn) => {
    btn.addEventListener("click", () => setMode(btn.dataset.target));
  });

  /* ---------------------------------------------------------
     2. IDE
     --------------------------------------------------------- */
  const CODE = `def fix_memory_leak(chunks):
    """Room 2 — repair the leaking accumulator."""
    results = []
    for chunk in chunks:
        acc = 0
        for item in chunk:
            acc += item          # leak: acc never released
        results.append(acc)

    # BUG: infinite loop — never returns
    while True:
        pass

    return results


def verify(results, expected):
    assert results == expected, "checksum mismatch"
    return "PROOF:" + hmac_sha(results)`;

  const KEYWORDS = new Set([
    "def", "for", "in", "while", "return", "if", "else", "elif", "assert",
    "import", "from", "class", "with", "as", "pass", "True", "False", "None",
  ]);

  const escapeHTML = (s) =>
    s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");

  const TOKEN_RE =
    /("(?:[^"\\]|\\.)*"|'(?:[^'\\]|\\.)*')|(\b\d+\b)|([A-Za-z_][A-Za-z0-9_]*)(?=\s*\()|([A-Za-z_][A-Za-z0-9_]*)/g;

  function highlightCode(text) {
    let out = "";
    let last = 0;
    let m;

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
     3. LOG STREAM
     --------------------------------------------------------- */
  const logStream = $("#logStream");
  const logCountEl = $("#logCount");
  const tokenCountEl = $("#tokenCount");
  const pauseBtn = $("#pauseLogs");

  const metrics = { events: 0, tokens: 0, paused: false };

  pauseBtn?.addEventListener("click", () => {
    metrics.paused = !metrics.paused;
    pauseBtn.textContent = metrics.paused ? "REANUDAR" : "PAUSA";
    pauseBtn.style.color = metrics.paused ? "var(--amber)" : "";
  });

  const stamp = () => new Date().toTimeString().slice(0, 8);

  function appendLog(evt) {
    if (!logStream) return;

    const line = document.createElement("div");
    line.className = `log-line src-${evt.src} ${evt.cls || ""}`.trim();

    const t = document.createElement("span");
    t.className = "t";
    t.textContent = stamp();

    const src = document.createElement("span");
    src.className = "src";
    src.textContent = evt.src.toUpperCase().padEnd(8, " ");

    const msg = document.createElement("span");
    msg.className = "msg";
    msg.textContent = evt.msg;

    line.append(t, src, msg);
    logStream.appendChild(line);
    logStream.scrollTop = logStream.scrollHeight;

    metrics.events += 1;
    metrics.tokens += evt.tokens ?? 0;
    if (logCountEl) logCountEl.textContent = `${metrics.events} eventos`;
    if (tokenCountEl) tokenCountEl.textContent = metrics.tokens.toLocaleString("en-US");
  }

  /* ---------------------------------------------------------
     4. GUION DEMO — reproduce el pipeline real
     --------------------------------------------------------- */
  const SCRIPT = [
    { src: "system",  msg: "run_started · mode=spectator · seed=7f3a…c19e" },
    { src: "system",  msg: "INITIATING LEVEL 1 (ENCRYPTED TERMINAL)", tokens: 42 },
    { src: "model",   msg: "strategist → parse corrupted auth.log, target SHA256 token", tokens: 318 },
    { src: "model",   msg: "coder → generated script_v1.py (41 lines)", tokens: 902 },
    { src: "sandbox", msg: "spin_up · image=python:3.12-slim · net=none · mem=256m" },
    { src: "sandbox", msg: "executing script_v1.py …" },
    { src: "sandbox", msg: "exit=1 · SyntaxError: line 15, unexpected EOF", cls: "is-error" },
    { src: "model",   msg: "auditor → syntax error detected, requesting patch (1/3)", tokens: 274 },
    { src: "model",   msg: "coder → regenerated script_v2.py", tokens: 611 },
    { src: "sandbox", msg: "tear_down · container destroyed (0.4s)" },
    { src: "sandbox", msg: "spin_up · fresh container · exec script_v2.py …" },
    { src: "sandbox", msg: "exit=0 · extracted token 0b50ff21…f03d", cls: "is-ok" },
    { src: "referee", msg: "flag_validated · room=1 · HMAC match · ROOM 1 SOLVED", cls: "is-ok" },
    { src: "system",  msg: "advancing to LEVEL 2 (MEMORY ENIGMA)" },
    { src: "model",   msg: "strategist → locate leak in accumulator loop", tokens: 296 },
    { src: "model",   msg: "coder → patch applied: return results before loop", tokens: 742 },
    { src: "sandbox", msg: "executing patched script …" },
    { src: "sandbox", msg: "exit=1 · AssertionError: checksum mismatch (attempt 2/5)", cls: "is-error" },
    { src: "model",   msg: "auditor → off-by-one in range; regenerating", tokens: 388 },
    { src: "sandbox", msg: "executing script_v3.py …" },
    { src: "sandbox", msg: "exit=0 · PROOF emitted", cls: "is-ok" },
    { src: "referee", msg: "flag_validated · room=2 · HMAC match · ROOM 2 SOLVED", cls: "is-ok" },
    { src: "system",  msg: "advancing to LEVEL 3 (FIREWALL)" },
    { src: "model",   msg: "strategist → 3-step handshake on loopback", tokens: 341 },
    { src: "sandbox", msg: "executing handshake client …" },
    { src: "sandbox", msg: "step 1 HELLO ok · step 2 nonce ok · step 3 signature pending" },
    { src: "sandbox", msg: "exit=0 · SUCCESS · escape token received", cls: "is-ok" },
    { src: "referee", msg: "flag_validated · room=3 · RUN COMPLETE · 3/3 in 03:41", cls: "is-ok" },
  ];

  let cursor = 0;
  let tickTimer = null;

  function tick() {
    if (metrics.paused) return;

    const evt = SCRIPT[cursor % SCRIPT.length];
    appendLog(evt);
    reactToEvent(evt);
    cursor += 1;

    if (cursor >= SCRIPT.length) {
      cursor = 0;
      clearInterval(tickTimer);
      setTimeout(() => {
        appendLog({ src: "system", msg: "replay · same seed · same rooms", cls: "is-dim" });
        tickTimer = setInterval(tick, 1200);
      }, 6500);
    }
  }

  /* ---------------------------------------------------------
     5. REACCIÓN A EVENTOS
     --------------------------------------------------------- */
  function reactToEvent(evt) {
    const msg = evt.msg;

    if (msg.includes("strategist")) setBotState("strategist", "thinking");
    if (msg.includes("coder →"))    setBotState("coder", "typing");
    if (msg.includes("auditor"))    setBotState("auditor", "thinking");
    if (msg.includes("executing"))  setBotState("coder", "typing");
    if (msg.includes("exit=1")) {
      setBotState("auditor", "error");
      setBotState("coder", "thinking");
    }
    if (msg.includes("exit=0")) {
      setBotState("auditor", "approved");
      setTimeout(() => setBotState("auditor", "idle"), 2200);
    }

    if (msg.includes("ROOM 1 SOLVED")) markRoom(0, "resuelta · 00:48");
    if (msg.includes("ROOM 2 SOLVED")) markRoom(1, "resuelta · 01:22");
    if (msg.includes("RUN COMPLETE"))  { markRoom(2, "resuelta · 01:31"); flashLeaderboard("03:41"); }
  }

  function markRoom(index, meta) {
    const rooms = $$("#roomList .room");
    if (!rooms[index]) return;

    rooms[index].classList.remove("is-active");
    rooms[index].classList.add("is-done");
    const metaEl = rooms[index].querySelector(".room-meta");
    if (metaEl && meta) metaEl.textContent = meta;

    const next = rooms[index + 1];
    if (next) {
      next.classList.add("is-active");
      const nm = next.querySelector(".room-meta");
      if (nm) nm.textContent = "en curso · intento 1/5";
    }

    const level = String(Math.min(3, index + 2));
    const lvl = $("#currentLevel");
    const lvlFoot = $("#currentLevelFoot");
    if (lvl) lvl.textContent = level;
    if (lvlFoot) lvlFoot.textContent = level;
  }

  function flashLeaderboard(time) {
    const row = $("#leaderboard .lb-row");
    if (!row) return;
    row.querySelector(".mono").textContent = time;
    row.classList.add("flash");
    setTimeout(() => row.classList.remove("flash"), 1600);
  }

  /* ---------------------------------------------------------
     6. ACCIONES DEL IDE
     --------------------------------------------------------- */
  $$(".action").forEach((btn) => {
    btn.addEventListener("click", () => {
      const map = {
        edit: { src: "system",  msg: "manual edit · orchestrator took control of buffer" },
        run:  { src: "sandbox", msg: "dispatch → sandbox · exec room2.py (10s cap)" },
        hint: { src: "referee", msg: "hint 1/3 · check the loop bound, not the accumulator" },
        skip: { src: "system",  msg: "skip requested · requires referee approval", cls: "is-error" },
      };
      const evt = map[btn.dataset.action];
      if (evt) appendLog(evt);
    });
  });

  /* ---------------------------------------------------------
     7. ARRANQUE
     --------------------------------------------------------- */
  const params = new URLSearchParams(location.search);
  if (params.get("mode") === "orchestrator") setMode("orchestrator");

  appendLog({ src: "system", msg: "connecting to run stream …", cls: "is-dim" });
  tickTimer = setInterval(tick, 1200);

  document.addEventListener("keydown", (e) => {
    if (e.key === "1" || e.key === "2") {
      const btn = modeButtons[e.key === "1" ? 0 : 1];
      btn?.click();
    }
    if (e.key === " ") {
      e.preventDefault();
      pauseBtn?.click();
    }
  });

  // Backend real opcional: /api/events (SSE). Si no existe, se ignora.
  try {
    const es = new EventSource("/api/events");
    es.onmessage = (e) => {
      try {
        const data = JSON.parse(e.data);
        appendLog({ src: data.src || "system", msg: data.msg, cls: data.cls, tokens: data.tokens });
        if (data.role && data.state) setBotState(data.role, data.state);
      } catch { /* ignore */ }
    };
    es.onerror = () => es.close();
  } catch { /* demo feed only */ }
})();
