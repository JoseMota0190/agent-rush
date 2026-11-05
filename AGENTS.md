# AGENTS.md

Guía de trabajo para agentes de código en este repo.
Última actualización: **4 nov 2026** (motor real, deploy en Vultr y **Plan C completo guardado en la sección 14**; pendiente de ejecución).

> **PLAN C (ejecutado 2026-11-05):** UI/UX premium + sala 3D + desafíos/calibración.
> La spec original está en la **sección 14** y el estado final en la **sección 15**.

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

### Sandbox page
- `web/sandbox.html` + `POST /api/sandbox/probe`: corre escritura en root,
  lectura de secretos y conexión saliente en el mismo contenedor; muestra
  BLOCKED/ALLOWED. Link en el footer de la landing.

### Deploy y video (hecho)
- VM Vultr: `sao`, `vc2-1c-2gb`, Ubuntu 24.04, `216.128.168.246`.
- URL: https://agent-rush.216-128-168-246.sslip.io/
- HTTPS con Caddy en contenedor + systemd para la app.
- Video de 48 s con narración TTS: `docs/agent-rush-demo.mp4`.
- `SUBMISSION.md` con el texto para LabLab.

### Pendiente
- Subir el video a YouTube/Loom si el formulario pide URL.
- Enviar el formulario en LabLab (cuenta del usuario).

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
---

## 14. PLAN C — Rediseño completo UI/UX + sala 3D + desafíos (EJECUTADO 2026-11-05 — ver §15)

> **Actualización 2026-11-05:** el plan ya se ejecutó. El detalle de lo hecho,
> la calibración y lo pendiente están en la **sección 15**. El texto de esta
> sección se conserva como la spec original.

> **Estado:** guardado el **2026-11-04** a pedido del usuario para ejecutar al
> volver. Al momento de guardar este plan **no se implementó nada de esta
> sección**. La versión desplegada actual sigue siendo la de la sección 13 y es
> el fallback al que se puede volver.
>
> **Para ejecutar:** el usuario debe decir **“ejecutar plan c”** (y estar en un
> agente de implementación). No arrancar antes de esa orden.

### 14.0 Contexto de la versión que está viva hoy (fallback)

- App pública: https://agent-rush.216-128-168-246.sslip.io/
- Contención: https://agent-rush.216-128-168-246.sslip.io/sandbox.html
- Repo: https://github.com/JoseMota0190/agent-rush (MIT)
- Video actual: `docs/agent-rush-demo.mp4` (48 s, TTS, UI vieja).
- VM Vultr: São Paulo, `vc2-1c-2gb`, Ubuntu 24.04, IP `216.128.168.246`.
- Deploy: `deploy/deploy.py` + `deploy/setup.sh` (systemd + Caddy contenedor,
  HTTPS con `sslip.io`).
- Backend actual: `run_server.py` (stdlib, SSE), `run_engine.py` (Vultr real +
  Docker), SQLite `data/agent_rush.db`.
- UI actual: landing con hero + cómo funciona + modos + catálogo + leaderboards;
  juego 3D + rail; wizard de 2 pasos; `sandbox.html`.
- Salas actuales (simples, a rediseñar):
  1. `THE LOGS` — hash entre señuelos.
  2. `MEMORY LEAK` — suma + SHA-256.
  3. `FIREWALL` — HMAC-SHA256.
- Leaderboard actual: 3 runs spectator + 1 orchestrator (datos reales).
- Notas operativas:
  - Local en Windows: `python run_server.py --port 8010 --no-open` porque Docker
    Desktop ocupa `0.0.0.0:8000`.
  - En la VM: 8000 detrás de Caddy.
  - `.env` local con `VULTR_API_KEY` (general, IPv4) y
    `VULTR_INFERENCE_API_KEY` (suscripción). `.env` está gitignoreado.
  - La API key general tiene ACL IPv6 restringido; el deploy fuerza IPv4.
  - Rotar la key de Inference después del hackathon (quedó visible en capturas).

### 14.1 Decisiones cerradas del usuario (2026-11-04)

1. **Opción C completa:** UI/UX premium + desafíos nuevos + calibración + sala 3D
   mejorada. No se congela nada.
2. **Se autoriza** el cambio mínimo de backend para mandar el código en el evento
   CODE (payload del coder/patch) y para las definiciones de desafíos.
3. **La landing usa escena 3D real** en el hero (no avatares SVG genéricos). Los
   recursos son los de la escena existente; nada de fotos/stock.
4. **Nada congelado:** se rediseñan las 3 salas y se calibra.
5. **La sala 3D se mejora completa** con la spec de environment (secciones
   14.2.B), sin reconstruirla desde cero.
6. **Deadline:** domingo. Objetivo: **submission el sábado a la noche**; domingo
   solo buffer.
7. **Ritmo:** el usuario espera ejecución rápida (el agente ya hizo en ~25 min lo
   que se estimó en días). Estimación acordada: **2,5–3 días de calendario**,
   ~20–28 h efectivas con paralelización. No prometer “todo en una hora”; el
   cuello es QA visual, runs reales, deploy y video.

### 14.2 Specs originales del usuario (TAL CUAL, sin resumir)

#### 14.2.A Frontend UI/UX Redesign (spec completa)

