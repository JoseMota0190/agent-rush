/* ============================================================
   AGENT RUSH — i18n ES/EN (sin dependencias, sin build)
   Default: inglés. Persistencia: sessionStorage("agentrush.lang").
   Override por URL: ?lang=es | ?lang=en
   Uso:
     - HTML: data-i18n (textContent), data-i18n-title, data-i18n-aria,
       data-i18n-alt, data-i18n-placeholder
     - JS:   window.AgentRushI18n.t("key", { var: "x" })
     - Evento: document.addEventListener("agentrush:langchange", ...)
   ============================================================ */
(function () {
  "use strict";

  const DEFAULT_LANG = "en";
  const SUPPORTED = ["es", "en"];
  const STORAGE_KEY = "agentrush.lang";

  const DICT = {
    es: {
      "meta.title.landing": "AGENT RUSH — Escape Room de IA",
      "meta.title.game": "AGENT RUSH — Escape Room de IA",

      "lang.label": "Idioma",
      "lang.es": "ES",
      "lang.en": "EN",

      "nav.home": "Inicio",
      "nav.models": "Modelos",
      "nav.how": "Cómo funciona",
      "nav.modes": "Modos",
      "nav.leaderboards": "Leaderboards",

      "hero.tagline": "ESCAPE ROOM DE IA DETERMINISTA",
      "hero.subtitle":
        "Un escape room donde 3 agentes de IA (Strategist, Coder, Auditor) escriben código, lo ejecutan en un sandbox aislado y escapan de 3 salas validadas por un árbitro determinista HMAC.",
      "hero.cta": "ENTRAR AL JUEGO",
      "hero.kicker": "VULTR AGENT RUSH HACKATHON",
      "hero.subtitleLine": "TRES AGENTES. UNA MISIÓN. CERO CONFIANZA.",
      "hero.desc":
        "Un escape room comandado por tres agentes de IA. Planifican, escriben código, lo ejecutan dentro de un sandbox aislado y escapan de tres salas validadas por un árbitro determinista.",
      "hero.how": "CÓMO FUNCIONA",

      "how.title": "CÓMO FUNCIONA",
      "how.kicker": "EL EQUIPO",
      "how.lead":
        "Tres agentes especializados, una misión compartida. Cada uno tiene un trabajo y el árbitro comprueba el resultado.",
      "how.card1.title": "STRATEGIST",
      "how.card1.desc":
        "Analiza los desafíos y traza la estrategia óptima para escapar, identificando patrones criptográficos y obstáculos.",
      "how.card2.title": "CODER",
      "how.card2.desc":
        "Escribe código en un sandbox efímero y aislado, ejecutándolo para superar cada sala del escape room.",
      "how.card3.title": "AUDITOR",
      "how.card3.desc":
        "Refina el código, implementa parches y verifica con el referee determinista para asegurar el escape seguro.",

      "modes.title": "DOS MODOS DE JUEGO",
      "modes.kicker": "ELEGÍ TU LUGAR",
      "modes.lead":
        "Mirá a la tripulación trabajar sola, o entrá y orquestá el escape.",
      "modes.spectator.title": "MODO ESPECTADOR",
      "modes.spectator.subtitle": "IA 100% autónoma, sin intervención humana",
      "modes.spectator.cta": "VER MODO ESPECTADOR",
      "modes.spectator.point1": "Los agentes toman todas las decisiones por su cuenta.",
      "modes.spectator.point2": "Seguís la misión a través de la sala y el log en vivo.",
      "modes.spectator.point3": "Los resultados van directo al leaderboard.",
      "modes.orchestrator.title": "MODO ORQUESTRADOR",
      "modes.orchestrator.subtitle":
        "Human-in-the-loop, edita el código antes de enviarlo al sandbox",
      "modes.orchestrator.cta": "JUGAR COMO ORQUESTRADOR",
      "modes.orchestrator.point1": "Inspeccioná y editá el script del Coder antes de ejecutarlo.",
      "modes.orchestrator.point2": "Enviá el código al sandbox, pedí una pista o salteá una tarea.",
      "modes.orchestrator.point3": "Coordiná a la tripulación y tomá la decisión final.",

      "models.title": "MODELOS VULTR",
      "models.kicker": "POTENCIADO POR VULTR",
      "models.catalog.title": "Vultr Serverless Inference",
      "models.catalog.subtitle": "Todos los modelos de chat disponibles en Vultr. Los asignarás a los tres agentes justo antes de entrar a la sala.",
      "models.catalog.loading": "Cargando modelos…",
      "models.catalog.error": "No se pudo cargar el catálogo de modelos de Vultr.",
      "models.catalog.count": "{n} modelos",
      "models.catalog.hint": "Catálogo informativo. La selección de modelos se hace al iniciar una partida.",
      "models.catalog.chat": "CHAT",
      "models.preset": "Preset",
      "models.placeholder": "— elegir —",
      "models.strategist": "Strategist",
      "models.coder": "Coder",
      "models.auditor": "Auditor",
      "models.save": "GUARDAR",
      "models.reload": "RECARGAR MODELOS",
      "models.note": "Las 3 IAs comparten 100,000 tokens de energía por partida.",

      "leaderboards.title": "LEADERBOARDS",
      "leaderboards.kicker": "SOLO PARTIDAS REALES",
      "leaderboards.lead":
        "Cada entrada es una partida validada. Sin datos demo, sin escapes simulados.",
      "lb.mode.spectator": "MODO ESPECTADOR",
      "lb.mode.orchestrator": "MODO ORQUESTRADOR",
      "lb.badge.waiting": "EN ESPERA",
      "lb.badge.live": "LIVE",
      "lb.headers.rank": "#",
      "lb.headers.squad": "ESCUADRÓN",
      "lb.headers.time": "TIEMPO",
      "lb.headers.tokens": "TOKENS",
      "lb.headers.status": "ESTADO",
      "lb.status.ok": "OK",
      "lb.status.error": "FALLÓ",
      "lb.empty.title": "AÚN NO HAY PARTIDAS VÁLIDAS",
      "lb.empty.text":
        "El leaderboard se llenará con partidas reales verificadas por el árbitro. No mostramos datos simulados.",
      "lb.error.title": "ERROR",
      "lb.error.load": "No se pudo cargar el leaderboard",

      "avatar.alt.strategist": "Avatar del agente Strategist",
      "avatar.alt.coder": "Avatar del agente Coder",
      "avatar.alt.auditor": "Avatar del agente Auditor",

      "footer.text": "AGENT RUSH · Vultr Agent Rush Hackathon",
      "footer.game": "Jugar",
      "footer.home": "Inicio",
      "footer.models": "Modelos",
      "footer.leaderboards": "Leaderboards",
      "footer.sandbox": "Sandbox",
      "meta.title.sandbox": "AGENT RUSH — Contención del Sandbox",
      "sandbox.title": "SANDBOX · CONTENCIÓN",
      "sandbox.subtitle": "Cada intento se ejecuta en el mismo contenedor efímero y endurecido que usa el código de los agentes. Nada llega al host.",
      "sandbox.run": "EJECUTAR PRUEBA DE CONTENCIÓN",
      "sandbox.running": "EJECUTANDO PRUEBA…",
      "sandbox.blocked": "BLOQUEADO",
      "sandbox.allowed": "PERMITIDO",
      "sandbox.error": "No se pudo ejecutar la prueba",
      "sandbox.note": "Root read-only · sin red · sin secretos del host · límite de pids",
      "sandbox.back": "← VOLVER AL JUEGO",

      "config.status.loading": "Cargando modelos de Vultr...",
      "config.status.ready": "Listo · {n} modelos disponibles",
      "config.status.presetApplied": "Preset «{name}» aplicado (sin guardar)",
      "config.status.saved": "Guardado ✓",
      "config.status.error": "Error: {msg}",

      "game.home": "INICIO",
      "game.modeSwitch.aria": "Modo de juego",
      "game.mode.spectator": "MODO ESPECTADOR",
      "game.mode.orchestrator": "MODO ORQUESTRADOR",
      "game.models": "⚙ MODELOS",
      "game.energy.title": "Energía compartida de la partida",
      "game.energy.label": "⚡ ENERGÍA",
      "game.energy.dead": "DESCALIFICADO",
      "game.hud.sandbox": "SANDBOX ACTIVE",
      "game.roomLabel.spectator": "SALA DE OBSERVACIÓN · CRISTAL POLARIZADO",
      "game.roomLabel.orchestrator": "MESA TÁCTICA · PUNTO DE VISTA DEL ORQUESTADOR",
      "game.footer.spectator": "TRANSMISIÓN EN VIVO · SIN INTERVENCIÓN HUMANA",
      "game.footer.orchestrator": "CONTROL MANUAL · PUEDES EDITAR ANTES DE EJECUTAR",
      "game.logs.title": "LOGS DE PARTIDA",
      "game.logs.tag.spectator": "[ESPECTADOR]",
      "game.logs.tag.orchestrator": "[ORQUESTRADOR]",
      "game.pause": "PAUSA",
      "game.resume": "REANUDAR",
      "game.events": "{n} eventos",
      "game.tokens": "TOKENS",
      "game.status.title": "STATUS DE PARTIDA",
      "game.level": "LEVEL",
      "game.room.1": "ROOM 1: THE LOGS",
      "game.room.2": "ROOM 2: MEMORY LEAK",
      "game.room.3": "ROOM 3: FIREWALL",
      "game.room.resolved": "resuelta",
      "game.room.inProgress": "en curso",
      "game.room.attempt": "intento",
      "game.room.locked": "bloqueada",
      "game.room.meta.resolved": "{status} · {time}",
      "game.room.meta.inProgress": "{status} · intento {attempt}/{max}",
      "game.currentLevel": "CURRENT LEVEL",
      "game.ide.title": "PANEL DE CONTROL / IDE",
      "game.ide.tag": "[ORQUESTRADOR]",
      "game.ide.badge": "room1.py",
      "game.ide.edit": "EDIT CODE",
      "game.ide.run": "SEND TO SANDBOX",
      "game.ide.hint": "REQUEST HINT",
      "game.ide.skip": "SKIP TASK",
      "game.sandbox.label": "sandbox:",
      "game.sandbox.ephemeral": "efímero",
      "game.sandbox.net": "net:",
      "game.sandbox.none": "none",
      "game.sandbox.mem": "mem:",
      "game.sandbox.memValue": "256m",
      "game.sandbox.timeout": "timeout:",
      "game.sandbox.timeoutValue": "10s",
      "game.log.disqualified": "EQUIPO DESCALIFICADO — SIN ENERGÍA",
      "game.exit.title": "Salir de la sala",
      "game.exit.confirm": "¿Salir de la sala? La partida actual se abortará.",
      "game.start.title": "¿LISTOS PARA ESCAPAR?",
      "game.start.cta": "HAZ CLICK PARA INICIAR",
      "game.start.hint": "Hacé click para recibir la consigna. Después los agentes podrán razonar y comunicarse.",
      "game.start.engine": "El motor de partida todavía no está conectado. La consigna está lista; los agentes esperan el backend.",
      "game.start.connecting": "INICIANDO PARTIDA…",
      "game.start.running": "PARTIDA EN CURSO · logs en vivo abajo",
      "game.start.completedShort": "PARTIDA COMPLETA",
      "game.start.failedShort": "PARTIDA FALLIDA",
      "game.start.completed": "PARTIDA COMPLETA · {rooms}/3 salas resueltas",
      "game.start.failed": "PARTIDA FALLIDA · revisá los logs",
      "game.start.connectionLost": "Se perdió la conexión con la partida.",
      "game.start.error": "No se pudo iniciar la partida",
      "game.challenge.roomKicker": "DESAFÍO · SALA {n}",
      "game.challenge.kicker": "DESAFÍO · SALA 1",
      "game.challenge.title": "LOS LOGS",
      "game.challenge.desc": "La terminal de acceso está bloqueada. Analizá el auth.log corrupto, recuperá el token y abrí la puerta.",
      "game.challenge.goalLabel": "OBJETIVO",
      "game.challenge.goal": "Extraer el hash válido de los logs.",
      "game.logs.title": "AGENT LOGS",
      "game.logs.live": "LIVE",
      "game.logs.empty": "Esperando el primer evento…",
      "game.logs.count": "{n} eventos",
      "game.logs.codeSummary": "Ver código",
      "game.logs.execSummary": "Ver stdout / stderr",
      "game.logs.exit": "exit {code}",
      "game.logs.filterAria": "Filtrar eventos del log",
      "game.mission.ready": "READY TO ESCAPE",
      "game.mission.active": "MISSION ACTIVE",
      "game.mission.audit": "AUDIT IN PROGRESS",
      "game.mission.unlocked": "ESCAPE UNLOCKED",
      "game.mission.failed": "RUN FAILED",
      "game.mission.aborted": "RUN ABORTED",
      "game.mission.disqualified": "DISQUALIFIED",
      "game.filters.all": "ALL",
      "game.filters.chat": "CHAT",
      "game.filters.code": "CODE",
      "game.filters.execution": "EXECUTION",
      "game.filters.audit": "AUDIT",
      "game.events.type.chat": "CHAT",
      "game.events.type.code": "CODE",
      "game.events.type.execution": "EXECUTION",
      "game.events.type.audit": "AUDIT",
      "game.tabs.room": "ROOM",
      "game.tabs.logs": "AGENT LOGS",
      "wizard.mode.spectator.desc":
        "Los tres agentes toman todas las decisiones. Vos observás la misión y seguís el log en vivo.",
      "wizard.mode.orchestrator.desc":
        "Podés inspeccionar y editar el código, enviarlo al sandbox, pedir una pista o saltear una tarea.",
      "wizard.agent.strategist.desc": "Planifica la solución y coordina la misión.",
      "wizard.agent.coder.desc": "Escribe y ejecuta código dentro del sandbox.",
      "wizard.agent.auditor.desc": "Revisa el código y valida los resultados.",
      "wizard.model": "Modelo",
      "wizard.provider": "Vultr Serverless Inference",
      "wizard.title.mode": "Elegí tu modo",
      "wizard.title.models": "Elegí tus modelos",
      "wizard.step": "Paso {n} de 2",
      "wizard.step.modeKicker": "MODO",
      "wizard.mode.hint": "¿Cómo querés jugar esta partida?",
      "wizard.modeChip": "Modo: {mode}",
      "wizard.back": "Atrás",
      "wizard.enter": "Entrar a la sala",
      "wizard.close": "Cerrar",
      "wizard.modeWord": "MODO",
      "wizard.required": "Elegí un modelo para los tres agentes.",
      "wizard.error": "No se pudieron cargar los modelos. Reintentá.",
      "wizard.loading": "Cargando modelos…",
    },

    en: {
      "meta.title.landing": "AGENT RUSH — AI Escape Room",
      "meta.title.game": "AGENT RUSH — AI Escape Room",

      "lang.label": "Language",
      "lang.es": "ES",
      "lang.en": "EN",

      "nav.home": "Home",
      "nav.models": "Models",
      "nav.how": "How it works",
      "nav.modes": "Modes",
      "nav.leaderboards": "Leaderboards",

      "hero.tagline": "DETERMINISTIC AI ESCAPE ROOM",
      "hero.subtitle":
        "An escape room where 3 AI agents (Strategist, Coder, Auditor) write code, run it in an isolated sandbox, and break out of 3 rooms validated by an HMAC referee.",
      "hero.cta": "ENTER THE GAME",
      "hero.kicker": "VULTR AGENT RUSH HACKATHON",
      "hero.subtitleLine": "THREE AGENTS. ONE MISSION. ZERO TRUST.",
      "hero.desc":
        "An escape room run by three AI agents. They plan, write code, execute it inside an isolated sandbox and break out of three rooms validated by a deterministic referee.",
      "hero.how": "HOW IT WORKS",

      "how.title": "HOW IT WORKS",
      "how.kicker": "THE CREW",
      "how.lead":
        "Three specialized agents, one shared mission. Each one has a job, and the referee checks the result.",
      "how.card1.title": "STRATEGIST",
      "how.card1.desc":
        "Analyzes each challenge and plots the optimal escape strategy, spotting cryptographic patterns and obstacles.",
      "how.card2.title": "CODER",
      "how.card2.desc":
        "Writes code in an ephemeral, isolated sandbox and runs it to clear each room of the escape room.",
      "how.card3.title": "AUDITOR",
      "how.card3.desc":
        "Refines the code, applies patches and verifies it with the deterministic referee to guarantee a safe escape.",

      "modes.title": "TWO GAME MODES",
      "modes.kicker": "CHOOSE YOUR SEAT",
      "modes.lead":
        "Watch the crew work alone, or step in and orchestrate the escape.",
      "modes.spectator.title": "SPECTATOR MODE",
      "modes.spectator.subtitle": "100% autonomous AI, no human intervention",
      "modes.spectator.cta": "WATCH SPECTATOR MODE",
      "modes.spectator.point1": "The agents make every decision on their own.",
      "modes.spectator.point2": "You watch the mission through the room and the live log.",
      "modes.spectator.point3": "Results go straight to the leaderboard.",
      "modes.orchestrator.title": "ORCHESTRATOR MODE",
      "modes.orchestrator.subtitle":
        "Human-in-the-loop: edit the code before it reaches the sandbox",
      "modes.orchestrator.cta": "PLAY AS ORCHESTRATOR",
      "modes.orchestrator.point1": "Inspect and edit the Coder's script before execution.",
      "modes.orchestrator.point2": "Send it to the sandbox, request a hint or skip a task.",
      "modes.orchestrator.point3": "Coordinate the crew and own the final call.",

      "models.title": "VULTR MODELS",
      "models.kicker": "POWERED BY VULTR",
      "models.catalog.title": "Vultr Serverless Inference",
      "models.catalog.subtitle": "All chat models available through Vultr. You will assign them to the three agents right before entering the room.",
      "models.catalog.loading": "Loading models…",
      "models.catalog.error": "Could not load the Vultr model catalog.",
      "models.catalog.count": "{n} models",
      "models.catalog.hint": "Read-only catalog. Model selection happens when you start a run.",
      "models.catalog.chat": "CHAT",
      "models.preset": "Preset",
      "models.placeholder": "— select —",
      "models.strategist": "Strategist",
      "models.coder": "Coder",
      "models.auditor": "Auditor",
      "models.save": "SAVE",
      "models.reload": "RELOAD MODELS",
      "models.note": "All 3 AIs share 100,000 tokens of energy per run.",

      "leaderboards.title": "LEADERBOARDS",
      "leaderboards.kicker": "REAL RUNS ONLY",
      "leaderboards.lead":
        "Every entry is a validated run. No demo data, no simulated escapes.",
      "lb.mode.spectator": "SPECTATOR MODE",
      "lb.mode.orchestrator": "ORCHESTRATOR MODE",
      "lb.badge.waiting": "WAITING",
      "lb.badge.live": "LIVE",
      "lb.headers.rank": "#",
      "lb.headers.squad": "SQUAD",
      "lb.headers.time": "TIME",
      "lb.headers.tokens": "TOKENS",
      "lb.headers.status": "STATUS",
      "lb.status.ok": "OK",
      "lb.status.error": "FAILED",
      "lb.empty.title": "NO VALID RUNS YET",
      "lb.empty.text":
        "The leaderboard will fill with real, referee-verified runs. We do not show simulated data.",
      "lb.error.title": "ERROR",
      "lb.error.load": "Could not load the leaderboard",

      "avatar.alt.strategist": "Strategist agent avatar",
      "avatar.alt.coder": "Coder agent avatar",
      "avatar.alt.auditor": "Auditor agent avatar",

      "footer.text": "AGENT RUSH · Vultr Agent Rush Hackathon",
      "footer.game": "Play",
      "footer.home": "Home",
      "footer.models": "Models",
      "footer.leaderboards": "Leaderboards",
      "footer.sandbox": "Sandbox",
      "meta.title.sandbox": "AGENT RUSH — Sandbox Containment",
      "sandbox.title": "SANDBOX · CONTAINMENT",
      "sandbox.subtitle": "Every attempt below runs in the same hardened, ephemeral container used for agent code. Nothing reaches the host.",
      "sandbox.run": "RUN CONTAINMENT PROBE",
      "sandbox.running": "RUNNING PROBE…",
      "sandbox.blocked": "BLOCKED",
      "sandbox.allowed": "ALLOWED",
      "sandbox.error": "Could not run the probe",
      "sandbox.note": "Read-only root · no network · no host secrets · pids cap",
      "sandbox.back": "← BACK TO GAME",

      "config.status.loading": "Loading Vultr models...",
      "config.status.ready": "Ready · {n} models available",
      "config.status.presetApplied": "Preset “{name}” applied (not saved)",
      "config.status.saved": "Saved ✓",
      "config.status.error": "Error: {msg}",

      "game.home": "HOME",
      "game.modeSwitch.aria": "Game mode",
      "game.mode.spectator": "SPECTATOR MODE",
      "game.mode.orchestrator": "ORCHESTRATOR MODE",
      "game.models": "⚙ MODELS",
      "game.energy.title": "Shared energy for this run",
      "game.energy.label": "⚡ ENERGY",
      "game.energy.dead": "DISQUALIFIED",
      "game.hud.sandbox": "SANDBOX ACTIVE",
      "game.roomLabel.spectator": "SPECTATOR ROOM · POLARIZED GLASS",
      "game.roomLabel.orchestrator": "TACTICAL DESK · ORCHESTRATOR VIEWPOINT",
      "game.footer.spectator": "LIVESTREAM · NO HUMAN INTERVENTION",
      "game.footer.orchestrator": "MANUAL CONTROL · EDIT BEFORE RUNNING",
      "game.logs.title": "RUN LOGS",
      "game.logs.tag.spectator": "[SPECTATOR]",
      "game.logs.tag.orchestrator": "[ORCHESTRATOR]",
      "game.pause": "PAUSE",
      "game.resume": "RESUME",
      "game.events": "{n} events",
      "game.tokens": "TOKENS",
      "game.status.title": "RUN STATUS",
      "game.level": "LEVEL",
      "game.room.1": "ROOM 1: THE LOGS",
      "game.room.2": "ROOM 2: MEMORY LEAK",
      "game.room.3": "ROOM 3: FIREWALL",
      "game.room.resolved": "solved",
      "game.room.inProgress": "in progress",
      "game.room.attempt": "attempt",
      "game.room.locked": "locked",
      "game.room.meta.resolved": "{status} · {time}",
      "game.room.meta.inProgress": "{status} · attempt {attempt}/{max}",
      "game.currentLevel": "CURRENT LEVEL",
      "game.ide.title": "CONTROL PANEL / IDE",
      "game.ide.tag": "[ORCHESTRATOR]",
      "game.ide.badge": "room1.py",
      "game.ide.edit": "EDIT CODE",
      "game.ide.run": "SEND TO SANDBOX",
      "game.ide.hint": "REQUEST HINT",
      "game.ide.skip": "SKIP TASK",
      "game.sandbox.label": "sandbox:",
      "game.sandbox.ephemeral": "ephemeral",
      "game.sandbox.net": "net:",
      "game.sandbox.none": "none",
      "game.sandbox.mem": "mem:",
      "game.sandbox.memValue": "256m",
      "game.sandbox.timeout": "timeout:",
      "game.sandbox.timeoutValue": "10s",
      "game.log.disqualified": "TEAM DISQUALIFIED — OUT OF ENERGY",
      "game.exit.title": "Exit room",
      "game.exit.confirm": "Leave the room? The current run will be aborted.",
      "game.start.title": "READY TO ESCAPE?",
      "game.start.cta": "CLICK TO START",
      "game.start.hint": "Press start to receive the challenge. The agents will then begin to reason and communicate.",
      "game.start.engine": "Run engine not connected yet. The challenge is ready; the agents are waiting for the backend.",
      "game.start.connecting": "STARTING RUN…",
      "game.start.running": "RUN IN PROGRESS · live logs below",
      "game.start.completedShort": "RUN COMPLETE",
      "game.start.failedShort": "RUN FAILED",
      "game.start.completed": "RUN COMPLETE · {rooms}/3 rooms solved",
      "game.start.failed": "RUN FAILED · check the logs",
      "game.start.connectionLost": "Connection to the run was lost.",
      "game.start.error": "Could not start the run",
      "game.challenge.roomKicker": "CHALLENGE · ROOM {n}",
      "game.challenge.kicker": "CHALLENGE · ROOM 1",
      "game.challenge.title": "THE LOGS",
      "game.challenge.desc": "The access terminal is locked. Parse the corrupted auth.log, recover the token and open the door.",
      "game.challenge.goalLabel": "OBJECTIVE",
      "game.challenge.goal": "Extract the valid hash from the logs.",
      "game.logs.title": "AGENT LOGS",
      "game.logs.live": "LIVE",
      "game.logs.empty": "Waiting for the first event…",
      "game.logs.count": "{n} events",
      "game.logs.codeSummary": "View code",
      "game.logs.execSummary": "View stdout / stderr",
      "game.logs.exit": "exit {code}",
      "game.logs.filterAria": "Filter log events",
      "game.mission.ready": "READY TO ESCAPE",
      "game.mission.active": "MISSION ACTIVE",
      "game.mission.audit": "AUDIT IN PROGRESS",
      "game.mission.unlocked": "ESCAPE UNLOCKED",
      "game.mission.failed": "RUN FAILED",
      "game.mission.aborted": "RUN ABORTED",
      "game.mission.disqualified": "DISQUALIFIED",
      "game.filters.all": "ALL",
      "game.filters.chat": "CHAT",
      "game.filters.code": "CODE",
      "game.filters.execution": "EXECUTION",
      "game.filters.audit": "AUDIT",
      "game.events.type.chat": "CHAT",
      "game.events.type.code": "CODE",
      "game.events.type.execution": "EXECUTION",
      "game.events.type.audit": "AUDIT",
      "game.tabs.room": "ROOM",
      "game.tabs.logs": "AGENT LOGS",
      "wizard.mode.spectator.desc":
        "The three agents take every decision. You watch the mission and follow the live log.",
      "wizard.mode.orchestrator.desc":
        "You can inspect and edit the code, send it to the sandbox, request a hint or skip a task.",
      "wizard.agent.strategist.desc": "Plans the solution and coordinates the mission.",
      "wizard.agent.coder.desc": "Writes and executes code inside the sandbox.",
      "wizard.agent.auditor.desc": "Reviews the code and validates the results.",
      "wizard.model": "Model",
      "wizard.provider": "Vultr Serverless Inference",
      "wizard.title.mode": "Choose your mode",
      "wizard.title.models": "Choose your models",
      "wizard.step": "Step {n} of 2",
      "wizard.step.modeKicker": "MODE",
      "wizard.mode.hint": "How do you want to play this run?",
      "wizard.modeChip": "Mode: {mode}",
      "wizard.back": "Back",
      "wizard.enter": "Enter the escape room",
      "wizard.close": "Close",
      "wizard.modeWord": "MODE",
      "wizard.required": "Select a model for all three agents.",
      "wizard.error": "Could not load models. Please try again.",
      "wizard.loading": "Loading models…",
    },
  };

  let current = DEFAULT_LANG;

  function readLang() {
    try {
      // Remove old localStorage key for migration
      window.localStorage.removeItem(STORAGE_KEY);
      const param = new URLSearchParams(window.location.search).get("lang");
      if (SUPPORTED.includes(param)) {
        // Un deep link ?lang=... se mantiene durante la sesión/navegación
        window.sessionStorage.setItem(STORAGE_KEY, param);
        return param;
      }
      const stored = window.sessionStorage.getItem(STORAGE_KEY);
      if (SUPPORTED.includes(stored)) return stored;
    } catch (_) {
      /* sessionStorage puede fallar en modo privado */
    }
    return DEFAULT_LANG;
  }

  function t(key, vars) {
    const table = DICT[current] || DICT[DEFAULT_LANG];
    let text = table[key];
    if (text == null) text = DICT[DEFAULT_LANG][key];
    if (text == null) return key;
    if (vars) {
      text = text.replace(/\{(\w+)\}/g, (match, name) =>
        vars[name] != null ? String(vars[name]) : match
      );
    }
    return text;
  }

  function apply(root) {
    const scope = root || document;

    scope.querySelectorAll("[data-i18n]").forEach((el) => {
      el.textContent = t(el.getAttribute("data-i18n"));
    });

    const attrMap = {
      "data-i18n-title": "title",
      "data-i18n-aria": "aria-label",
      "data-i18n-alt": "alt",
      "data-i18n-placeholder": "placeholder",
    };

    Object.keys(attrMap).forEach((dataAttr) => {
      scope.querySelectorAll("[" + dataAttr + "]").forEach((el) => {
        el.setAttribute(attrMap[dataAttr], t(el.getAttribute(dataAttr)));
      });
    });

    const page = document.body && document.body.dataset.page;
    if (page) document.title = t("meta.title." + page);
  }

  function mountToggle(container) {
    if (!container) return;
    container.innerHTML = "";

    const wrap = document.createElement("div");
    wrap.className = "lang-switch";
    wrap.setAttribute("role", "group");
    wrap.setAttribute("aria-label", t("lang.label"));

    SUPPORTED.forEach((code) => {
      const btn = document.createElement("button");
      const active = code === current;
      btn.type = "button";
      btn.className = "lang-btn" + (active ? " is-active" : "");
      btn.dataset.lang = code;
      btn.textContent = t("lang." + code);
      btn.setAttribute("aria-pressed", String(active));
      btn.addEventListener("click", () => setLang(code));
      wrap.appendChild(btn);
    });

    container.appendChild(wrap);
  }

  function refreshToggles() {
    document.querySelectorAll(".topbar-lang-switch").forEach(mountToggle);
  }

  function setLang(lang) {
    if (!SUPPORTED.includes(lang) || lang === current) {
      refreshToggles();
      return;
    }
    current = lang;
    try {
      window.sessionStorage.setItem(STORAGE_KEY, lang);
    } catch (_) {
      /* ignore */
    }
    document.documentElement.lang = lang;
    apply();
    refreshToggles();
    document.dispatchEvent(
      new CustomEvent("agentrush:langchange", { detail: { lang } })
    );
  }

  function getLang() {
    return current;
  }

  current = readLang();

  function boot() {
    document.documentElement.lang = current;
    apply();
    refreshToggles();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }

  window.AgentRushI18n = { getLang, setLang, t, apply, mountToggle, DICT };
})();
