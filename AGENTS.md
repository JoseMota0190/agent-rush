# AGENTS.md

Guía de trabajo para agentes de código en este repo.
Última actualización: **4 nov 2026** (wizard de entrada, catálogo Vultr, topbar de sala y compuerta de inicio; EN por defecto).

---

## 1. Qué es esto

**AGENT RUSH** — un escape room donde los jugadores son agentes de IA.
Tres agentes (Strategist / Coder / Auditor) colaboran, escriben código, lo ejecutan
en un sandbox aislado y escapan de 3 salas validadas por un árbitro determinista.

Proyecto para **Vultr: Agent Rush Hackathon** (Lablab.ai, 3–8 nov 2026), challenge 1
*Blast Radius Zero*: ejecución real, sandbox-first, salida verificable.

Repo: `my-agent-system/` · docs en **español** · producto **bilingüe ES/EN** (default ES).

---

## 2. Estado actual (lo que hay)

### Funciona
- **Landing page** (`web/index.html`): intro, cómo funcionan los 3 agentes,
  tarjetas de los dos modos, catálogo Vultr de solo lectura, wizard de entrada y
  dos leaderboards.
- **Escena 3D completa** (Three.js vendorizado, sin build step): sala cerrada con
  piso en rejilla, paredes con paneles y juntas, puerta central, pilares en las
  esquinas, techo con barras de luz, zócalo luminoso y wall-wash lights.
- **3 robots humanoides sentados** en sillas, con mesa holográfica central,
  consola propia, placa en el pecho (rol + modelo) y LED de estado.
- **Dos modos** de cámara: espectador (detrás del cristal) y orquestador (POV con
  silueta humana en primer plano).
- **UI de rail del juego**: la sala abre vacía con una **compuerta de inicio**
  (`CLICK TO START`); al iniciar muestra la consigna de la sala 1. Sin guion demo.
  Estado de salas y panel IDE con resaltado de sintaxis y botones de acción.
- **Topbar del juego**: marca estática (no link), badge del modo actual, energía,
  idioma y botón de salida. Ya no hay pestañas de modo, `INICIO` ni `MODELOS`.
- **Contador de energía** en la topbar del juego: arranca en `0 / 100,000` y solo
  cambiará con eventos reales del backend. Sin timers ni demo.
- **Wizard de entrada** (`web/wizard.js`): Enter the game → modo → modelos;
  las tarjetas de modo saltan directo a modelos. Guarda en `sessionStorage` y
  navega a `game.html?mode=...`.
- **Catálogo Vultr** (`web/catalog.js`): lista de solo lectura con los modelos de
  `/api/models` + logo en `web/assets/vultr-logo.svg`. No asigna ni guarda nada.
- **Leaderboards por modo** en la landing (`#leaderboards`): espectador y
  orquestador, alimentados por `GET /api/leaderboard` desde SQLite. Solo lista
  runs reales exitosas; si la base está vacía, muestra el estado vacío.
- **Avatares de los agentes** en "CÓMO FUNCIONA" (`web/avatars/*.svg`), con los
  mismos colores y diseño que los robots de la sala 3D.
- **i18n ES/EN** (`web/i18n.js`): **default inglés**, selector en la topbar,
  persistencia en `sessionStorage` (misma pestaña), `?lang=es` para forzar español.
  ES mantiene la misma funcionalidad que EN, solo traducida.
- **Árbitro determinista** (`referee.py`) con validación HMAC-SHA256 — probado.
- **3 salas** con seed criptográfica (`challenges/room{1,2,3}/seed_and_verify.py`).
- Estructura de agentes (`agents/planner.py`, `coder.py`, `evaluator.py`).

### Es mock / falta
- `main.py` (CLI) sigue usando `MockLLM`; el motor web ya usa Vultr real.
- `tools/vultr_sandbox.py` es el wrapper viejo/simulado. El motor web usa Docker
  real desde `run_engine.py`; la prueba está en `tools/containment_probe.py`.