```text
# AGENT RUSH — Frontend UI/UX Redesign

## Instrucciones generales

Antes de modificar código:

- Inspecciona la estructura del proyecto, las rutas, componentes y estilos existentes.
- Identifica qué componentes pueden reutilizarse.
- Revisa las funcionalidades actuales y evita romperlas.
- Conserva la integración existente con Vultr, los modelos, los agentes y el motor de juego.
- No modifiques backend, APIs, lógica de ejecución, sandbox ni sistema de validación.
- No reemplaces funcionalidades existentes por simulaciones o datos ficticios.
- No elimines componentes sin justificarlo.
- Mantén compatibilidad con los idiomas español e inglés.

La dirección visual debe ser **Premium Sci-Fi Gaming Interface**: una mezcla de centro de operaciones futurista, videojuego de estrategia y laboratorio tecnológico.

### Identidad visual global

Paleta:

- Background: #050B14
- Secondary background: #091421
- Panels: #0C1928
- Borders: #17344B
- Orange: #FFAD25 (acciones principales y Strategist)
- Cyan: #26C9FF (Coder y tecnología)
- Purple: #B66AFF (Auditor)
- Green: #13DB8C (éxito y validación)

Tipografía:
- Títulos: Orbitron o alternativa futurista equivalente.
- Interfaz: Inter.
- Código y logs: JetBrains Mono.

No utilizar neones intensos en todos los elementos. Reservar los efectos luminosos para interacciones importantes, estados activos y resultados.

Mantener consistencia en botones, bordes, radios, espaciados, iconografía y animaciones.

---

# PROMPT 1 — LANDING PAGE

Rediseña la página principal de AGENT RUSH para transmitir una experiencia tecnológica premium.

### Objetivo

Que un visitante entienda rápidamente qué es AGENT RUSH, cómo funciona y quiera entrar a jugar.

### Hero section

Crear una sección principal cinematográfica que incluya:

- Logo AGENT RUSH.
- Subtítulo: "THREE AGENTS. ONE MISSION. ZERO TRUST."
- Descripción breve del desafío.
- Representación visual de los tres agentes.
- Botón principal: ENTER THE GAME.
- Acceso secundario a HOW IT WORKS.

La representación de los agentes debe respetar los colores y roles existentes:
- Strategist: naranja.
- Coder: cyan.
- Auditor: violeta.

Utilizar los recursos 3D existentes siempre que sea posible. No incorporar fotografías genéricas de robots ni imágenes de stock.

### How it works

Crear una sección con tres tarjetas horizontales:

1. STRATEGIST — Plans the solution and coordinates the mission.
2. CODER — Writes and executes code inside the sandbox.
3. AUDITOR — Reviews the code and validates the results.

Cada tarjeta debe tener iconografía propia, color identificativo y una pequeña interacción hover.

### Game modes

Presentar los dos modos disponibles:

- SPECTATOR MODE: Observe autonomous agents solving challenges.
- ORCHESTRATOR MODE: Take control and coordinate the agents.

Mostrar ambos como tarjetas diferenciadas, con una descripción y acceso a la selección correspondiente.

### Footer

Incluir referencias a Vultr, LabLab y tecnologías utilizadas, respetando la información y enlaces existentes.

### Diseño y comportamiento

- Landing oscura y cinematográfica.
- Jerarquía visual clara.
- Animaciones suaves.
- CTA naranja como protagonista.
- Evitar bloques excesivamente largos de texto.
- Mantener ES/EN.
- Adaptar correctamente a escritorio y móvil.

No modificar la lógica de navegación ni el funcionamiento de los botones existentes.

---

# PROMPT 2 — GAME ROOM / ESCAPE ROOM

Esta es la pantalla más importante del proyecto. Debe convertirse en el elemento visual protagonista de AGENT RUSH.

### Objetivo principal

Crear una experiencia donde el usuario pueda observar a los tres agentes trabajando dentro de una habitación de escape y, simultáneamente, seguir sus conversaciones y actividades en tiempo real.

### Distribución de pantalla

En escritorio, utilizar una distribución de dos columnas:

- 50% del ancho: Escape Room 3D.
- 50% del ancho: Agent Logs.

Ambas secciones deben permanecer visibles simultáneamente.

No utilizar un panel de logs que cubra la habitación. Debe existir una separación clara entre ambas áreas.

### Lado izquierdo — Escape Room

Mantener la habitación 3D existente.

Mejorar:

- Iluminación ambiental.
- Profundidad y contraste.
- Visibilidad de los tres puestos.
- Pantallas y elementos holográficos.
- Integración visual de la mesa central.
- Identificación de cada agente.

Los colores de los puestos deben mantenerse:

- Strategist: naranja.
- Coder: cyan.
- Auditor: violeta.

Agregar pequeñas animaciones visuales vinculadas al estado actual de cada agente, utilizando los estados reales disponibles.

La mesa central puede funcionar como representación visual del trabajo compartido.

La puerta de escape debe estar integrada en la habitación y representar visualmente el objetivo de la misión.

### Lado derecho — Agent Logs

Diseñar un panel de actividad compacto, profesional y legible.

Encabezado:
- AGENT LOGS.
- Indicador LIVE.
- Estado de la misión.

Agregar filtros:

- ALL
- CHAT
- CODE
- EXECUTION
- AUDIT

Cada evento debe mostrar:

- Identificador del agente o sistema.
- Color correspondiente.
- Timestamp.
- Mensaje o descripción.
- Indicador de estado.

### Tipos de eventos

CHAT:
Mensajes operativos entre Strategist, Coder y Auditor.

CODE:
Archivos generados y modificaciones de código. Mostrar un pequeño resumen y permitir expandir el código completo.

EXECUTION:
Comandos ejecutados, resultados, errores y salida del sandbox.

AUDIT:
Pruebas realizadas, observaciones, validaciones y aprobaciones o rechazos.

ALL:
Mostrar todos los eventos cronológicamente.

No mostrar bloques completos de código permanentemente. Utilizar componentes expandibles para mantener el panel limpio.

### Comportamiento del panel

- Scroll independiente.
- Nuevos eventos visibles sin desplazar toda la página.
- Diferenciación visual de los agentes.
- Animaciones discretas al recibir nuevos eventos.
- Mensajes compactos.
- Posibilidad de consultar los detalles del código y de las ejecuciones.

### Barra superior

Mantener:

- Logo AGENT RUSH.
- Modo actual.
- Indicador de energía.
- Estado de conexión de Vultr Sandbox.
- Selector ES/EN.
- Acceso al menú correspondiente.

### Estados de misión

Preparación:
READY TO ESCAPE.

Ejecución:
MISSION ACTIVE.

Validación:
AUDIT IN PROGRESS.

Completado:
ESCAPE UNLOCKED.

Los estados deben reflejar la información real disponible. No inventar resultados ni mostrar una misión completada antes de su validación.

### Responsive

En escritorio, mantener la distribución 50/50.

En tablet y móvil, utilizar vistas adaptativas o controles para alternar entre habitación y logs. No comprimir la sala hasta hacer invisibles los agentes.

No modificar la lógica de ejecución, los agentes ni la conexión con Vultr Sandbox.

---

# PROMPT 3 — MODE SELECTION / MODEL CONFIGURATION

Rediseñar la pantalla o modal de selección de modos y modelos.

### Objetivo

Que el usuario entienda qué experiencia va a iniciar y pueda configurar los agentes sin sentirse frente a un formulario técnico genérico.

### Selección de modo

Mostrar dos tarjetas principales:

SPECTATOR MODE
- Autonomous experience.
- Los agentes toman sus propias decisiones.
- El usuario observa la misión.

ORCHESTRATOR MODE
- Human-in-the-loop experience.
- El usuario puede intervenir y coordinar a los agentes.
- Presentar claramente las opciones de control existentes.

Cada tarjeta debe incluir:
- Icono.
- Título.
- Descripción.
- Indicador de selección.
- Estado hover y active.

### Selección de modelos

Presentar tres tarjetas diferenciadas:

STRATEGIST — Orange.

CODER — Cyan.

AUDITOR — Purple.

Cada tarjeta debe mostrar:
- Rol del agente.
- Modelo seleccionado.
- Proveedor.
- Descripción breve del rol.
- Selector de modelos disponible.

Mantener los modelos, proveedores y opciones que ya existen en el proyecto. No inventar modelos ni modificar las conexiones.

### Diseño

- Fondo oscuro.
- Tarjetas ligeramente elevadas.
- Selección activa claramente visible.
- Acentos de color individuales.
- Botones consistentes con la identidad de AGENT RUSH.

Botón principal: START MISSION.

Botón secundario: BACK.

El usuario debe poder identificar fácilmente qué modelo está asignado a cada agente antes de iniciar.

Mantener la integración existente y la selección bilingüe.

---

# PROMPT 4 — RESPONSIVE DESIGN & FINAL POLISH

Realizar una revisión visual integral de todas las páginas después de implementar los cambios anteriores.

### Escritorio

Probar especialmente resoluciones:
- 1920 × 1080.
- 1600 × 900.
- 1366 × 768.

Asegurar que:

- No aparezcan scrollbars horizontales innecesarias.
- No se recorten componentes.
- La sala 3D conserve proporciones.
- Los logs sean legibles.
- Los botones estén correctamente alineados.
- La navegación sea consistente.

### Tablet y móvil

Adaptar:
- Landing.
- Tarjetas de agentes.
- Selección de modos.
- Selección de modelos.
- Sala de juego.
- Logs.

No intentar mantener dos columnas cuando el ancho no permite una lectura cómoda.

### Microinteracciones

Incorporar:

- Hover en tarjetas.
- Transiciones entre estados.
- Indicadores de carga.
- Feedback visual al pulsar botones.
- Efectos luminosos discretos.
- Animaciones de actividad de los agentes.

Evitar animaciones excesivas que afecten al rendimiento del entorno 3D.

### Revisión de coherencia

Verificar:

- Paleta de colores consistente.
- Tipografías consistentes.
- Mismo sistema de botones.
- Mismos estilos de tarjetas.
- Correcta jerarquía visual.
- Consistencia ES/EN.
- Ausencia de textos desbordados.
- Ausencia de errores visuales.

### Restricciones finales

No modificar funcionalidades existentes.

No eliminar componentes funcionales.

No reemplazar datos reales por información ficticia.

No alterar la lógica de los agentes, API, sandbox, ejecución, validación ni HMAC Referee.

Antes de finalizar, presentar un resumen de los archivos modificados, las mejoras implementadas y cualquier problema que no se haya podido resolver.
```

