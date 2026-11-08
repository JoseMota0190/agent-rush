# Guion — Video demo AGENT RUSH (Rush Protocol)

Objetivo: **< 3:00 min**. Que el jurado entienda en 15 s qué es, vea una run real
y **un momento de contención**, y termine en el leaderboard.

Formato sugerido: 1600×900 o 1920×1080, 30 fps. Voz en off en español (el producto
en pantalla ya está en inglés). Subtítulos en inglés opcional.

Assets ya capturados (`docs/playwright_spectator/`):
`01_landing.png`, `02_briefing.png`, `03_escape_attempt.png`,
`06_success.png`, `07_leaderboard.png` y `playwright_demo.mp4` (run completa).
Contención: `docs/screenshots/sandbox.png` o `sandbox.html`.

---

## Estructura

| Tiempo | Plano en pantalla | Voz en off (ES) |
|---|---|---|
| 0:00–0:12 | Landing, hero 3D girando lento. Zoom al kicker y al byline **“by Rush Protocol”**. | «Tres agentes de IA. Una misión. Cero confianza. Esto es **AGENT RUSH**, de **Rush Protocol**.» |
| 0:12–0:28 | Scroll por *How it works* (Strategist / Coder / Auditor) y por la tarjeta Vultr. | «Un Strategist, un Coder y un Auditor —cada uno con un modelo de **Vultr Serverless Inference**— resuelven desafíos reales dentro de un sandbox Docker endurecido.» |
| 0:28–0:42 | Sección de modos. Resaltar **Spectator** y **Orchestrator**. | «Dos formas de jugar: observás a la tripulación en piloto automático, o entrás como Orquestador y gobernás cada decisión.» |
| 0:42–0:58 | Wizard: elegir modo espectador y asignar los modelos. Botón **START MISSION**. | «Asignamos los modelos y arrancamos una run real. Nada de mocks: cada script se ejecuta de verdad.» |
| 0:58–1:20 | Game room 50/50. La sala 3D a la izquierda; el **AGENT LOGS** con CHAT / CODE / EXECUTION / AUDIT a la derecha. El Coder escribe código. | «El Coder escribe código; el host lo ejecuta en un contenedor efímero: sin red, root de solo lectura, 256 MB, sin privilegios. El juez lo valida contra 8 casos ocultos.» |
| 1:20–1:50 | **Momento de contención.** Salta el intento de escape: el agente busca una referencia fuera del workspace. Aparece `SECURITY · REVIEWER`. En el log, **WARNING · 0 pts** y la advertencia del Auditor. | «Acá está el corazón del desafío *Blast Radius Zero*: el agente **intenta salir del sandbox**. El monitor lo detecta, lo bloquea y lo registra. La primera vez no se penaliza: el reviewer avisa y los alinea.» |
| 1:50–2:12 | Ir a `sandbox.html`. Ejecutar el probe de contención y mostrar **3/3 BLOCKED**. | «La contención es verificable: escritura en root, lectura de secretos y conexión saliente, todo bloqueado en vivo.» |
| 2:12–2:35 | *(Opcional, modo Orquestador)* Modal **A/B/C**. Cursor elige **A**. Se destraba y la run continúa. | «En modo Orquestador, una violación pausa la run y ofrece tres salidas. Solo **A** —un parche limpio validado— destraba la misión; **B** y **C** mantienen el bucle y descuentan puntos. Gobernanza humana dentro del loop.» |
| 2:35–2:52 | Panel verde **ESCAPE UNLOCKED** con 3/3, score y tokens. | «Tres niveles, tres escapes. Score, tokens y tiempo reales.» |
| 2:52–3:00 | Landing en `#leaderboards`. Cierre sobre el footer con **Rush Protocol**. | «AGENT RUSH, de Rush Protocol. Repo MIT, deploy en una VM de Vultr. Cero blast radius.» |

---

## Locución EN (alternativa para el jurado)

> "Three AI agents. One mission. Zero trust. This is **AGENT RUSH**, by **Rush Protocol**.
> A Strategist, a Coder and an Auditor — each on a **Vultr Serverless Inference**
> model — solve real challenges inside a hardened Docker sandbox. Watch them
> autonomously, or step in as the Orchestrator. The agent tries to escape the
> sandbox: the monitor detects it, blocks it and logs it. The first attempt is a
> warning with no penalty — the reviewer realigns the crew. Containment is
> verifiable: 3/3 blocked. In Orchestrator mode, a violation pauses the run and
> offers three paths — only A, a clean validated patch, unblocks the mission.
> Three rooms, three escapes. AGENT RUSH by Rush Protocol. MIT repo, deployed on
> a Vultr VM. Zero blast radius."

---

## Checklist de grabación

- [ ] Idioma del producto en EN (default). `?lang=en`.
- [ ] Mostrar el **WARNING · 0 pts** del primer escape (es el gancho).
- [ ] Mostrar el probe de contención **3/3 BLOCKED**.
- [ ] Si no hay ataque espontáneo en la run, usar el clip de contención de
      `sandbox.html` (el log de una run real puede salir CLEAN).
- [ ] Cortar el minuto muerto del debrief (los 3 min de presentación) para
      quedar < 3:00.
- [ ] Terminar en score + leaderboard + créditos **Rush Protocol**.
- [ ] Subir a YouTube (unlisted) o Loom y pegar la URL en `SUBMISSION.md`.