- Falta el modo orquestador “real” (editar y re-ejecutar desde el IDE): la run
  real es la misma, pero los botones del IDE todavía no modifican el código.
- El deploy en Vultr está scripteado (`deploy/`) y pendiente de ejecutar con una
  key general válida.

---

## 3. Cómo correr

```bash
# Web (sin dependencias, http.server de la stdlib)
python run_server.py         # abre http://localhost:8000/ (landing)
python run_server.py --no-open

# rutas
http://localhost:8000/                    # landing (EN por defecto)
http://localhost:8000/?lang=es            # landing en español
http://localhost:8000/?select=1           # landing con el wizard abierto
http://localhost:8000/game.html           # redirige al wizard si no hay selección
http://localhost:8000/#modelos            # catálogo Vultr (solo lectura)
http://localhost:8000/#leaderboards       # leaderboards (vacíos)

# atajo en el juego: espacio = pausa/reanuda (cuando haya logs)

# la energía arranca en 0 y solo se moverá con eventos reales del backend;
# la sala ya no tiene guion demo ni ?tick.

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
├── run_server.py           ← sirve web/ + API (models, agents, leaderboard)
├── run_web.py              ← servidor estático viejo (compatibilidad)
├── core/state.py           ← estado Pydantic + Orchestrator
├── agents/                 ← planner (Strategist), coder, evaluator (Auditor)
├── tools/vultr_sandbox.py  ← sandbox (hoy simulado)
├── challenges/room{1,2,3}/ ← seed + verify de cada sala
├── config/
│   ├── prompts.py          ← system prompts por agente
│   ├── models.py           ← descubrimiento de modelos Vultr + presets
│   ├── model_profiles.py   ← selección por agente (sin API key)
│   └── budget.py           ← límites de tokens
└── web/
    ├── index.html          ← LANDING: intro, modos, modelos, leaderboards
    ├── game.html           ← juego: canvas + overlay de cristal + rail
    ├── config.html         ← redirect a /#modelos (compatibilidad, conserva ?lang)
    ├── i18n.js             ← diccionarios ES/EN + selector + apply()
    ├── catalog.js          ← catálogo Vultr de solo lectura
    ├── wizard.js           ← modo → modelos → sessionStorage → sala
    ├── leaderboard.js      ← fetch + render de los dos leaderboards (vacío = estado vacío)
    ├── styles.css          ← estética + paneles + landing + energía + wizard + inicio
    ├── scene.js            ← TODA la escena 3D (Three.js)
    ├── app.js              ← modo, compuerta de inicio, log stream SSE, IDE, energía
    ├── avatars/            ← strategist.svg, coder.svg, auditor.svg
    ├── assets/             ← vultr-logo.svg
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
     --disable-gpu --use-gl=swiftshader --enable-unsafe-swiftshader `
     --disable-dev-shm-usage --hide-scrollbars --window-size=900,560 `
     --screenshot='...\web\shot.png' 'http://localhost:8000/game.html' --virtual-time-budget=2000
   ```
   SwiftShader es lento: mantener `window-size` chico (900×560) y el budget bajo
   (~2 s). Con `--use-angle=swiftshader` o ventanas grandes el proceso puede
   colgarse; si pasa, `taskkill /F /IM msedge.exe /T` antes de reintentar.
   Para verificar lógica sin captura, `--dump-dom` es más estable que `--screenshot`.
   Escribir siempre a un archivo nuevo evita leer capturas viejas.

6. **Contador de energía en el juego.** El budget por defecto es 100,000 tokens.
   Para probar la descalificación sin esperar: `?budget=1000&tick=100` (el `tick`
   acelera el guion demo). El contador vive en la topbar (`#energy`) y se actualiza
   desde `appendLog()` en `app.js`.

7. **No commitear `__pycache__`** (ya está en `.gitignore`).