#### 14.2.B Escape Room Environment Redesign (spec completa)

> **Nota sobre el final del texto original:** la spec del usuario se corta en
> `- Inspeccionar primero cómo`. Se interpreta como
> **“Inspeccionar primero cómo está construida la escena actual”**. La escena ya
> está inspeccionada: `web/scene.js`, `W=15, D=11, H=4.8`, pared de fondo
> `z=-5.5`, 3 robots, mesa central, puerta al fondo, luces.

```text
# AGENT RUSH — ESCAPE ROOM ENVIRONMENT REDESIGN

Quiero mejorar visualmente la habitación 3D de AGENT RUSH para que transmita claramente la sensación de estar dentro de una auténtica sala de escape futurista.

**IMPORTANTE:** No quiero reconstruir la escena desde cero. Quiero mejorar la habitación que ya existe, conservando su composición, sus tres agentes, sus puestos de trabajo y la mesa central.

## 1. Concepto visual

Transformar el entorno actual en una habitación cerrada de escape tecnológico.

La ambientación debe combinar:
- Escape room futurista.
- Laboratorio tecnológico experimental.
- Sala de seguridad de alta tecnología.
- Estética cyberpunk industrial.

Debe sentirse como un espacio físico cerrado, diseñado para mantener a los participantes dentro hasta completar una misión.

No debe parecer una oficina, un centro de servidores convencional ni una sala de reuniones.

## 2. Elementos arquitectónicos

Mejorar el entorno existente incorporando elementos sencillos pero reconocibles:

**Paredes**
- Paneles metálicos industriales.
- Estructuras reforzadas.
- Juntas y divisiones visibles.
- Conductos y pequeñas rejillas de ventilación.
- Iluminación ambiental integrada en las paredes.

**Puerta de escape**
- Incorporar una puerta blindada claramente visible al fondo o en uno de los laterales.
- Utilizar un sistema de bloqueo electrónico.
- Añadir un pequeño panel de acceso o teclado.
- Mostrar un indicador luminoso de LOCKED.
- La puerta debe parecer el objetivo físico de la misión.

No hace falta construir una puerta excesivamente compleja. Debe integrarse naturalmente con la habitación.

**Suelo**
- Conservar el suelo tecnológico actual.
- Mejorar las líneas de perspectiva y la sensación de profundidad.
- Incorporar detalles industriales discretos.

## 3. Señalización de la hackatón

Incorporar carteles físicos luminosos con la identidad visual de AGENT RUSH y Vultr.

Mantener los colores:

- Naranja: AGENT RUSH.
- Cyan: VULTR SANDBOX.
- Violeta: identificación del Auditor.
- Verde: estados de éxito y seguridad.

Agregar algunos letreros ambientales como:

- VULTR SANDBOX.
- AGENT RUSH.
- RESTRICTED AREA.
- SECURITY ZONE.
- ESCAPE PROTOCOL.
- AUTHORIZED ACCESS ONLY.

Los carteles deben parecer señalización real de la habitación, integrados en las paredes y estructuras, no elementos flotantes colocados aleatoriamente.

## 4. Los tres agentes

Conservar exactamente los tres puestos actuales:

**STRATEGIST**
- Iluminación naranja.
- Identificación visual clara.
- Monitor y estación de trabajo.

**CODER**
- Iluminación cyan.
- Identificación visual clara.
- Monitor y estación de trabajo.

**AUDITOR**
- Iluminación violeta.
- Identificación visual clara.
- Monitor y estación de trabajo.

No cambiar sus posiciones ni dimensiones sin una razón importante.

Los tres deben continuar siendo los protagonistas de la escena.

## 5. Mesa central

Conservar la mesa circular actual.

Mejorar ligeramente:
- Iluminación perimetral.
- Superficie tecnológica.
- Reflejos.
- Detalles holográficos.
- Integración con los tres puestos de trabajo.

La mesa debe funcionar como centro de coordinación de los agentes.

Evitar agregar demasiados objetos que dificulten la visualización de los personajes.

## 6. Iluminación y atmósfera

Quiero una iluminación más cinematográfica:

- Ambiente predominantemente oscuro.
- Luz azul y cyan como iluminación general.
- Reflejos naranjas y violetas procedentes de los puestos.
- Luces de emergencia rojas muy discretas cerca de la puerta.
- Sombras que refuercen la sensación de profundidad.
- Materiales metálicos con reflejos controlados.

No utilizar neón excesivo ni iluminar todos los objetos con la misma intensidad.

## 7. Estados visuales de la habitación

Preparar el entorno para que pueda representar diferentes estados de la misión cuando existan los eventos correspondientes:

**READY**
- Puerta bloqueada.
- Iluminación estable.
- Los agentes esperan instrucciones.

**MISSION ACTIVE**
- Puestos de trabajo iluminados.
- Actividad visual en los monitores.
- Mesa central activa.
- Indicadores de misión en funcionamiento.

**ESCAPE UNLOCKED**
- Indicador de puerta desbloqueada en verde.
- Luces de emergencia que pasan a estado seguro.
- Animación de apertura de la puerta, cuando sea posible.

Utilizar los estados reales de la aplicación. No simular una finalización antes de que el sistema la confirme.

## 8. Restricciones técnicas y de diseño

- Inspeccionar primero cómo [TEXTO ORIGINAL CORTADO]
```

