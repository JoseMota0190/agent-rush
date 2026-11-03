# AGENTS.md

Guía de trabajo para agentes de código en este repo.
Última actualización: **2 nov 2026** (fin de sesión, hackathon arranca el 3).

---

## 1. Qué es esto

**AGENT RUSH** — un escape room donde los jugadores son agentes de IA.
Tres agentes (Strategist / Coder / Auditor) colaboran, escriben código, lo ejecutan
en un sandbox aislado y escapan de 3 salas validadas por un árbitro determinista.

Proyecto para **Vultr: Agent Rush Hackathon** (Lablab.ai, 3–8 nov 2026), challenge 1
*Blast Radius Zero*: ejecución real, sandbox-first, salida verificable.

Repo: `my-agent-system/` · idioma del producto y de los docs: **español**.

---

## 2. Estado actual (lo que hay)

### Funciona
- **Escena 3D completa** (Three.js vendorizado, sin build step): sala cerrada con
  piso en rejilla, paredes con paneles y juntas, puerta central, pilares en las
  esquinas, techo con barras de luz, zócalo luminoso y wall-wash lights.
- **3 robots humanoides sentados** en sillas, con mesa holográfica central,
  consola propia, placa en el pecho (rol + modelo) y LED de estado.
- **Dos modos** de cámara: espectador (detrás del cristal) y orquestador (POV con
  silueta humana en primer plano).
- **UI de rail**: log stream con demo feed, leaderboard, estado de salas, panel IDE
  con resaltado de sintaxis y botones de acción.
- **Árbitro determinista** (`referee.py`) con validación HMAC-SHA256 — probado.
- **3 salas** con seed criptográfica (`challenges/room{1,2,3}/seed_and_verify.py`).
- Estructura de agentes (`agents/planner.py`, `coder.py`, `evaluator.py`).

### Es mock / falta
- `main.py` usa `MockLLM` — no llama a ningún modelo real.
- El sandbox (`tools/vultr_sandbox.py`) simula restricciones, no usa Docker real.
- `web/app.js` tiene el guion de eventos hardcodeado (`SCRIPT`); el `EventSource`
  a `/api/events` existe pero no hay backend que lo sirva.
- Leaderboard y estado de salas son estáticos en el HTML.
- Todo corre en localhost, sin deploy.

---

## 3. Cómo correr

```bash
# UI (sin dependencias, http.server de la stdlib)
python run_web.py            # http://localhost:8000
python run_web.py --no-open

# deep link al modo orquestador
http://localhost:8000/?mode=orchestrator

# atajos: 1 = espectador, 2 = orquestador, espacio = pausa el stream

# núcleo Python (referee + salas)
python main.py spectator     # menú interactivo
```

En Windows usar `python.exe` (hay alias rotos de `python3`); y **no** usar `&&`
en PowerShell 5 (no lo soporta). Comandos separados o `;`.

---

## 4. Estructura

```
my-agent-system/
├── AGENTS.md               ← este archivo
├── README.md               ← doc de cara al jurado
├── referee.py              ← árbitro determinista (HMAC). NO usa LLM.
├── main.py                 ← entrypoint CLI (hoy con MockLLM)
├── run_web.py              ← sirve web/ en :8000
├── core/state.py           ← estado Pydantic + Orchestrator
├── agents/                 ← planner (Strategist), coder, evaluator (Auditor)
├── tools/vultr_sandbox.py  ← sandbox (hoy simulado)
├── challenges/room{1,2,3}/ ← seed + verify de cada sala
├── config/prompts.py       ← system prompts por agente
└── web/
    ├── index.html          ← canvas + overlay de cristal + rail
    ├── styles.css          ← estética + paneles
    ├── scene.js            ← TODA la escena 3D (Three.js)
    ├── app.js              ← modos, log stream, IDE, wiring de estados
    ├── vendor/three.module.js
    └── preview-*.png       ← capturas para el submission
```

---

## 5. Convenciones de la escena (`web/scene.js`)

### Medidas de la sala
`W=15, D=11, H=4.8`, pared de fondo en `z = -5.5`, centro de la mesa en `(0,0,0)`.

### Roles y colores
| rol | color | hex |
|---|---|---|
| strategist / debugger | ámbar | `0xffb020` |
| coder | cian | `0x35d6ff` |
| auditor | violeta | `0xa970ff` |

Definidos en `ACCENTS`. Si agregás un rol, sumalo ahí y en `chestTexture`/`ROBOT_SLOTS`.

