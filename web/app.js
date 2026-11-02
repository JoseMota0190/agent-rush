/* ============================================================
   AGENT RUSH — front-end controller
   - mode switching (spectator / orchestrator)
   - live log stream (SSE if backend present, demo feed otherwise)
   - leaderboard / room status updates
   - IDE panel with syntax highlighting + line numbers
   ============================================================ */

(() => {
  "use strict";

  const $  = (sel, root = document) => root.querySelector(sel);
  const $$ = (sel, root = document) => [...root.querySelectorAll(sel)];

  /* ---------------------------------------------------------
     1. MODE SWITCH
     --------------------------------------------------------- */
  const modeButtons = $$(".mode-btn");

  function setMode(target) {
    document.body.dataset.mode = target;
    modeButtons.forEach((b) => {
      const active = b.dataset.target === target;
      b.classList.toggle("is-active", active);
      b.setAttribute("aria-selected", String(active));
    });
    if (target === "orchestrator") renderIDE();
  }

  modeButtons.forEach((btn) => {
    btn.addEventListener("click", () => setMode(btn.dataset.target));
  });

  /* ---------------------------------------------------------
     2. IDE PANEL
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

  // One-pass tokenizer: strings, numbers, keywords, calls
  const TOKEN_RE =
    /("(?:[^"\\]|\\.)*"|'(?:[^'\\]|\\.)*')|(\b\d+\b)|([A-Za-z_][A-Za-z0-9_]*)(?=\s*\()|([A-Za-z_][A-Za-z0-9_]*)/g;

  function highlightCode(text) {
    let out = "";
    let last = 0;
    let m;

    while ((m = TOKEN_RE.exec(text)) !== null) {
      out += escapeHTML(text.slice(last, m.index));

      const [raw, str, num, call, word] = m;
      if (str) {
        out += `<span class="str">${escapeHTML(str)}</span>`;
      } else if (num) {
        out += `<span class="num">${num}</span>`;
      } else if (call) {
        out += `<span class="fn">${call}</span>`;
      } else if (word && KEYWORDS.has(word)) {
        out += `<span class="kw">${word}</span>`;
      } else {
        out += escapeHTML(raw);
      }
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

  function stamp() {
    const d = new Date();
    return d.toTimeString().slice(0, 8);
  }

  /**
   * Append one log line.
   * @param {{src:string, cls?:string, msg:string, tokens?:number}} evt
   */
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
     4. DEMO SCRIPT — mirrors the real run pipeline
     --------------------------------------------------------- */
  const SCRIPT = [
    { src: "system",  msg: "run_started · mode=spectator · seed=7f3a…c19e", tokens: 0 },
    { src: "system",  msg: "INITIATING LEVEL 1 (ENCRYPTED TERMINAL)", tokens: 42 },
    { src: "model",   msg: "strategist → parse corrupted auth.log with regex, target SHA256 token", tokens: 318 },
    { src: "model",   msg: "coder → generated script_v1.py (41 lines)", tokens: 902 },
    { src: "sandbox", msg: "spin_up · image=python:3.12-slim · net=none · mem=256m", tokens: 0 },
    { src: "sandbox", msg: "executing script_v1.py …", tokens: 0 },
    { src: "sandbox", msg: "exit=1 · SyntaxError: line 15, unexpected EOF", cls: "is-error", tokens: 0 },
    { src: "model",   msg: "auditor → syntax error detected, requesting patch (1/3)", tokens: 274 },
    { src: "model",   msg: "coder → regenerated script_v2.py", tokens: 611 },
    { src: "sandbox", msg: "tear_down · container destroyed (0.4s)", tokens: 0 },
    { src: "sandbox", msg: "spin_up · fresh container · exec script_v2.py …", tokens: 0 },
    { src: "sandbox", msg: "exit=0 · extracted token 0b50ff21…f03d", cls: "is-ok", tokens: 0 },
    { src: "referee", msg: "flag_validated · room=1 · HMAC match · ROOM 1 SOLVED", cls: "is-ok", tokens: 0 },
    { src: "system",  msg: "advancing to LEVEL 2 (MEMORY ENIGMA)", tokens: 0 },
    { src: "model",   msg: "strategist → locate leak in accumulator loop, remove infinite while", tokens: 296 },
    { src: "model",   msg: "coder → patch applied: return results before loop", tokens: 742 },
    { src: "sandbox", msg: "executing patched script …", tokens: 0 },
    { src: "sandbox", msg: "exit=1 · AssertionError: checksum mismatch (attempt 2/5)", cls: "is-error", tokens: 0 },
    { src: "model",   msg: "auditor → off-by-one in range; regenerating", tokens: 388 },
    { src: "sandbox", msg: "executing script_v3.py …", tokens: 0 },
    { src: "sandbox", msg: "exit=0 · PROOF emitted", cls: "is-ok", tokens: 0 },
    { src: "referee", msg: "flag_validated · room=2 · HMAC match · ROOM 2 SOLVED", cls: "is-ok", tokens: 0 },
    { src: "system",  msg: "advancing to LEVEL 3 (FIREWALL)", tokens: 0 },
    { src: "model",   msg: "strategist → 3-step handshake on loopback, derive nonce", tokens: 341 },
    { src: "sandbox", msg: "executing handshake client …", tokens: 0 },
    { src: "sandbox", msg: "step 1 HELLO ok · step 2 nonce ok · step 3 signature pending", tokens: 0 },
    { src: "sandbox", msg: "exit=0 · SUCCESS · escape token received", cls: "is-ok", tokens: 0 },
    { src: "referee", msg: "flag_validated · room=3 · RUN COMPLETE · 3/3 in 03:41", cls: "is-ok", tokens: 0 },
  ];

  let cursor = 0;
  let tickTimer = null;
  let restartTimer = null;

  function tick() {
    if (metrics.paused) return;

    const evt = SCRIPT[cursor % SCRIPT.length];
    appendLog(evt);
    reactToEvent(evt);
    cursor += 1;

    if (cursor >= SCRIPT.length) {
      cursor = 0;
      clearInterval(tickTimer);
      restartTimer = setTimeout(() => {
        appendLog({ src: "system", msg: "replay · same seed · same rooms", cls: "is-dim" });
        tickTimer = setInterval(tick, 1100);
      }, 6000);
    }
  }

  function reactToEvent(evt) {
    const msg = evt.msg;

    // bot states
    const setBot = (role, state, label) => {
      const bot = $(`.bot[data-role="${role}"]`);
      const badge = bot?.querySelector(".bot-state");
      if (!badge) return;
      badge.dataset.state = state;
      badge.textContent = label;
    };

    if (msg.includes("strategist")) setBot("strategist", "thinking", "THINKING");
    if (msg.includes("coder →"))    setBot("coder", "typing", "TYPING");
    if (msg.includes("auditor"))    setBot("auditor", "thinking", "VERIFYING");
    if (msg.includes("exit=1")) {
      setBot("auditor", "error", "ERROR FOUND");
      setBot("coder", "thinking", "PATCHING");
    }
    if (msg.includes("exit=0")) {
      setBot("auditor", "idle", "APPROVED");
      setBot("coder", "typing", "TYPING");
    }

    // room status (orchestrator view)
    if (msg.includes("ROOM 1 SOLVED")) markRoom(0, "is-done", "resuelta · 00:48");
    if (msg.includes("ROOM 2 SOLVED")) markRoom(1, "is-done", "resuelta · 01:22");
    if (msg.includes("RUN COMPLETE"))  markRoom(2, "is-done", "resuelta · 01:31");

    // leaderboard flash on completion
    if (msg.includes("RUN COMPLETE")) flashLeaderboard("03:41");
  }

  function markRoom(index, cls, meta) {
    const rooms = $$("#roomList .room");
    if (!rooms[index]) return;
    rooms[index].classList.remove("is-active");
    rooms[index].classList.add(cls);
    const metaEl = rooms[index].querySelector(".room-meta");
    if (metaEl && meta) metaEl.textContent = meta;

    // promote next room
    const next = rooms[index + 1];
    if (next) {
      next.classList.add("is-active");
      const nm = next.querySelector(".room-meta");
      if (nm) nm.textContent = "en curso · intento 1/5";
    }
    const lvl = $("#currentLevel");
    if (lvl) lvl.textContent = String(Math.min(3, index + 2));
  }

  function flashLeaderboard(time) {
    const row = $("#leaderboard .lb-row");
    if (!row) return;
    row.querySelector(".mono").textContent = time;
    row.classList.add("flash");
    setTimeout(() => row.classList.remove("flash"), 1600);
  }

  /* ---------------------------------------------------------
     5. IDE ACTION BUTTONS
     --------------------------------------------------------- */
  $$(".action").forEach((btn) => {
    btn.addEventListener("click", () => {
      const action = btn.dataset.action;
      const map = {
        edit: { src: "system", msg: "manual edit · orchestrator took control of buffer" },
        run:  { src: "sandbox", msg: "dispatch → sandbox · exec room2.py (10s cap)" },
        hint: { src: "referee", msg: "hint ladder 1/3 · check the loop bound, not the accumulator" },
        skip: { src: "system", msg: "skip requested · requires referee approval", cls: "is-error" },
      };
      const evt = map[action];
      if (evt) appendLog(evt);
    });
  });

  /* ---------------------------------------------------------
     6. START
     --------------------------------------------------------- */
  // deep link: ?mode=orchestrator (after renderIDE is available)
  const params = new URLSearchParams(location.search);
  if (params.get("mode") === "orchestrator") setMode("orchestrator");

  tickTimer = setInterval(tick, 1100);
  appendLog({ src: "system", msg: "connecting to run stream …", cls: "is-dim" });

  // keyboard shortcuts: 1 = spectator, 2 = orchestrator
  document.addEventListener("keydown", (e) => {
    if (e.key === "1" || e.key === "2") {
      const btn = $$(".mode-btn")[e.key === "1" ? 0 : 1];
      btn?.click();
    }
    if (e.key === " ") {
      e.preventDefault();
      pauseBtn?.click();
    }
  });

  // Optional real backend: GET /api/events (SSE). Silently ignored if absent.
  try {
    const es = new EventSource("/api/events");
    es.onmessage = (e) => {
      try {
        const data = JSON.parse(e.data);
        appendLog({ src: data.src || "system", msg: data.msg, cls: data.cls, tokens: data.tokens });
      } catch { /* ignore malformed */ }
    };
    es.onerror = () => es.close();
  } catch { /* no backend — demo feed only */ }
})();