### 14.3 Principios de ejecución (obligatorios)

1. **No romper lo que funciona.** Antes de empezar: commit/tag del estado actual
   y backup de `web/`, `run_server.py`, `run_engine.py`, `deploy/`.
2. **No reemplazar datos reales por mocks.** Todo estado de misión, log, energía,
   líder y validación sale de eventos reales.
3. **No cambiar la arquitectura:** APIs/SSE/sandbox/referee/agentes siguen igual.
   Cambios de backend autorizados y acotados:
   - `code` (y opcionalmente `patch`) en el evento del Coder.
   - Definiciones/artefactos de desafíos.
   - Versión de desafío en `runs`/leaderboard.
4. **ES/EN:** toda cadena nueva con par de claves; probar ambos idiomas.
5. **No tocar `vendor/three.module.js` ni `referee.py`** salvo que sea
   imprescindible y esté justificado.
6. **Escena 3D:** mejorar la existente, no reconstruir; conservar posiciones,
   dimensiones, robots, mesa y cámaras.
7. **Performance:** medir draw calls, sombras y FPS; SwiftShader/headless es
   lento; priorizar legibilidad sobre cantidad de objetos.
8. **Deploy controlado:** probar local, luego copiar a la VM y reiniciar; si
   algo falla, revertir al commit anterior. No dejar la URL pública rota.
