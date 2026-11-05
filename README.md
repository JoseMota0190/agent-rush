# AGENT RUSH — Deterministic AI Escape Room

## 🎬 Demo

- **App:** https://agent-rush.216-128-168-246.sslip.io/
- **Sandbox containment:** https://agent-rush.216-128-168-246.sslip.io/sandbox.html
- **Video (48 s):** [docs/agent-rush-demo.mp4](docs/agent-rush-demo.mp4)
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

- Inglés por defecto, español con el toggle `ES`.
- Los usuarios eligen el modelo de cada agente antes de entrar.
- La energía se mide con los tokens reales de Vultr.
- El leaderboard solo registra runs reales verificadas.
- La página `/sandbox.html` demuestra la contención en vivo.

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

```
web/
├── index.html      # landing: intro, modos, modelos, leaderboards
├── game.html       # juego: canvas 3D + rail de paneles
├── config.html     # redirect a /#modelos (compatibilidad)
├── i18n.js         # diccionarios ES/EN + selector de idioma
├── catalog.js      # catálogo Vultr de solo lectura
├── wizard.js       # flujo modo → modelos → sala
├── leaderboard.js  # fetch + render de los dos leaderboards
├── styles.css      # estética cyberpunk, paneles, landing, energía, wizard
├── scene.js        # sala, mesa holográfica, sillas, 3 robots, cámaras, luces
├── app.js          # modos, compuerta de inicio, log stream, IDE, energía
├── avatars/        # avatares SVG de Strategist, Coder y Auditor
├── assets/         # vultr-logo.svg
├── vendor/three.module.js
├── preview-spectator.png
└── preview-orchestrator.png
```

**Escena 3D:** sala con piso en rejilla, techo con tiras de luz, mesa holográfica
con anillos giratorios, tres robots humanoides **sentados en sillas** con brazos
sobre la mesa, visores emisivos por rol y animación idle/typing/error.

**Modo espectador:** cámara detrás del cristal polarizado (overlay CSS de
reflejos y viñeta) y panel de logs en vivo. El leaderboard vive en la landing,
con una tabla por modo de juego.

**Modo orquestador:** cámara baja con silueta humana en primer plano (POV),
panel de estado de las 3 salas y panel IDE con el código del reto y los botones
`EDIT CODE`, `SEND TO SANDBOX`, `REQUEST HINT`, `SKIP TASK` apilados a la derecha.

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
Docker + Python, levanta la app con systemd y Caddy en un contenedor con HTTPS
(`agent-rush.<ip>.sslip.io`). La app escucha en `127.0.0.1:8000` y Caddy hace el
proxy público.

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

## 🎮 Modos de operación

### Modo Espectador (`python main.py spectator`)
- **Autonomía 100%**: Los agentes deciden solos sin intervención humana
- **Ideal para**: Demostraciones de hackatón, benchmark de modelos
- **Leaderboard**: Registra tiempo, intentos, modelos usados
- **Reproducibilidad**: Mismo flujo cada partida (usando seeds)

### Modo Orquestador (`python main.py orchestrator`)
- **Human-in-the-loop**: Puedes aprobar/modificar código antes de ejecutar
- **Ideal para**: Prototipado rápido, depuración, control fino
- **Interacción**: Panel tipo VS Code para revisar/editar scripts

## 🔒 Seguridad y Contención

### Garantías del Sandbox
- **Efimeridad**: Cada ejecución levanta y destruye contenedor efímero
- **Red aislada**: Sin tráfico saliente (network isolation)
- **Sin variables sensibles**: API keys nunca dentro del contenedor
- **Límites estrictos**: Max 10s ejecución, 256MB memoria máximo
- **Usuario sin privilegios**: Ejecución bajo usuario nodev

### Buenas Prácticas
```python
from tools.vultr_sandbox import sandbox

# Ejecutar código de manera segura
result = sandbox.execute_code(user_code, timeout=10)

# Siempre destruye después
sandbox.tear_down()
```

## 👥 Agentes y Roles

| Agente | Rol | Modelo Recomendado |
|--------|-----|-------------------|
| Strategist | Planificador y estrategia | meta-llama/llama-3.3-70b-instruct:free |
| Coder | Generador de scripts Python | qwen/qwen-2.5-coder-32b:free |
| Auditor | Evaluador y self-healing | deepseek/deepseek-r1:free |

## 📊 Leaderboard y Métricas

El sistema rastrea automáticamente:
- **Escape Time**: Tiempo total en resolver todas las salas
- **Token Efficiency**: Tokens consumidos por modelo
- **Self-Healing Index**: Número de reintentos exitosos antes de solución
- **Cost per Escape**: Costo aproximado (gratis con modelos open-source)

### Tabs del Leaderboard
- **Free Tier Arena**: Ranking con modelos gratuitos only
- **Open Arena (BYOK)**: Ranking general con claves propias
- **Orchestrated vs Autonomous**: Comparativa human vs auto

## 🛠️ Personalización

### Agregar Nuevos Modelos
Edita `config/prompts.py` y actualiza las rutas de enrutamiento en `main.py`.

### Nuevos Puzzles/Salas
1. Agrega descripción en `RoomChallenge` (estado.py)
2. Actualiza los prompts del Strategist para el nuevo tipo de reto
3. Ajusta los patrones de detección de FLAG en el Auditor

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