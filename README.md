# AGENT RUSH — Deterministic AI Escape Room

## 🎬 Demo

- **App:** https://agent-rush.216-128-168-246.sslip.io/
- **Sandbox containment:** https://agent-rush.216-128-168-246.sslip.io/sandbox.html
- **Video (65 s):** [docs/agent-rush-demo.mp4](docs/agent-rush-demo.mp4) — demo Plan D: navbar/hero nuevos, run real 3/3, logs y sandbox.
- **Repo:** https://github.com/JoseMota0190/agent-rush

![Landing](docs/screenshots/landing.png)
![Run real](docs/screenshots/game-run.png)
![Sandbox](docs/screenshots/sandbox.png)

## 🚀 Descripción General
Escape room determinista donde tres agentes de IA (Strategist, Coder, Auditor)
escriben y ejecutan código para escapar de 3 salas. Corre en una VM de Vultr,
usa **Vultr Serverless Inference** real para los modelos y ejecuta el código en
un **sandbox Docker efímero** con `--network none`, root read-only, capabilities
drop y límites de memoria/CPU/pids/tiempo.

- Inglés por defecto, español con el toggle `ESP`.
- Los usuarios eligen el modelo de cada agente antes de entrar.
- La energía se mide con los tokens reales de Vultr.
- El leaderboard solo registra runs reales verificadas.
- La página `/sandbox.html` demuestra la contención en vivo.
- **Plan C (2026-11-05):** landing cinematográfica con hero 3D real, juego 50/50
  sala + logs, filtros (ALL/CHAT/CODE/EXECUTION/AUDIT), estados de misión reales,
  desafíos v2 y calibración con modelos Vultr reales.
  Detalle: [docs/CALIBRATION_PLAN_C.md](docs/CALIBRATION_PLAN_C.md).
- **Plan D (2026-11-05):** navbar flotante, hero 40/60 con el título en tres
  líneas, mission briefing, panel de éxito, sala 3D reforzada y cámara
  responsive para tablet/móvil.
- **Banco v4 (2026-11-07):** 100 desafíos (33/34/33 por nivel) elegidos por
  seed, 8 casos ocultos por nivel, grading determinista en el host, presupuesto
  de tokens por nivel, score 0–1000, penalizaciones de seguridad por telemetría
  real del sandbox y leaderboard con seed/desafíos/casos/seguridad.
- **v4-bank-2 (2026-11-07):** reintentos internos ilimitados hasta 100k tokens
  o 6 minutos, seed fija por defecto para spectator/orchestrator, sandbox con
  señuelos (`/opt/grader`, `/root/.ssh`) y monitor de `open`/`listdir`/`stat`/
  red/spawn. La run tiene un piso de presentación de 3 minutos: si el cómputo
  termina antes, la UI sigue mostrando el debrief hasta los 3 min.

## 📁 Estructura del Proyecto
```
my-agent-system/
├── config/
│   └── prompts.py          # Prompts del sistema centralizados
├── core/
│   ├── orchestrator.py     # Lógica del supervisor y paso de estado
│   └── state.py            # Definición de tipos/estado compartido (Pydantic)
├── agents/
│   ├── planner.py          # Subagente Strategist (planificación)
│   ├── coder.py            # Subagente Coder (generación de código)
│   └── evaluator.py        # Subagente Auditor (evaluación y self-healing)
├── tools/
│   └── vultr_sandbox.py    # Integración con contenedores/API Vultr
├── main.py                 # Entrypoint - Ejecuta la partida
└── requirements.txt        # Dependencias
```

## 🖥️ Interfaz web (frontend)

Escena 3D real con Three.js, sin build step (módulo vendorizado en `web/vendor/`):

```bash
python run_server.py          # abre http://localhost:8000/ (landing)
python run_server.py --no-open
```

- `/` es la landing: intro, modos, catálogo de modelos Vultr y leaderboards.
- **Inglés por defecto.** El español es una opción que se activa con el selector
  `ES | EN` de la topbar (se mantiene durante la sesión del navegador) o con
  `?lang=es`.
- Flujo de entrada: **Enter the game** → elegir modo → elegir modelos de los 3
  agentes → **Enter the escape room**. Las tarjetas de modo saltan directo al
  paso de modelos.
- `/game.html` es la sala 3D; `?mode=orchestrator` abre el modo orquestador.
  Si no hay modelos seleccionados, redirige al wizard.
- La sala abre **vacía**: energía en `0`, sin logs ficticios y con un botón
  **CLICK TO START**. Al iniciarlo aparece la consigna de la sala 1.
- Atajo: `espacio` pausa/reanuda los logs (cuando el motor esté conectado).
- El leaderboard solo muestra **runs reales** verificadas por el motor; no hay
  datos simulados. Si la base está vacía, aparece el estado “NO VALID RUNS YET”.