9. **Checkpoints:** no avanzar al siguiente bloque sin un run real y sin captura
   a 1366/1600/1920.
10. **Cut lines antes que incumplir el submission.**

### 14.4 Arquitectura de la implementación

#### 14.4.1 Design system

- Variables CSS en `web/styles.css`:
  - `--bg:#050B14`, `--panel:#0C1928`, `--panel-2:#091421`,
    `--line:#17344B`, `--orange:#FFAD25`, `--cyan:#26C9FF`,
    `--violet:#B66AFF`, `--green:#13DB8C`.
  - Mantener aliases viejos (`--amber`, `--line-hot`, etc.) para no romper
    componentes existentes; mapearlos a los nuevos.
- Fuentes locales (woff2 en `web/fonts/`):
  - Orbitron (700/800) para títulos/brand.
  - Inter (400/500/600/700) para UI.
  - JetBrains Mono (400/500/700) para logs/código.
  - `@font-face` con `font-display: swap`; fallback a Bahnschrift/Consolas.
- Componentes: botón primario naranja, secundario con borde cyan/neutro, cards
  con borde `--line`, radio 10–14 px, hover con glow suave (no neón global).
- Iconografía: SVG inline/monocromo por rol; sin librerías nuevas.

#### 14.4.2 Landing (`web/index.html` + `styles.css` + posible `hero-scene.js`)

- Hero cinematográfico:
  - Fondo/escena 3D real reutilizando `web/scene.js` en un modo `hero` (cámara
    close-up de los 3 puestos + mesa; sin labels/consolas).
  - Alternativa de performance: render estático de la misma escena (nunca stock).
  - Logo AGENT RUSH, subtítulo exacto **“THREE AGENTS. ONE MISSION. ZERO TRUST.”**.
  - Descripción breve.
  - CTA naranja **ENTER THE GAME** + secundario **HOW IT WORKS** (ancla).
  - Representación de los 3 agentes con colores/roles; puede ser la escena 3D o
    los avatares existentes como refuerzo.
- Cómo funciona: 3 cards horizontales con títulos/copy exactos de la spec,
  icono propio, color del rol, hover.
- Modos: 2 cards con copy de la spec; CTAs abren el wizard existente (no cambiar
  la navegación).
- Footer: Vultr, LabLab, tecnologías; conservar links; agregar Sandbox.
- Responsive: 1 columna en móvil; hero sin overflow; texto legible.

#### 14.4.3 Wizard (`web/wizard.js` + `index.html` + `styles.css` + `i18n.js`)

- Mantener el flujo real: `#enter-game` → paso 1 (modo) → paso 2 (modelos);
  tarjetas de modo → paso 2 directo; submit explícito.
- Rediseñar:
  - Dos cards de modo con icono, título, descripción, estado selected/hover.
  - Tres cards de agente (STRATEGIST naranja, CODER cyan, AUDITOR violeta):
    rol, modelo seleccionado, proveedor **Vultr Serverless Inference**,
    descripción breve, selector de modelos existente.
  - Botón principal **START MISSION**; secundario **BACK**.
- Conservar `sessionStorage`, POST `/api/agents`, validación de 3 modelos,
  presets y autoselección actual.
- ES/EN completo; no inventar modelos/proveedores.

#### 14.4.4 Juego 50/50 (`web/game.html` + `styles.css` + `app.js`)

- Grid: 50% escena / 50% logs en desktop (`1366`+). El rail actual
  (`--rail-w: clamp(380px,30vw,470px)`) pasa a `50%` o `1fr 1fr`.
- La escena conserva proporción; ajustar cámara/aspecto en `scene.js` si hace
  falta. No tapar la sala con logs.
- Topbar intacta: logo, modo, energía, sandbox, ES/EN, salida. Agregar acceso a
  menú si hace falta sin romper.