---

## 7. Próximos pasos (priorizados)

### Bloqueante
1. **Sandbox Docker real**: `--network none`, `--read-only`, `--tmpfs /tmp`,
   `--memory 256m`, `--cpus 0.5`, `--pids-limit 64`, `--cap-drop ALL`,
   `no-new-privileges`, usuario no-root, timeout 10 s, `--rm` y contenedor nuevo
   por intento.
2. **Backend de runs reales**: `POST /runs`, `GET /runs/{id}/events` (SSE) y
   conectar el `EventSource` de `app.js` (hoy cae al guion demo).
3. **Leaderboard en SQLite** (tiempo, intentos, tokens, modelos por rol) y
   reemplazar `LEADERBOARD_DEMO` de `run_server.py` por consultas reales.

### Después
4. Modo adversarial: intentos de escape (`rm -rf /`, `/proc/self/environ`,
   conexión saliente) bloqueados por el sandbox → el "containment moment" del video.
5. Deploy en Vultr VM (Coolify o docker compose + Caddy) + URL pública.
6. Video de 3 min y submission en LabLab (repo MIT, demo URL, README).

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

---

## 9. Sesión 2026-11-03 (noche) — energía/tokens + menú de modelos

Trabajo hecho por el agente principal (capataz) + subagente free de OpenRouter.

### Subagente codificador free
- Archivo: `.opencode/agent/coder-free.md` (`mode: all`, `temperature: 0.2`).
- Modelo: `openrouter/cohere/north-mini-code:free` (free, con tool calling, 256k ctx).
- Invocación usada (desde la raíz del proyecto):
  ```bash
  opencode run --standalone --agent coder-free \
    --model openrouter/cohere/north-mini-code:free --auto "<tarea>"
  ```
- Nota: el modelo free falla a veces por rate limit (`finish_reason: error`); en esos
  casos el capataz completó el código a mano. Su shell por defecto es PowerShell 5:
  usar `bash -lc "..."` para comandos Unix.

### Núcleo nuevo (Fase 0) — verificado
- `config/__init__.py`
- `config/models.py`: `discover_models()` (GET `/v1/models`, filtra chat por
  `output_modalities.type == "text"`), `FALLBACK_CHAT_MODELS`, `AGENT_DEFAULTS`, `PRESETS`.
- `config/budget.py`: `MAX_TOKENS_PER_RUN` (def **100000**), `MAX_TOKENS_PER_CALL`
  (def 1200), `TOKEN_BUDGET_MODE` (def `hard`), leídos de env.
- `config/model_profiles.py`: `ModelProfile` + `DEFAULT_PROFILES` +
  `load_selection()`/`save_selection()` en `config/model_selection.json`
  (solo model_id/params, **nunca la key**) + `resolve_api_key()`.
- `llm/meter.py`: `TokenMeter` (thread-safe) y `TokenBudgetExceeded`.
- `llm/factory.py`: `MeteredLLM` + `build_all(profiles, meter)` (VultrLLM o MockLLM,
  pasando `model=profile.model_id`).
- `llm/vultr.py`: `generate_with_usage()` (lee `usage`), `list_models()`, `MockLLM`,
  parámetro `model` en `VultrLLM`.

### Juego: tokens = energía (Fase 1) — verificado
- `core/state.py`: `AgentState` y `GameResult` con `token_budget`, `tokens_used`,
  `tokens_by_agent`, `disqualified`.
- `main.py` reescrito: menú CLI de modelos (ver modelos Vultr en vivo, elegir por
  agente, presets, guardar), validación **estricta** Vultr (`--allow-mock` para dev),
  contador de ENERGÍA por paso, y **descalificación** al agotar tokens.
- Flags: `--mode {spectator,orchestrator}`, `--allow-mock`, `--no-menu`,
  `--preset {balanced,fast,quality}`.