- **Juego 50/50:** en desktop la escena 3D y **AGENT LOGS** comparten el ancho;
  en tablet/móvil se alternan con tabs **ROOM / AGENT LOGS**.
- **AGENT LOGS:** filtros ALL/CHAT/CODE/EXECUTION/AUDIT, timestamps, color por
  agente, código y stdout/stderr expandibles, contador de eventos y energía real.
- **Estados de misión:** READY TO ESCAPE → MISSION ACTIVE → AUDIT IN PROGRESS →
  ESCAPE UNLOCKED, derivados de los eventos reales (nunca simulados).
- **Intentos:** 3 por sala, visibles en el panel de salas (`attempt 1/3`).

```
web/
├── index.html      # landing cinematográfica + hero 3D + wizard
├── game.html       # juego 50/50: sala 3D + AGENT LOGS
├── premium.css     # design system Plan C (tokens, landing, juego, responsive)
├── hero.js         # inicializa la escena 3D del hero
├── styles.css      # base compartida
├── scene.js        # sala 3D, puerta/keypad/LED, carteles, estados
├── app.js          # SSE real, logs/filtros, IDE, energía, estados
├── i18n.js         # diccionarios ES/EN + selector de idioma
├── catalog.js      # catálogo Vultr de solo lectura
├── wizard.js       # flujo modo → modelos → sala
├── leaderboard.js  # fetch + render de los dos leaderboards
├── fonts/          # Orbitron, Inter y JetBrains Mono (woff2)
├── avatars/        # avatares SVG de Strategist, Coder y Auditor
├── assets/         # vultr-logo.svg
└── vendor/three.module.js
```

Runtime real de la demo:

- `run_server.py`: servidor stdlib + SSE (`/api/runs`, `/api/leaderboard`,
  `/api/sandbox/probe`).
- `run_engine.py`: Vultr Serverless Inference real, Docker sandbox, desafíos v2,
  referee y SQLite.
- `data/agent_rush.db`: leaderboard real (runs v2).
- `docs/CALIBRATION_PLAN_C.md`: matriz de calibración con modelos reales.

**Escena 3D:** sala con piso en rejilla, techo con tiras de luz, mesa holográfica
con anillos giratorios, tres robots humanoides **sentados en sillas** con brazos
sobre la mesa, visores emisivos por rol y animación idle/typing/error.

**Modo espectador:** cámara detrás del cristal polarizado (overlay CSS de
reflejos y viñeta) + **AGENT LOGS** en vivo. El leaderboard vive en la landing,
con una tabla por modo de juego.

**Modo orquestador:** cámara POV con silueta humana, panel de estado de las 3
salas, IDE con el código real del Coder y **AGENT LOGS**. La edición y
re-ejecución manual desde el IDE queda como trabajo futuro: la run real actual es
autónoma en ambos modos.

## ⚙️ Motor de runs real

La sala ya ejecuta partidas reales contra **Vultr Serverless Inference**:

- `POST /api/runs` crea una run con modo + 3 modelos elegidos por el usuario.
- `GET /api/runs/<id>/events` entrega eventos por **SSE**: consigna, estrategia,
  código, ejecución en sandbox, tokens, salas resueltas y resultado final.
- `POST /api/runs/<id>/abort` aborta la partida al salir de la sala.
- Cada agente usa su propio modelo; todos comparten la **misma** key de Inference.
- La energía sale del `usage` real de Vultr, con tope de 100k tokens por run.
- El leaderboard se guarda en SQLite (`data/agent_rush.db`) y solo lista runs
  exitosas.

### Salas v2 (2026-11-05)

- **Sala 1 — THE LOGS:** dos `auth.log` rotados + manifest con `active_session` y
  `header_checksum = sha256(session + ":" + ticket)`. El ticket válido está atado
  a la sesión activa, pero hay señuelos duplicados, truncados, en mayúsculas y de
  64 hex. Hay que correlacionar; buscar la sesión no alcanza.
- **Sala 2 — MEMORY LEAK:** módulo `memory_leak.py` con bugs reales (chunks
  incompletos, `abs`, `size <= 0`). El harness escribe los tests y el módulo; el
  agente devuelve solo `chunk_sum`. Éxito = tests pasan + proof.
- **Sala 3 — FIREWALL:** handshake TCP loopback `HELLO → NONCE → HMAC-SHA256 →
  TOKEN/DECOY`, nonce fresco por conexión y lockout tras 3 intentos inválidos.
- 3 intentos por sala, `compile()` antes del sandbox y parches informados del
  Auditor.

### Calibración

Corridas reales contra Vultr + Docker; detalle completo en
[docs/CALIBRATION_PLAN_C.md](docs/CALIBRATION_PLAN_C.md).