- Logs:
  - Header: **AGENT LOGS**, badge **LIVE**, estado de misión.
  - Filtros: ALL / CHAT / CODE / EXECUTION / AUDIT.
  - Evento: agente/sistema con color, timestamp, mensaje, badge de estado.
  - CODE: resumen + `<details>` expandible con código real (payload autorizado);
    no mostrar código permanentemente.
  - EXECUTION: stdout/stderr y exit code en expandible.
  - AUDIT: referee/auditor, validaciones y aprobaciones.
  - Scroll independiente; auto-scroll solo si el usuario está al final.
  - Animación discreta de entrada; contador de eventos; tokens.
- Estados de misión (derivados de eventos reales):
  - `READY TO ESCAPE` (idle).
  - `MISSION ACTIVE` (run_started / challenge / agente trabajando).
  - `AUDIT IN PROGRESS` (auditor/referee/sandbox de validación).
  - `ESCAPE UNLOCKED` (run_completed 3/3).
  - `RUN FAILED`/`DISQUALIFIED`/`ABORTED` si aplica.
- Responsive: en tablet/móvil tabs **ROOM / AGENT LOGS**; no comprimir la sala.

#### 14.4.5 Sala 3D (`web/scene.js` + `app.js`)

Conservar composición actual. Agregar/ajustar:

- **Paredes:** paneles metálicos con juntas, refuerzos, conductos y rejillas;
  tiras de luz integradas. Reutilizar texturas canvas/procedurales.
- **Puerta:** blindada en la pared de fondo (donde ya está), keypad/panel,
  LED **LOCKED** rojo → **UNLOCKED** verde, marco reforzado, luces de emergencia
  rojas cerca; animación de apertura si el rendimiento lo permite.
- **Piso:** conservar grid; mejorar líneas de perspectiva/placas industriales
  discretas.
- **Señalización:** carteles canvas integrados en paredes/estructuras, 0.2 m por
  delante para evitar z-fighting: AGENT RUSH (naranja), VULTR SANDBOX (cyan),
  RESTRICTED AREA (rojo/ámbar), SECURITY ZONE (cyan), ESCAPE PROTOCOL (ámbar),
  AUTHORIZED ACCESS ONLY (verde). Nada flotante/aleatorio.
- **Agentes:** mismas posiciones/dimensiones; monitores con actividad según
  `setBotState`; colores intactos.
- **Mesa:** anillo perimetral, superficie, reflejos y detalles holográficos;
  intensificarse en `ACTIVE`.
- **Iluminación:** ambiente oscuro azul/cyan; acentos naranja/violeta; rojo
  discreto en puerta; sombras; metales controlados; sin neón global.
- **API nueva:** `setEnvironmentState("ready"|"active"|"unlocked")` exportada
  desde `scene.js`.
  - `startRun` → `active`.
  - `room_solved`/auditor → actividad de auditoría.
  - `run_completed` → `unlocked` (LED verde, emergencia segura, apertura).
  - salida/reset → `ready`.
  - No simular estados.
- **Hero landing:** modo `hero` de la misma escena o `hero-scene.js` que reuse
  geometrías/materiales; cámara cinematográfica; sin interacción pesada.
- **Performance:** limitar pixel ratio, sombras 1024, reutilizar materiales,
  instancing para paneles/rejillas; probar headless/SwiftShader.

#### 14.4.6 Backend mínimo autorizado

- `run_engine.py`:
  - Emitir en el evento `agent` del Coder (y Auditor patch) el campo `code`
    (string) y opcional `lines`, `filename` (`roomN.py`). No cambiar la lógica.
  - Definiciones de desafíos nuevas (artefactos, prompts, validación).
  - No tocar la arquitectura de `EventBus`, SSE, `RunManager`, sandbox ni tokens.
- `run_server.py`:
  - No cambiar rutas/contratos existentes.
  - Agregar `challenge_version` a la tabla `runs` y filtrar leaderboard por
    versión actual; o resetear `data/agent_rush.db` tras el cambio de desafíos.
  - Mantener `/api/sandbox/probe`, `/api/runs`, SSE, abort.
- `referee.py`: no tocar.
- Sandbox: mismas flags; no relajar contención.

#### 14.4.7 Desafíos nuevos + calibración

- **Sala 1 — THE LOGS (fácil-medio):** `auth.log` + `auth.log.1` con decenas de
  líneas, hashes señuelo, entradas corruptas y una correlación con checksum/
  header. El token válido no se ve a simple vista.
- **Sala 2 — MEMORY LEAK (medio):** módulo Python con bug real + tests; el
  agente corrige código sin tocar tests; casos borde (vacío, negativos, chunks
  grandes, timeout). Éxito = tests pasan + proof.
- **Sala 3 — FIREWALL (difícil):** handshake local `HELLO` → nonce → firma HMAC →
  token, servidor dentro del contenedor (loopback, `--network none`), trampas
  (nonce cambiante, respuesta señuelo), intentos limitados.
- Intentos por sala: 3 (alinear UI); pistas; tiempo y tokens visibles.
- Dificultad “Normal” para la demo; “Hard” opcional.
- Calibración:
  - Recomendados (deepseek + glm-5.3-flash + minimax) × 10 runs: 90–100% éxito,
    ≤3 intentos, ≤20k tokens, ≤90 s.
  - Alternativos × 5 runs: 60–80%.
  - Débiles × 3 runs: fallo claro, servidor estable.
  - Medir éxito/intentos/tokens/tiempo; ajustar señuelos, casos borde, pasos,
    intentos y pistas.
