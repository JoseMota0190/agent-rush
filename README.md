# AI Escape Room - Agent Rush Hackathon

## 🚀 Descripción General
Sistema multi-agente para escape rooms de código donde equipos de IA (Estratega, Coder, Auditor) colaboran o compiten para resolver puzzles de programación en entornos aislados (Sandbox Vultr).

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

Prototipo navegable de los dos modos, sin dependencias ni build step:

```bash
python run_web.py          # abre http://localhost:8000
python run_web.py --no-open
```

- `?mode=orchestrator` abre directamente el modo orquestador (útil para el video).
- Atajos: `1` espectador · `2` orquestador · `espacio` pausa el stream.

```
web/
├── index.html   # estructura de las dos escenas + paneles
├── styles.css   # estética cyberpunk: vidrio, neón, rejilla de suelo
├── app.js       # cambio de modo, log stream, IDE con resaltado, leaderboard
├── preview-spectator.png
└── preview-orchestrator.png
```

**Modo espectador:** sala de observación tras cristal polarizado, tres robots
(Strategist / Coder / Auditor) alrededor de la mesa holográfica, panel de logs
en vivo y leaderboard free tier.

**Modo orquestador:** POV sentado a la mesa, panel de estado de las 3 salas y
panel IDE con el código del reto, botones `EDIT CODE`, `SEND TO SANDBOX`,
`REQUEST HINT`, `SKIP TASK` y los límites del sandbox visibles en el pie.

El front consume `/api/events` (SSE) si el backend está presente; si no,
usa un feed de demo que reproduce el pipeline real (incluido el fallo y el
self-healing) para poder ensayar la demo sin red.

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