- Corrección: `agents/coder.py` tenía un f-string con `FLAG{example}` que lanzaba
  `NameError`; ahora `FLAG{{example}}`.
- Mock ahora imprime `FLAG{MOCK_PROOF}` para que la demo complete 3/3.

### Web (Fase 2/3) — verificado
- `run_server.py` (stdlib, sin dependencias): sirve `web/` y expone
  `GET /api/models`, `GET /api/presets`, `GET /api/agents`, `POST /api/agents`.
- `web/config.html` + `web/config.js`: panel **MODEL CONFIG** con 3 selects por agente,
  preset y botón guardar. Enlace `⚙ MODELOS` agregado en `web/index.html`.
- FastAPI/uvicorn: `fastapi` y `sse_starlette` NO están instalados; por eso el backend
  es stdlib. Si se quiere FastAPI, `pip install -r requirements.txt` primero.

### Cómo correr
```bash
# CLI (menú de modelos + energía)
python3 main.py                    # menú interactivo
python3 main.py --no-menu --preset fast          # directo (necesita key Vultr)
python3 main.py --allow-mock --no-menu --preset fast   # sin Vultr (dev)

# Web (config de modelos + juego estático)
python3 run_server.py              # http://localhost:8000/config.html
```

### Pruebas realizadas (todas OK)
- `py_compile` de todos los módulos.
- Smoke mock: 3/3 salas, energía final ~291/100000.
- Descalificación: `MAX_TOKENS_PER_RUN=20` → “EQUIPO DESCALIFICADO — SIN ENERGÍA”.
- Menú con input pipe: ver selección + guardar + correr.
- Modo estricto: sin key → exit 1 con mensajes por agente.
- Servidor: `/api/models` devolvió 13 modelos de chat en vivo; POST guardó; `/config.html` OK.

### Pendiente (para la próxima sesión)
1. Integrar el **referee** y una condición real de FLAG en el loop (hoy mock imprime FLAG).
   Definir cómo cada sala valida HMAC y cómo el Coder produce la prueba correcta.
2. **Health-check real** por modelo al iniciar (mini-completion) + mostrar el modelo
   en la placa de cada robot en `scene.js`.
3. Barra de ENERGÍA **en vivo** en la UI 3D (hoy solo en CLI/config), vía SSE.
4. Sandbox Docker real y deploy en Vultr VM (pasos 3 y 7 de la sección 7).
5. Revisar presets con los **model IDs reales** (`/api/models`) antes de la demo.
6. Considerar rate limit / replay sin costo para el tráfico de jueces.

---

## 10. Sesión 2026-11-04 — landing, leaderboards y energía

Trabajo hecho por el capataz + subagente free (`openrouter/cohere/north-mini-code:free`).

### Reorganización de páginas
- `web/index.html` pasó a ser la **landing**.
- El juego se movió a `web/game.html` (antes era `index.html`).
- `web/config.html` ahora redirige a `/#modelos` (compatibilidad).
- `run_server.py` abre `/` por defecto y sigue sirviendo `/game.html`.

### Landing (`web/index.html`)
- Hero con intro del proyecto y CTA `ENTRAR AL JUEGO`.
- Sección `CÓMO FUNCIONA` con Strategist / Coder / Auditor.
- Sección `DOS MODOS DE JUEGO` con CTAs a `?mode=spectator` y `?mode=orchestrator`.
- Sección `#modelos`: selector de modelos embebido (reutiliza `config.js`).
- Sección `#leaderboards`: dos tablas, una por modo.
- Estilos nuevos en `web/styles.css` (bloques `LANDING`, `LANDING CONFIG CARD`,
  `LANDING LEADERBOARDS`, `ENERGY METER`). La landing sobreescribe
  `html, body { overflow: hidden }` para poder scrollear.

### Leaderboards
- `GET /api/leaderboard` devuelve ambos modos; `?mode=spectator|orchestrator`
  devuelve uno solo.