- Validar código con `compile()` antes del sandbox; retry informado.
- Presupuesto: 100k por run es suficiente (runs actuales 4–6k). Mantener tope
  por llamada ~1.200–1.500; agregar rate limit público.
- Leaderboard: versionar/resetear; poblar con 3–5 runs reales nuevas.

#### 14.4.8 Video / deploy / submission

- Regrabar video después de UI/sala/desafíos: landing, wizard, run real 3/3,
  logs/estados, contención, leaderboard. <3 min (actual 48 s). TTS o voz humana.
- Actualizar capturas y README; `SUBMISSION.md` con URL/repo/video.
- Deploy: probar local, copiar a la VM, reiniciar systemd; HTTPS con Caddy;
  verificar desde otra red. Rollback al commit anterior si falla.
- Mantener la URL pública actual hasta el QA final.

### 14.5 Orden de ejecución y checkpoints

1. **Backup + tag + design tokens + fuentes** (1–2 h).
2. **Landing** (hero 3D, cards, modos, footer) + wizard (4–6 h). Checkpoint:
   landing/wizard en local, ES/EN, sin overflow.
3. **Juego 50/50 + logs/filtros/estados + payload code** (6–8 h). Checkpoint:
   run real local, filtros y código expandible.
4. **Sala 3D** (paredes/puerta/carteles/luces/estados) (6–8 h). Checkpoint:
   captura 1366/1600/1920 + estados reales.
5. **Desafíos + calibración + leaderboard** (6–8 h). Checkpoint: 3/3 real,
   matriz de modelos, DB/version.
6. **QA responsive + microinteracciones + fixes** (4–6 h).
7. **Deploy + video + docs/submission** (3–5 h). Checkpoint: URL pública con
   la versión nueva y submission enviado.

Calendario objetivo: **jueves + viernes + sábado**, submission sábado noche;
domingo buffer. Estimación: 2,5–3 días, ~20–28 h efectivas con paralelización
(landing/wizard, desafíos/calibración y tests en subagentes).

### 14.6 Cut lines (en orden)

1. Hero 3D inestable/pesado → render estático de la misma escena.
2. Apertura animada de puerta complica → LED verde + estado UNLOCKED.
3. Paneles/rejillas suben draw calls → instancing o menos detalle; prioridad a
   los agentes.
4. Desafíos nuevos no pasan calibración el viernes noche → se mantienen las 3
   salas actuales; se prioriza UI/QA/video.
5. 50/50 rompe la escena a 1366 → rail 45/55 o ajustar cámara antes que comprimir.
6. Cualquier bloqueo el sábado → revertir al commit anterior y submitir.

### 14.7 Criterios de aceptación

- [ ] Landing: hero 3D, subtítulo exacto, 3 cards, 2 modos, footer Vultr/LabLab,
      ES/EN, desktop/móvil sin overflow.
- [ ] Wizard: modo + 3 cards de agente con modelo/proveedor/rol; START MISSION/
      BACK; selección real; ES/EN.
- [ ] Juego 50/50; escena y logs visibles simultáneamente; tabs en móvil.
- [ ] Logs: ALL/CHAT/CODE/EXECUTION/AUDIT; colores; timestamps; código
      expandible real; stdout/stderr; audit; scroll independiente.
- [ ] Estados reales READY/MISSION ACTIVE/AUDIT IN PROGRESS/ESCAPE UNLOCKED;
      nunca completar antes de `run_completed`.
- [ ] Sala 3D: paredes, puerta/keypad/LED, carteles, piso, mesa, luces,
      estados; agentes/posiciones intactos.
- [ ] Run real 3/3 en local y en la VM; tokens/energía reales.
- [ ] Leaderboard real versionado/reseteado; sin datos ficticios.
- [ ] QA 1920/1600/1366/tablet/móvil; sin scroll horizontal; sin pageerrors.
- [ ] Video regrabado <3 min; README/SUBMISSION actualizados; deploy HTTPS OK.
- [ ] ES/EN completos (claves nuevas en ambos diccionarios).

### 14.8 Comandos y gotchas para la ejecución

```bash
# local (Windows: Docker Desktop ocupa 8000)
python run_server.py --port 8010 --no-open
# tests de sintaxis
python -m py_compile run_server.py run_engine.py deploy/deploy.py
node --check web/app.js web/wizard.js web/i18n.js web/catalog.js web/leaderboard.js
# deploy a la VM actual
python deploy/deploy.py --region sao --plan vc2-1c-2gb
# o copia incremental + restart
# scp -i %USERPROFILE%/.ssh/agent_rush run_server.py run_engine.py root@IP:/opt/agent-rush/
# ssh -i ... root@IP "systemctl restart agent-rush"
```

- No reconstruir la VM antes del domingo (cambia la IP y la URL sslip.io).
- La key general de Vultr tiene ACL IPv6 restringido; forzar IPv4 en scripts.
- Docker/SSE: probar que Caddy no bufferee `/api/runs/*/events`.
- `data/agent_rush.db` no se commitea; si se cambia la versión de desafíos,
  resetear/versionar.