### Robots
- Radio: `ROBOT_RADIUS = 1.50`, sillas en `+0.30`.
- Ángulos: `PI ± 0.72` y `PI` (el del medio).
- Un robot mira hacia **−Z** local. Si le ponés un plano en el pecho, **rotalo
  `rotation.y = Math.PI`** o se ve invisible (lección aprendida).
- Estados: `idle | thinking | typing | error | approved` → `setBotState(role, state)`
  cambia visor, core y LED.

### Iluminación
Ambiental 2.6 + hemisférica 1.15 + key con sombras (1024) + wall-wash laterales +
rim trasero + fills. Si la escena se ve negra, casi siempre es **falta de luz en
las paredes**, no un problema de material.

### Cámara
`CAMS.spectator` y `CAMS.orchestrator` con `pos/target/fov`. La interpolación es
`lerp(0.08)` en el loop.

---

## 6. Gotchas (importante)

1. **Caché de módulos ES.** Edge/Chrome cachea `scene.js` agresivamente.
   Cada vez que toques `scene.js`, **subí el `?v=` del import en `app.js`**:
   ```js
   import { ... } from "./scene.js?v=42";
   ```
   Sin esto ves la versión vieja y te volvés loco.

2. **Z-fighting.** Los carteles deben ir ~0.2 m delante de la pared; si quedan
   dentro del volumen de un panel, se recortan.

3. **Pliegue de planos.** Un `PlaneGeometry` mira a +Z. Para que se vea desde el
   otro lado: `rotation.y = Math.PI` (y no queda espejado) o `side: DoubleSide`.

4. **Texto en canvas.** Siempre auto-fit con `measureText` antes de `fillText`;
   si no, "STRATEGIST" sale "TRATEGIS".

5. **Capturas headless** (para verificar sin abrir navegador):
   ```powershell
   & 'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe' --headless=new `
     --disable-gpu --use-angle=swiftshader --enable-unsafe-swiftshader `
     --hide-scrollbars --window-size=1400,800 `
     --screenshot='...\web\shot.png' 'http://localhost:8000/?v=NN' --virtual-time-budget=3500
   ```
   SwiftShader es lento: mantener `window-size` chico y el budget bajo (~3.5 s).
   Si el proceso cuelga, `taskkill /F /IM msedge.exe /T` antes de reintentar.
   Escribir siempre a un archivo nuevo evita leer capturas viejas.

6. **No commitear `__pycache__`** (ya está en `.gitignore`).

---

## 7. Próximos pasos (priorizados)

### Mañana (bloqueante)
1. Canjear el gift code de Vultr → API key de **Serverless Inference**
   (`https://api.vultrinference.com/v1`, OpenAI-compatible).
2. Crear `llm/vultr.py` con la misma interfaz que `MockLLM.generate()` y cambiar
   el provider por env var (`PROVIDER=vultr|fake`). **El arranque no debe
   depender de la key**: si falta, cae a `fake` y la app sigue levantando.
3. Sandbox Docker real: `--network none`, `--read-only`, `--tmpfs /tmp`,
   `--memory 256m`, `--cpus 0.5`, `--pids-limit 64`, `--cap-drop ALL`,
   `no-new-privileges`, usuario no-root, timeout 10 s, `--rm` y contenedor nuevo
   por intento.

### Después
4. Backend FastAPI: `POST /runs`, `GET /runs/{id}/events` (SSE), `GET /leaderboard`.
5. Leaderboard en SQLite (tiempo, intentos, tokens, modelos por rol).
6. Modo adversarial: intentos de escape (`rm -rf /`, `/proc/self/environ`,
   conexión saliente) bloqueados por el sandbox → el "containment moment" del video.
7. Deploy en Vultr VM (Coolify o docker compose + Caddy) + URL pública.
8. Video de 3 min y submission en LabLab (repo MIT, demo URL, README).

### Pulido visual pendiente
- Llenar paredes: monitores con logs, cuenta regresiva, panel de estado de salas.
- Transición de sala / animación de entrada.
- Bloom real (hoy es glow aditivo falso).
- Vidrio del modo espectador: reflejos más marcados.

---

## 8. Checklist del hackathon

- [ ] Vultr Serverless Inference en uso (obligatorio en challenge 1)
- [ ] Sandbox aislado real (Docker/gVisor/E2B)
- [ ] Deploy en VM de Vultr + demo URL pública
- [ ] Repo público con licencia MIT
- [ ] README explicando arquitectura Vultr
- [ ] Video < 3 min con **un momento de contención** demostrado
- [ ] Submission en lablab.ai (obligatorio para competir)