- **Sin datos demo**: `run_server.py` devuelve `rows: []` y `has_runs: false`.
- `web/leaderboard.js` hace fetch y renderiza los dos paneles; sin filas muestra
  un estado vacío ("AÚN NO HAY PARTIDAS VÁLIDAS" / badge "EN ESPERA").
- Se eliminó el panel de leaderboard de `game.html` y `flashLeaderboard()` de
  `app.js`.

### Contador de energía
- Chip en la topbar de `game.html`: `⚡ ENERGÍA  usado / 100,000` + barra.
- `app.js`: `TOKEN_BUDGET` (default 100000), `updateEnergy()`, estados
  `is-warn` (70%), `is-danger` (90%) e `is-dead` (descalificado).
- Al agotar el budget: se detiene el stream y se loguea
  `EQUIPO DESCALIFICADO — SIN ENERGÍA`.
- En el replay se resetea el contador.
- Parámetros de prueba: `?budget=1000&tick=100`.

### Verificación
- `python -m py_compile run_server.py` OK.
- `node --check web/app.js` y `node --check web/leaderboard.js` OK.
- `/`, `/game.html`, `/api/agents`, `/api/models`, `/api/leaderboard` → 200.
- Capturas: landing completa, selector de modelos, leaderboards y chip de energía.
- Descalificación verificada por DOM: `1,262 / 1,000` + label `DESCALIFICADO`.

### Notas / gotchas nuevas
- El subagente free se trabó al definir `updateEnergy()`; el capataz la completó
  y agregó el `setTimeout` para romper la recursión `updateEnergy → appendLog`.
- Headless: usar `--use-gl=swiftshader`, ventana 900×560 y budget ~2 s. Con
  `--use-angle=swiftshader` o ventanas grandes el proceso se cuelga.
- `--dump-dom` es más estable que `--screenshot` para verificar lógica.

---

## 11. Sesión 2026-11-04 (tarde) — leaderboard vacío, avatares e i18n

Trabajo delegado al subagente free y **revisado/corregido por el capataz**: el
subagente dejó una base, pero el i18n estaba incompleto, los avatares no se
parecían a los robots y `data-i18n` rompía contadores anidados.

### Leaderboard
- `run_server.py`: `LEADERBOARD` (antes `LEADERBOARD_DEMO`) devuelve
  `{mode, rows: [], has_runs: false}`. Sin filas inventadas.
- `web/leaderboard.js`: render por filas reales; con `rows` vacío muestra
  `.lb-empty` (título + texto) y badge `is-waiting`. Se re-renderiza en
  `agentrush:langchange`.

### Avatares
- `web/avatars/{strategist,coder,auditor}.svg`: busto de robot con cabeza
  cúbica, visera emisiva del color del rol, cresta, hombros, placa de pecho y
  glow. Glifos de visera distintos (barras / prompt / check).
- En la landing reemplazan el círculo numérico; el paso queda como badge
  `.landing-card-step`. Títulos de tarjeta con el color del rol (`--role`).

### i18n
- `web/i18n.js`: `window.AgentRushI18n` con `DICT.es` / `DICT.en` (mismas keys),
  `t()`, `apply()`, `setLang()`, `mountToggle()`.
- Atributos: `data-i18n` (textContent), `data-i18n-title`, `data-i18n-aria`,
  `data-i18n-alt`, `data-i18n-placeholder`. **Nunca** poner `data-i18n` en un
  elemento con hijos (`<b>`, `<span>`) o `apply()` los borra: usá spans internos.
- En esa sesión: default `es` con `localStorage` (luego se cambió a EN +
  `sessionStorage`; ver §12).
- El toggle (`ES | EN`) se monta en `.topbar-lang-switch` (landing y juego).
- Evento `agentrush:langchange` para re-render dinámico (`app.js`, `catalog.js`,
  `wizard.js`, `leaderboard.js`).
- `config.html` conserva el idioma al redirigir a `/#modelos`.