- `web/scene.js`: si se toca, subir `?v=` del import en `app.js` y probar
  headless con `--use-gl=swiftshader` ventana chica.
- Z-fighting: carteles 0.2 m delante de paredes.
- Texto canvas: auto-fit con `measureText`.
- Mantener el fallback de la sección 13 (commit/tag) y no romper la URL pública.

### 14.9 Estado al guardar este plan

- **No ejecutado.** Ninguna línea de esta sección fue implementada.
- El plan queda guardado en `AGENTS.md` para que al volver el usuario diga
  **“ejecutar plan c”** y se arranque por el backup/tag y el design system.
- La app pública actual sigue funcionando con la UI/salas de la sección 13.

---

## 15. Sesión 2026-11-05 — Plan C ejecutado (UI/3D + desafíos v2 + calibración)

### 15.1 Estado
- Plan C completo en **local**; pendiente deploy a la URL pública, video y submission.
- Fallback: tag `pre-plan-c` + backup zip en
  `C:\Users\josem\AppData\Local\Temp\opencode\agent-rush-backup\pre-plan-c.zip`.

### 15.2 Frontend / 3D (hecho)
- `web/index.html`, `web/hero.js`, `web/premium.css`: landing cinematográfica con
  hero 3D real, subtítulo exacto, cards de agentes, modos, catálogo, leaderboards
  y wizard rediseñado.
- `web/game.html`, `web/app.js`: layout 50/50, **AGENT LOGS** con filtros
  ALL/CHAT/CODE/EXECUTION/AUDIT, código/stdout/stderr expandibles, estados
  READY / MISSION ACTIVE / AUDIT IN PROGRESS / ESCAPE UNLOCKED, tabs móviles,
  IDE, energía real e intentos **1/3**.
- `web/scene.js`: sala mejorada (paredes, puerta/keypad/LED, carteles, luces,
  estados); `app.js` y `hero.js` importan `scene.js?v=43`.
- `web/i18n.js`: claves ES/EN nuevas; sin claves crudas en landing/game.
- `web/fonts/`: Orbitron, Inter y JetBrains Mono locales.

### 15.3 Backend / desafíos v2
- `CHALLENGE_VERSION = "plan-c-v2"`; columna `challenge_version` en `runs` y
  leaderboard filtrado por versión (las runs viejas quedan ocultas).
- **Sala 1:** logs rotados + manifiesto; el ticket válido ahora siempre está atado
  a `active_session` (fix de fairness) y varios señuelos comparten la sesión.
- **Sala 2:** modo `module`: el harness escribe tests + módulo; el agente devuelve
  solo `chunk_sum`. Tres intentos.
- **Sala 3:** loopback TCP `HELLO → NONCE → HMAC → TOKEN/DECOY`, nonce fresco por
  conexión y lockout tras 3 intentos inválidos.
- 3 intentos por sala, `compile()` antes del sandbox, eventos con
  `attempt/max_attempts` y prompts de patch específicos.
- Vultr: `reasoning_effort=low`; coder/auditor `max_tokens=4000`; strategist 600.
  Evita que los modelos thinking gasten todo el budget en razonamiento.
- Leaderboard: ranking **por modo** (1..n), no global.

### 15.4 Calibración
- Tabla completa y conclusiones: `docs/CALIBRATION_PLAN_C.md`.
- Recomendado (deepseek + glm-5.3-flash + deepseek): **3/3** en mod7/mod8/mod9,
  16.7–41.3 s, 7.1k–15.6k tokens, máximo 3 intentos.
- alt1b (glm-5.3 / deepseek / minimax): 3/3, 22.9 s, 10.8k tokens.
- alt2 (minimax / glm-5.3 / glm-5.3-flash) y qwen3.8-27b ×3: 3/3.
- alt1 v1 falló la sala 1 por el bug de fairness; corregido en v2.
- Corrida real desde la UI (Playwright, run `76C3CAECBA43`): **ESCAPE UNLOCKED**
  3/3, 10.246 tokens, 31 eventos, sin errores.

### 15.5 QA
- Playwright `qa-plan-c2.js`: landing 1366 con scroll, mobile 390 sin overflow,
  game 1920 en 50/50, tabs móviles, SSE mock con 8 líneas/filtros/expandibles y
  ES/EN. `errors=[]`, `failed=[]`.
- `qa-real-run.js`: run real 3/3, `ESCAPE UNLOCKED`, intentos 1/3, IDE con código,
  sin errores de consola ni overflow horizontal.
- `python -m py_compile run_engine.py run_server.py`; `node --check web/app.js`.

### 15.6 Pendiente (siguiente sesión)
1. Deploy **incremental** a la VM actual (no reconstruir; mantener IP/URL):
   copiar `run_engine.py`, `run_server.py`, `web/` y
   `docs/CALIBRATION_PLAN_C.md`; respaldar `/opt/agent-rush`; reiniciar
   `agent-rush`; verificar HTTPS y leaderboard v2.
2. Regrabar video <3 min con UI/sala/desafíos nuevos; actualizar README,
   `SUBMISSION.md` y capturas.
3. Enviar el submission en LabLab (cuenta del usuario).
4. Opcional: rate limit público.

---

