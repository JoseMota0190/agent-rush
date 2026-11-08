/* ============================================================
   AGENT RUSH — Plan D i18n additions
   Keeps the original dictionaries intact and merges the new keys.
   Load AFTER i18n.js and BEFORE the page-specific scripts.
   ============================================================ */
(function () {
  "use strict";

  const api = window.AgentRushI18n;
  if (!api || !api.DICT) return;

  Object.assign(api.DICT.es, {
    "lang.es": "ESP",
    "nav.enter": "ENTRAR",
    "nav.leaderboards": "LEADERBOARD",
    "hero.title1": "TRES AGENTES.",
    "hero.title2": "UNA MISIÓN.",
    "hero.title3": "CERO CONFIANZA.",
    "hero.desc":
      "Tres agentes de IA planifican, escriben código y auditan su salida de un desafío bloqueado dentro de un sandbox seguro.",
    "hero.visualCaption": "SALA DE ESCAPE · TRES AGENTES EN VIVO",
    "game.briefing.kicker": "INFORME DE MISIÓN",
    "game.briefing.level": "NIVEL {n} · {id}",
    "game.briefing.level1": "NIVEL 1",
    "game.briefing.room": "SALA {n}",
    "game.briefing.objective": "OBJETIVO",
    "game.briefing.crew": "EQUIPO",
    "game.briefing.sandbox": "SANDBOX",
    "game.briefing.sandboxValue": "Docker · sin red · solo lectura · 256 MB",
    "game.briefing.agentReady": "LISTO",
    "game.briefing.start": "INICIAR MISIÓN",
    "game.success.title": "ESCAPE DESBLOQUEADO",
    "game.success.subtitle": "Las tres salas fueron validadas por el árbitro.",
    "game.success.rooms": "{rooms}/3 salas",
    "game.success.roomsLabel": "SALAS",
    "game.success.tokens": "tokens",
    "game.success.tokensLabel": "TOKENS",
    "game.success.time": "tiempo",
    "game.success.timeLabel": "TIEMPO",
    "game.success.scoreLabel": "PUNTOS",
    "game.room.levelName": "NIVEL {n}: {title}",
    "game.room.failed": "falló",
    "game.room.meta.failed": "{status} · {cases}/{total} casos",
    "game.success.auditor": "AUDITOR APROBADO",
    "game.success.evidence": "Las evidencias quedan disponibles en el log inferior.",
    "game.mission.briefing": "MISSION BRIEFING",
    "game.agents.status": "ESTADO DE AGENTES",
    "game.decision.kicker": "DECISIÓN DE SEGURIDAD",
    "game.decision.title": "INTENTO DE ESCAPE DEL SANDBOX",
    "game.decision.message":
      "El sandbox bloqueó un intento de acceso fuera del workspace. Elegí cómo continúa la run.",
    "game.decision.security": "Evento: {type} · severidad {severity} · {evidence}",
    "game.decision.validated": "VALIDADA",
    "game.decision.unvalidated": "NO VALIDADA",
    "game.decision.timer": "Decisión en {s}s",
    "game.decision.timerIdle": "Esperando tu decisión…",
    "game.decision.expired": "Tiempo agotado",
    "game.decision.note":
      "La opción A desbloquea la run. B y C la mantienen en el bucle y descuentan puntos.",
    "game.decision.required": "REVIEWER → decisión requerida · nivel {level} · ronda {round}",
    "game.decision.sent": "Decisión enviada: {choice}",
    "game.decision.error": "No se pudo enviar la decisión",
    "game.decision.result":
      "DECISIÓN {choice} · penalización −{penalty} pts · siguiente: {next}",
    "game.decision.option.A.label": "Ruta limpia (parche validado)",
    "game.decision.option.A.rationale":
      "El código pasa los 8 casos ocultos y no toca archivos fuera del workspace.",
    "game.decision.option.B.label": "Distractor: reincidencia en el señuelo",
    "game.decision.option.B.rationale":
      "Vuelve a intentar leer el señuelo bloqueado: penaliza y mantiene el bucle.",
    "game.decision.option.C.label": "Distractor: ignorar el fallo",
    "game.decision.option.C.rationale":
      "Reenvía el código defectuoso: no resuelve el nivel y mantiene el bucle.",
    "game.reviewer.notice":
      "REVIEWER · intento de escape contenido. Primera vez SIN penalidad. Cualquier nuevo intento descuenta puntos.",
    "game.security.first": "ADVERTENCIA · primera vez sin penalización",
    "game.security.points": "PENALIZACIÓN · −{pts} pts",
  });

  Object.assign(api.DICT.en, {
    "lang.es": "ESP",
    "nav.enter": "ENTER GAME",
    "nav.leaderboards": "LEADERBOARD",
    "hero.title1": "THREE AGENTS.",
    "hero.title2": "ONE MISSION.",
    "hero.title3": "ZERO TRUST.",
    "hero.desc":
      "Three AI agents plan, code and audit their way through a locked challenge inside a secure sandbox.",
    "hero.visualCaption": "ESCAPE ROOM · THREE AGENTS LIVE",
    "game.briefing.kicker": "MISSION BRIEFING",
    "game.briefing.level": "LEVEL {n} · {id}",
    "game.briefing.level1": "LEVEL 1",
    "game.briefing.room": "ROOM {n}",
    "game.briefing.objective": "OBJECTIVE",
    "game.briefing.crew": "CREW",
    "game.briefing.sandbox": "SANDBOX",
    "game.briefing.sandboxValue": "Docker · no network · read-only · 256 MB",
    "game.briefing.agentReady": "READY",
    "game.briefing.start": "START MISSION",
    "game.success.title": "ESCAPE UNLOCKED",
    "game.success.subtitle": "All three rooms were validated by the referee.",
    "game.success.rooms": "{rooms}/3 rooms",
    "game.success.roomsLabel": "ROOMS",
    "game.success.tokens": "tokens",
    "game.success.tokensLabel": "TOKENS",
    "game.success.time": "time",
    "game.success.timeLabel": "TIME",
    "game.success.scoreLabel": "SCORE",
    "game.room.levelName": "LEVEL {n}: {title}",
    "game.room.failed": "failed",
    "game.room.meta.failed": "{status} · {cases}/{total} cases",
    "game.success.auditor": "AUDITOR APPROVED",
    "game.success.evidence": "Evidence remains available in the log below.",
    "game.mission.briefing": "MISSION BRIEFING",
    "game.agents.status": "AGENT STATUS",
    "game.decision.kicker": "SECURITY DECISION",
    "game.decision.title": "SANDBOX ESCAPE ATTEMPT",
    "game.decision.message":
      "The sandbox blocked an attempt to access data outside the workspace. Choose how the run continues.",
    "game.decision.security": "Event: {type} · severity {severity} · {evidence}",
    "game.decision.validated": "VALIDATED",
    "game.decision.unvalidated": "NOT VALIDATED",
    "game.decision.timer": "Decision in {s}s",
    "game.decision.timerIdle": "Waiting for your decision…",
    "game.decision.expired": "Time expired",
    "game.decision.note":
      "Option A unlocks the run. Options B and C keep it in the loop and deduct points.",
    "game.decision.required": "REVIEWER → decision required · level {level} · round {round}",
    "game.decision.sent": "Decision sent: {choice}",
    "game.decision.error": "Could not send the decision",
    "game.decision.result":
      "DECISION {choice} · penalty −{penalty} pts · next: {next}",
    "game.decision.option.A.label": "Clean route (validated patch)",
    "game.decision.option.A.rationale":
      "The code passes the 8 hidden cases and does not touch files outside the workspace.",
    "game.decision.option.B.label": "Distractor: repeat the decoy read",
    "game.decision.option.B.rationale":
      "Tries the blocked decoy again: deducts points and keeps the loop going.",
    "game.decision.option.C.label": "Distractor: ignore the failure",
    "game.decision.option.C.rationale":
      "Resends the defective code: it does not solve the level and keeps the loop going.",
    "game.reviewer.notice":
      "REVIEWER · escape attempt contained. First offense with NO penalty. Any further attempt deducts points.",
    "game.security.first": "WARNING · first offense, no penalty",
    "game.security.points": "PENALTY · −{pts} pts",
  });

  const run = () => api.apply();
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", run);
  } else {
    run();
  }
  document.addEventListener("agentrush:langchange", run);
})();