### Gotcha importante (topbar)
La landing tenía reglas `.topbar { position:absolute; background:transparent }`
**dentro de `styles.css`** (no solo en el inline de `index.html`), y se filtraban
al juego: el topbar no ocupaba espacio y la escena lo tapaba. Se eliminaron de
`styles.css` y quedaron solo en el `<style>` de `index.html`. Además el topbar
del juego ahora oculta sys-status (<1250px), MODELOS (<1080px) e INICIO
(<980px) para dejar entrar la energía y el selector de idioma.

### Verificación
- `python -m py_compile run_server.py`; `node --check` de `i18n.js`, `app.js`,
  `config.js`, `leaderboard.js`.
- Cobertura de keys: sin faltantes entre ES/EN ni entre HTML/JS.
- `/api/leaderboard` → `rows: []` en ambos modos.
- Capturas ES/EN de landing y juego (1000-1280 px) y móvil (400-500 px).
- Título de documento y `<html lang>` cambian con el idioma.
- Playwright (Edge headless): toggle real, persistencia entre páginas, `?lang`
  sobre localStorage, avatares cargados, leaderboard vacío, stream avanzando,
  energía subiendo y descalificación ES/EN. Todo en verde.

### Gotcha de JS (ya corregido)
`appendLog()` declaraba `const t = document.createElement("span")`, que sombreaba
el helper `t()` del i18n: al pedir `t("game.events", ...)` lanzaba
`t is not a function` y **congelaba el log stream** (la energía se quedaba en 0).
El span ahora se llama `timeEl`. Si ves errores `t is not a function`, buscá
variables locales llamadas `t`.

---

## 12. Sesión 2026-11-04 (cierre) — wizard EN-first y arranque limpio

Trabajo ejecutado con el subagente free en 5 pasos cortos; el capataz revisó,
corrigió y completó los pasos que el subagente dejó a medias.

### Idioma
- **EN por defecto**; ES solo se activa con click en `ES` (o `?lang=es`).
- Persistencia en **sessionStorage** (`agentrush.lang`), no localStorage. En el
  arranque se elimina la clave vieja de localStorage.
- `config.html` conserva `?lang` y arranca en EN.
- Los textos estáticos del HTML quedaron en inglés para evitar el flash en ES.

### Flujo de entrada
- `web/catalog.js`: catálogo Vultr de solo lectura (13 modelos de
  `/api/models`), logo en `web/assets/vultr-logo.svg`, sin selects ni guardado.
- `web/wizard.js`: wizard de dos pasos.
  - `#enter-game` → paso 1 (modo) → paso 2 (modelos).
  - `[data-wizard-mode]` (tarjetas) → paso 2 directo y bloqueado (sin Back).
  - Precarga: sessionStorage → `/api/agents` → primer modelo.
  - Presets opcionales (objeto de `/api/presets`).
  - Submit explícito, escribe `sessionStorage["agentrush.models"]`
    (`{mode, strategist, coder, auditor}`) + `POST /api/agents` y navega.
  - `?select=1&mode=...` abre el wizard automáticamente (redirect de la sala).
- `web/config.js` se eliminó (lo reemplazan catalog + wizard).

### Sala
- Topbar: marca estática más grande (no link), badge del modo, energía,
  sandbox, ES/EN y botón de salida. Se quitaron INICIO, pestañas de modo y
  MODELOS.
- Sin guion demo ni timers: **energía en 0** y log vacío hasta iniciar.
- Compuerta `CLICK TO START` en spectator (panel a todo el alto) y en el panel
  de estado del orquestador. El IDE queda oculto hasta iniciar.
- Al iniciar: aparece la consigna de la sala 1 (THE LOGS) y el aviso
  “Run engine not connected”. No se inventan logs ni tokens.
- Salida: si ya se inició, pide confirmación; vuelve a `/`.