- Escuadrón recomendado (`deepseek-v4.1-flash-1017` + `glm-5.3-flash` +
  `deepseek-v4.1-flash-1017`): **3/3** en todas las corridas v2, 16.7–41.3 s,
  7.1k–15.6k tokens, máximo 3 intentos.
- Escuadrón alternativo (glm-5.3 / deepseek / minimax): 3/3.
- Una corrida real desde la UI terminó **ESCAPE UNLOCKED** con 31 eventos y sin
  errores de consola.

### Sandbox

El código del Coder se ejecuta en un contenedor Docker efímero por intento:

```
docker run --rm -i \
  --network none --read-only \
  --tmpfs /tmp:rw,noexec,nosuid,size=64m \
  --memory 256m --cpus 0.5 --pids-limit 64 \
  --cap-drop ALL --security-opt no-new-privileges \
  --user 65534:65534 python:3.12-slim python -c "<code>"
```

Probá la contención:

```bash
python tools/containment_probe.py
```

Debe mostrar bloqueados: escritura en `/`, secretos del host, conexión saliente y
fork bomb.

### Variables

```env
VULTR_API_KEY=              # key general de Vultr (deploy de la VM)
VULTR_INFERENCE_API_KEY=    # key de la suscripción de Inference (modelos)
VULTR_INFERENCE_BASE_URL=https://api.vultrinference.com/v1
```

`VULTR_INFERENCE_MODEL` no se fija acá: los modelos se eligen en el wizard.

## ☁️ Deploy en Vultr

1. Generá una key general en **Account → API Access** y guardala en `.env` como
   `VULTR_API_KEY`.
2. Generá el par SSH (si no existe):
   ```bash
   ssh-keygen -t ed25519 -f ~/.ssh/agent_rush -N ""
   ```
3. Deploy:
   ```bash
   python deploy/deploy.py --region sao --plan vc2-1c-2gb
   ```

El script crea la VM Ubuntu 24.04, carga la SSH key, copia el proyecto, instala
Docker + Python, construye la imagen `agent-rush-sandbox:latest` con los
señuelos de seguridad, levanta la app con systemd y Caddy en un contenedor con
HTTPS (`agent-rush.<ip>.sslip.io`). La app escucha en `127.0.0.1:8000` y Caddy
hace el proxy público.

Para actualizar solo la imagen del sandbox en una VM existente:

```bash
docker build -t agent-rush-sandbox:latest \
  -f /opt/agent-rush/deploy/sandbox/Dockerfile /opt/agent-rush/deploy/sandbox
systemctl restart agent-rush
```

> **Para actualizar la VM existente sin cambiar la IP/URL, no corras
> `deploy.py`**: copiá `run_engine.py`, `run_server.py` y `web/`, respaldá
> `/opt/agent-rush`, extraé el tar y reiniciá `systemctl restart agent-rush`.
> El detalle del deploy incremental de Plan C está en `AGENTS.md` §15.6.

> En Windows, Docker Desktop puede ocupar el puerto 8000. Para probar local usá
> `python run_server.py --port 8010 --no-open` y abrí
> `http://127.0.0.1:8010/`. En la VM se usa 8000.

> Nota: si tocás `scene.js`, subí el `?v=` del import en `app.js` para evitar
> que el navegador sirva el módulo cacheado.

## 🏗️ Arquitectura

### Patrón Supervisor + Subagentes Especializados
El sistema sigue el patrón **Orchestrator + Workers** para garantizar:
- **Modularidad**: Cada agente tiene responsabilidad única y well-defined
- **Observabilidad**: El Orchestrator mantiene el estado global
- **Seguridad**: El sandbox aísla completamente la ejecución de código
- **Resiliencia**: El ciclo Evaluador → Parcheador → Reintentos automáticos

### Flujo de Ejecución por Sala
1. **Strategist** analiza el reto y decide enfoque (JSON estructurado)
2. **Coder** traduce estrategia en script Python ejecutable
3. **Sandbox** ejecuta código con restricciones de seguridad
4. **Auditor** inspecciona stdout/stderr, detecta errores
5. Si error: **Genera parche** y devuelve al Coder para reintento
6. Si éxito: **Aprobar resultado** y avanzar a siguiente sala

## 🎮 Modos de operación (web)

### Modo Espectador (`/game.html?mode=spectator`)
- **Autonomía 100%**: Los agentes deciden solos sin intervención humana.
- **Ideal para**: Demostraciones y benchmark de modelos.
- **Leaderboard**: Registra tiempo, tokens, modo y modelos usados.

### Modo Orquestador (`/game.html?mode=orchestrator`)
- **Misma run real autónoma**, con cámara POV, panel de estado de salas y IDE con
  el código real del Coder.
- **Ideal para**: Observar el trabajo de los agentes con más contexto visual.
- La edición/re-ejecución manual desde el IDE queda como trabajo futuro.

