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
    "game.briefing.level": "NIVEL {n}",
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
    "game.success.auditor": "AUDITOR APROBADO",
    "game.success.evidence": "Las evidencias quedan disponibles en el log inferior.",
    "game.mission.briefing": "MISSION BRIEFING",
    "game.agents.status": "ESTADO DE AGENTES",
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
    "game.briefing.level": "LEVEL {n}",
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
    "game.success.auditor": "AUDITOR APPROVED",
    "game.success.evidence": "Evidence remains available in the log below.",
    "game.mission.briefing": "MISSION BRIEFING",
    "game.agents.status": "AGENT STATUS",
  });

  const run = () => api.apply();
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", run);
  } else {
    run();
  }
  document.addEventListener("agentrush:langchange", run);
})();