### Errores del subagente corregidos
- Dejó un `}` faltante en `styles.css` que anulaba todo el bloque del catálogo.
- El wizard trataba `/api/agents` y `/api/presets` como arrays (son objetos),
  exigía preset para habilitar Submit y no enganchaba las tarjetas de la landing.
- En el paso 5 borró las declaraciones de `metrics`/`logStream` y dejó
  referencias a `tickTimer`/`tick`: se reescribió `app.js` completo.
- La compuerta del orquestador quedó dentro de `#statusContent[hidden]`.
  Ahora está fuera y es visible antes de iniciar.
- El contenido de `.wizard-mode` era inline; se pasó a flex column y el wizard a una
  columna en mobile.

### Verificación
- `node --check` de `app.js`, `wizard.js`, `catalog.js`, `i18n.js`,
  `leaderboard.js`; `python -m py_compile run_server.py`.
- Playwright: EN por defecto, ES por click, wizard paso 1/2 desde los 3 CTAs,
  validación de modelos, presets, sessionStorage, redirect sin selección,
  sala vacía (0 logs / energía 0), start, consigna, IDE oculto/visible,
  salida con confirmación, 400/760 px sin scroll horizontal.
- Cobertura i18n ES/EN de todas las claves nuevas (start, challenge, wizard).

### Pendiente
- Deploy en Vultr y video/submission.

---

## 13. Sesión 2026-11-04 (noche) — motor real, sandbox y deploy

### Motor (`run_engine.py`)
- Cliente Vultr **estricto** (`VultrChat`): no usa el fallback a MockLLM de
  `llm/vultr.py`; si Vultr falla, emite `run_failed`.
- 3 salas deterministas:
  1. `THE LOGS`: hash válido entre señuelos (regex SHA256).
  2. `MEMORY LEAK`: suma + SHA-256 del decimal.
  3. `FIREWALL`: HMAC-SHA256 de key/message.
- `EventBus` con historial + `seq` para SSE (el cliente salta duplicados).
- `RunManager`: una run a la vez, SQLite `data/agent_rush.db`, leaderboard real.
- Tokens reales con `TokenMeter` (100k), eventos `energy`.

### Sandbox
- Docker real con `--network none`, `--read-only`, `--tmpfs`, `--memory 256m`,
  `--cpus 0.5`, `--pids-limit 64`, `--cap-drop ALL`,
  `--security-opt no-new-privileges`, `--user 65534:65534`.
- `tools/containment_probe.py` verifica escritura, secretos, red y fork bomb.

### Web / SSE
- `POST /api/runs`, `GET /api/runs/<id>/events`, `POST /api/runs/<id>/abort`.
- `web/app.js` dispara la run real, consume SSE, actualiza logs, energía, bots,
  salas, challenge y estado; salir aborta.
- Corregido: `room_solved` duplicaba el log del referee; se quitó el append del
  front. `strategist` se recorta a 240 chars.

### Deploy
- `deploy/deploy.py`: crea/reutiliza SSH key en Vultr, crea Ubuntu 24.04,
  espera SSH, empaqueta y ejecuta `deploy/setup.sh`.
- `deploy/setup.sh`: Docker, Python, systemd + Caddy en contenedor con red host
  y HTTPS vía `sslip.io`; `.env` en `/opt/agent-rush/.env`.
- Requiere `VULTR_API_KEY` general en `.env` (la key de Inference no sirve para
  la API de Vultr). La key general anterior quedó inválida (401).

### Gotchas
- Docker Desktop en Windows ocupa `0.0.0.0:8000` (backend). Para desarrollo
  local correr `python run_server.py --port 8010 --no-open`. En la VM, 8000.
- La key de Inference se obtiene en **Products → Serverless → Inference →
  suscripción → Overview**; NO en Account → API Access.
- `.env` está gitignoreado; el tar de deploy lo incluye y se borra después.
- Repo público: https://github.com/JoseMota0190/agent-rush (MIT).