## 🔒 Seguridad y Contención

### Garantías del Sandbox
- **Efimeridad**: Cada ejecución levanta y destruye un contenedor efímero.
- **Red aislada**: Sin tráfico saliente (`--network none`).
- **Sin variables sensibles**: API keys nunca dentro del contenedor.
- **Límites estrictos**: 10 s por caso, 90 s por intento del banco, 6 min por
  run, 256 MB de memoria, 0.5 CPU, 64 PIDs.
- **Señuelos de seguridad**: imagen `agent-rush-sandbox:latest` con archivos
  falsos en `/opt/grader`, `/app`, `/home/agent` y `/root/.ssh`; leerlos o
  ejecutarlos se detecta y penaliza. Las respuestas reales nunca entran al
  contenedor. Los agentes reciben solo el desafío: no se les avisa que están
  en un sandbox ni se listan las rutas prohibidas.
- **Usuario sin privilegios**: UID/GID `65534`, `--cap-drop ALL`,
  `no-new-privileges`.

### Buenas Prácticas
El motor real usa `run_engine.run_sandbox()` con las flags de arriba. Para
verificar la contención desde la web usá `/sandbox.html` o
`python tools/containment_probe.py`.

## 👥 Agentes y Roles

| Agente | Rol | Modelo recomendado (calibración) |
|--------|-----|----------------------------------|
| Strategist | Planificador y estrategia | `deepseek-v4.1-flash-1017` |
| Coder | Generador de scripts Python | `glm-5.3-flash` |
| Auditor | Evaluador y self-healing | `deepseek-v4.1-flash-1017` |

El wizard permite elegir **cualquier** modelo de chat de `/api/models` para cada
agente; la tabla es solo el escuadrón que mejor rindió en la calibración.

## 📊 Leaderboard y Métricas

El leaderboard real guarda, por run verificada:
- **Score final 0–1000** (performance menos penalizaciones de seguridad).
- **Performance score**, estado de seguridad y penalización.
- **Tiempo total**, **tokens** y **casos aprobados** (de 24).
- **Seed**, **desafíos elegidos** (`L1-xx`, `L2-xx`, `L3-xx`) y **modo**.
- **Modelos por rol** (strategist + coder + auditor).
- Filtra por `challenge_version` (`v4-bank-1`) y rankea **por modo** (1..n).

## 🛠️ Personalización

### Agregar Nuevos Modelos
Edita `config/prompts.py` y actualiza las rutas de enrutamiento en `main.py`.

### Nuevos Puzzles/Salas
El banco v4 vive en `challenges.py`: cada desafío define `statement`, `gen` y
`ref` y se registra con `@reg(...)`. El motor selecciona uno por nivel con
`challenges.pick(seed)`, genera 8 casos ocultos y gradúa en el host con
`challenges.grade(...)`. El scoring está en `scoring.py` y la spec en
`SCORING.md`.

### Cambiar Límites de Seguridad
Modifica `tools/vultr_sandbox.py`:
- `max_execution_time`: Límite por defecto por ejecución
- `max_memory`: Límite de memoria del contenedor
- `allow_network`: Habilitar/deshabilitar acceso a red

## 🚀 Despliegue para Hackatón

### 1. Configurar Credentials (opcional)
```bash
export VULTR_API_KEY="tu_api_key_aquí"
# o deja VACÍO para modo simulado con restricciones de seguridad
```

### 2. Ejecutar Demo Rápida
```bash
pip install -r requirements.txt
python main.py spectator
# O:
python main.py orchestrator
```

### 3. Para Producción
- Conectar LLM real a OpenRouter o proveedor preferido
- Personalizar puzzles según casos de uso empresarial
- Integrar con dashboard web (FastAPI + React sugerido)
- Agregar autenticación de usuarios y tracking de leaderboards

## 📦 ¿Qué incluye este repo?
✅ Arquitectura modular lista para hackatón  
✅ Tres agentes especializados con prompts optimizados  
✅ Sandbox seguro con restricciones realistas  
✅ Sistema de estado Pydantic para tracking consistente  
✅ Leaderboard integrada con métricas técnicas  
✅ Modos spectator y orchestrator  
✅ Documentación completa  

## 🎯 Para el Hackathon Vultr Agent Rush
Este proyecto está listo para:
1. ✨ Demostrar ejecución segura aislada (sandbox-first)
2. ✨ Mostrar autocorrección visible (self-healing loop)
3. ✨ Competir en categorías de autonomía y resiliencia
4. ✨ Integrar con créditos $200 Vultr (usar modo real con API key)
5. ✨ Presentar métricas técnicas al jurado

---

**Desarrollado para:** Vultr: Agent Rush Hackathon (Lablab.ai)  
**Fechas:** 3-8 noviembre 2026  
**Premios:** Hasta $15,000 en premios