# Plan de Calibración C — Resultados Reales

> **Nota:** Estas ejecuciones se realizaron contra **Vultr Serverless Inference** real (modelos alojados en Docker local), **no son mocks**. Cada corrida consumió tokens y tiempo real de inferencia.

---

## Tabla de ejecuciones

| Tag | Versión | Modo | Strategist | Coder | Auditor | Salas | Intentos (R1/R2/R3) | Tokens | Segundos | Resultado |
|-----|---------|------|------------|-------|---------|-------|---------------------|--------|----------|-----------|
| mod3 | v1 | spectator | deepseek-v4.1-flash-1017 | glm-5.3-flash | deepseek-v4.1-flash-1017 | 3/3 | 1 / 1 / 1 | 7 221 | 35,0 | ✅ OK |
| mod4 | v1 | spectator | deepseek-v4.1-flash-1017 | glm-5.3-flash | deepseek-v4.1-flash-1017 | 3/3 | 2 / 1 / 1 | 11 464 | 32,0 | ✅ OK |
| mod5 | v1 | spectator | deepseek-v4.1-flash-1017 | glm-5.3-flash | deepseek-v4.1-flash-1017 | 3/3 | 1 / 1 / 1 | 7 518 | 23,4 | ✅ OK |
| mod6 | v1 | orchestrator | deepseek-v4.1-flash-1017 | glm-5.3-flash | deepseek-v4.1-flash-1017 | 3/3 | 1 / 1 / 3 | 16 644 | 56,2 | ✅ OK |
| mod7 | v2 | spectator | deepseek-v4.1-flash-1017 | glm-5.3-flash | deepseek-v4.1-flash-1017 | 3/3 | 1 / 1 / 2 | 11 253 | 41,3 | ✅ OK |
| mod8 | v2 | orchestrator | deepseek-v4.1-flash-1017 | glm-5.3-flash | deepseek-v4.1-flash-1017 | 3/3 | 1 / 1 / 3 | 15 576 | 37,8 | ✅ OK |
| mod9 | v2 | spectator | deepseek-v4.1-flash-1017 | glm-5.3-flash | deepseek-v4.1-flash-1017 | 3/3 | 1 / 1 / 1 | 7 111 | 16,7 | ✅ OK |
| alt1 | v1 | spectator | glm-5.3 | deepseek-v4.1-flash-1017 | minimax-m3.1-flash | 0/3 | 3 / — / — | 9 037 | 15,0 | ❌ Falló sala 1 |
| alt1b | v2 | spectator | glm-5.3 | deepseek-v4.1-flash-1017 | minimax-m3.1-flash | 3/3 | 1 / 1 / 1 | 10 803 | 22,9 | ✅ OK |
| alt2 | v1 | spectator | minimax-m3.1-flash | glm-5.3 | glm-5.3-flash | 3/3 | 2 / 1 / 1 | 10 663 | 26,4 | ✅ OK |
| weak1 | v1 | spectator | qwen3.8-27b | qwen3.8-27b | qwen3.8-27b | 3/3 | 1 / 1 / 1 | 12 699 | 19,4 | ✅ OK |

*Versión inferida del tag: mod7, mod8, mod9, alt1b = **v2** (plan-c-v2); el resto = **v1** (plan-c-v1).*

> **Integración UI:** una corrida real lanzada desde `game.html` con Playwright (run `76C3CAECBA43`) terminó en **ESCAPE UNLOCKED** con 3/3 salas, 10.246 tokens, 31 eventos y sin errores de consola ni requests fallidos.

---

## Conclusiones

1. **Escuadrón recomendado** — `deepseek-v4.1-flash-1017` (strategist) + `glm-5.3-flash` (coder) + `deepseek-v4.1-flash-1017` (auditor) — resolvió **3/3 en todas las corridas v2** (mod7, mod8, mod9).
   - Mejor tiempo: **~16,7 s** (mod9, modo spectator).
   - Rango de tokens: **7,1 k – 15,6 k**.
   - Máximo de reintentos por sala: **3** (sala 3 en mod6 y mod8).

2. **Escuadrón alternativo alt1b** (mismos modelos, roles rotados: glm-5.3 / deepseek / minimax) también logró **3/3 en v2** (22,9 s, 10,8 k tokens).

3. **alt1 (v1)** falló en la sala 1 tras 3 intentos. El ticket válido podía aparecer en una línea con una sesión distinta a la activa, así que un plan que filtrara por sesión podía descartarlo. Se corrigió en v2: el ticket ganador siempre está atado a la sesión activa (y varios señuelos comparten esa sesión, así que encontrar la sesión no alcanza).

4. **alt2** (minimax + glm-5.3 + glm-5.3-flash) y **weak1** (qwen3.8-27b ×3) **también resolvieron 3/3 en v1**. Esto indica que la dificultad del reto **no fue suficiente** para provocar fallo real en un escuadrón «débil»; la calibración v2 endureció la sala 1 (fairness fix) y ajustó parámetros de backend.

---

## Notas de calibración del backend

Dos cambios clave se aplicaron durante la fase para estabilizar el consumo de tokens y latencia:

1. **`reasoning_effort=low`** en todas las llamadas a Vultr. Los modelos «thinking» (deepseek, glm) gastaban todo el budget en razonamiento oculto sin emitir tokens útiles; forzar `low` recorta la cadena de pensamiento y devuelve respuesta accionable.

2. **`max_tokens=4000`** para **coder** y **auditor** (el strategist mantiene 600 para una respuesta breve). Antes, el coder podía gastar todo el budget en razonamiento y el auditor en parches largos; el límite deja espacio para emitir código completo y mantiene soluciones concisas (la sala 2 module-mode ahora pide solo `chunk_sum`).

3. **Room 2 en modo módulo (module-mode)**: el harness escribe los tests + el esqueleto del módulo; el agente solo debe devolver el fragmento `chunk_sum`. Esto reduce superficie de error y tokens.

---

*Documento generado a partir de los 11 JSON de calibración (mod3–mod9, alt1, alt1b, alt2, weak1) y de una corrida de integración real desde la UI.*