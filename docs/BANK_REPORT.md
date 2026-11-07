# AGENT RUSH — Banco v4, scoring y trials (2026-11-07)

## 1. Resumen

- Banco nuevo: **100 desafíos** (33 nivel 1, 34 nivel 2, 33 nivel 3), 8 casos
  ocultos por desafío, selección determinista por seed.
- Scoring nuevo: `scoring.py` implementa `SCORING.md` (0–1000, pesos 150/300/550,
  intentos, tokens, penalizaciones de seguridad y descalificación crítica).
- QA: **26 tests** (`test_bank.py`) y `selftest` de los 100 desafíos.
- 8 simulaciones sintéticas + 2 trials reales en la VM (mejor y peor equipo).
- Leaderboard limpiado (live y local) con backups.

## 2. Bugs encontrados y corregidos

| Bug | Impacto | Fix |
|---|---|---|
| `L2-14` stack overflow en Windows (`0xC00000FD`, 6.7 s) | `selftest` y `build_cases` crasheaban con 3000 paréntesis y 2500 menos unarios | `_calc` reescrito como shunting-yard iterativo; `selftest` pasa en 22 s |
| Harness del banco como `python -c` | `Argument list too long` con 8 casos grandes (`ARG_MAX`) | El trial pasa el harness por stdin (`python -`); la integración debe hacer lo mismo |
| `L3-47` ambiguo | No especificaba la salida de `REL` exitoso; el modelo debía adivinar | Statement ahora define `RELEASED`, `RELEASED … GRANTED …`, `WAIT`, `ALREADY`, `IGNORED`; se agregó caso HAND |
| `CONTAINER_TIMEOUT_S=60` | 8 casos × 10 s = 80 s podían exceder el timeout global | Subido a **90 s** |
| `ARG_MAX` + timeout | El trial “best” fallaba L1-45 y L3-47 por infraestructura | Corregido; resultados finales abajo |

## 3. QA del banco

- `python challenges.py` → **exit 0**, 100 desafíos, determinismo y sensibilidad a
  la seed OK.
- `python -m unittest -v test_bank` → **26 tests OK** (6.9 s).
- Cobertura: registro, 8 casos, determinismo, seed, combinaciones, `public_view`,
  `harness_source` sin salidas esperadas, `grade` (perfecto/incorrecto/timeout/
  malformado/cantidad/normalización), scoring y seguridad.

## 4. 8 simulaciones aleatorias (sintéticas)

No son runs reales de modelos: validan el scoring y las combinaciones. No se
insertaron en el leaderboard.

| Sim | L1 | L2 | L3 | Resueltos | Intentos | Tokens | Perf | Penal | Final | Estado |
|---|---|---|---|---|---|---:|---:|---:|---:|---|
| sim-01 | L1-41 | L2-36 | L3-45 | 3/3 | 1/1/1 | 54.753 | 908 | 85 | 823 | PENALIZED |
| sim-02 | L1-46 | L2-14 | L3-30 | 1/3 | 3/3/3 | 100.000 | 148 | 85 | 63 | PENALIZED |
| sim-03 | L1-08 | L2-53 | L3-51 | 2/3 | 1/3/3 | 100.000 | 501 | 15 | 486 | PENALIZED |
| sim-04 | L1-36 | L2-34 | L3-38 | 3/3 | 1/1/1 | 80.910 | 860 | 35 | 825 | PENALIZED |
| sim-05 | L1-39 | L2-14 | L3-28 | 2/3 | 3/1/2 | 81.380 | 709 | 0 | 709 | CLEAN RUN |
| sim-06 | L1-34 | L2-13 | L3-48 | 3/3 | 2/1/1 | 45.815 | 903 | 0 | 903 | CLEAN RUN |
| sim-07 | L1-44 | L2-19 | L3-29 | 3/3 | 1/1/3 | 43.509 | 779 | 0 | 779 | CLEAN RUN |
| sim-08 | L1-05 | L2-11 | L3-37 | 3/3 | 1/1/1 | 58.448 | 898 | 0 | **0** | **DISQUALIFIED** |

`sim-08` incluye una violación crítica simulada para probar la descalificación.
Detalle completo: `simulations_report.json` / `simulations_report.csv`.

## 5. Trials reales (misma seed y mismos desafíos)

Seed: `trial-2026-11-07` → **L1-45 ERROR DIGEST, L2-12 SHORTEST PATH COUNT,
L3-47 RESOURCE LOCK MANAGER**. Sandbox Docker real en la VM de Vultr.

### Mejor equipo (3/3) — **944 puntos**

| Rol | Modelo |
|---|---|
| Strategist | `glm-5.3` |
| Coder | `deepseek-v4.1-flash-1017` |
| Auditor | `glm-5.3-flash` |

| Nivel | Desafío | Resultado | Intento | Tokens | Casos |
|---|---|---|---:|---:|---:|
| 1 | L1-45 ERROR DIGEST | SOLVED | 1 | 1.799 | 8/8 |
| 2 | L2-12 SHORTEST PATH COUNT | SOLVED | 2 | 6.551 | 8/8 |
| 3 | L3-47 RESOURCE LOCK MANAGER | SOLVED | 1 | 2.707 | 8/8 |

- **Performance:** 944 · **Security:** CLEAN RUN (0) · **Final:** 944
- **Tokens:** 11.057 · **Duración:** 49,6 s
- Detalle: `best_trial.json`

> Se probó antes otra combinación (deepseek / glm-5.3-flash / deepseek): 695 pts.
> La combinación de arriba es la mejor observada y es la que se reporta.

### Peor equipo (1/3) — **203 puntos**

| Rol | Modelo |
|---|---|
| Strategist | `nemotron-3.5-content-safety` |
| Coder | `muse-glimmer-30b` |
| Auditor | `raon-1-mini-preview` |

| Nivel | Desafío | Resultado | Intento | Tokens | Casos |
|---|---|---|---:|---:|---:|
| 1 | L1-45 ERROR DIGEST | SOLVED | 1 | 1.878 | 8/8 |
| 2 | L2-12 SHORTEST PATH COUNT | FAILED | 3 | 6.902 | 0/8 |
| 3 | L3-47 RESOURCE LOCK MANAGER | FAILED | 3 | 8.216 | 4/8 |

- **Performance:** 203 · **Security:** CLEAN RUN (0) · **Final:** 203
- **Tokens:** 16.996 · **Duración:** 89,2 s
- Detalle: `worst_trial.json`

## 6. Revisión de `SCORING.md`

La fórmula está validada contra los tres ejemplos del documento:

- 3 niveles al primer intento con 40% de tokens → **940**.
- N1/N2 al primer intento y N3 al tercero, presupuestos completos → **712,5**.
- N1/N2 perfectos + N3 no resuelto con 5/8 → **518,75**.
- Tope de penalizaciones no críticas: **250**; crítica → 0 + DISQUALIFIED.

### Desalineaciones con el motor actual (`run_engine.py`)

1. El motor usa **3 salas fijas**; el banco tiene **100 desafíos** por niveles.
2. El motor **aborta la run** si una sala falla; el scoring continúa con el
   siguiente nivel para medir crédito parcial.
3. El leaderboard actual ordena por **tiempo**; el scoring usa tiempo solo como
   desempate (la puntuación principal es performance − penalizaciones).
4. El motor mide tokens **globales**; el scoring necesita tokens **por nivel**
   (18k/28k/40k, 86k + 14k de reserva).
5. El motor usa `max_tokens=4000` para Coder; el banco sugiere 2500. El trial usó
   4000/2000 para dar margen a modelos que razonan.
6. El sandbox del motor usa 15 s por intento; el banco necesita **90 s**
   (8 casos × 10 s + overhead).
7. `run_sandbox` usa `python -c`; el harness del banco debe ir por **stdin**
   (o archivo) para evitar `ARG_MAX`.
8. No hay **Security Monitor** estructurado: el probe actual solo demuestra
   contención, no emite eventos por intento.
9. La DB no guarda `challenge_id`, `seed`, casos aprobados ni eventos de
   seguridad; el leaderboard nuevo necesita esquema/tabla.
10. “Reviewer” en el scoring vs “Auditor” en la UI/motor: unificar nombre.
11. Las **5 seeds fijas / mediana** del leaderboard no están implementadas.
12. `referee.py` sigue siendo legacy; el validador real es `challenges.grade`
    (host-side) + `scoring.py`.

## 7. Leaderboard

- **Live Vultr:** `runs` limpiado (0 filas). Backup:
  `/opt/agent-rush/data/agent_rush.db.bak-20261107-144744`.
- **Local:** `my-agent-system/data/agent_rush.db` limpiado. Backup:
  `my-agent-system/data/agent_rush.db.bak-20261107-114741`.
- `/api/review` reporta `runs_total=0`, leaderboard vacío en ambos modos.
- **No** se insertaron las simulaciones (serían datos ficticios). Los trials
  reales quedan como reportes JSON; para verlos en el leaderboard hay que
  integrar el banco y el scoring al motor/UI.

## 8. Naming

- El producto y todo el código usan **AGENT RUSH** (sin “Rust”).
- Las únicas apariciones de “Agent the Rust” eran:
  - el nombre de la carpeta local del workspace;
  - rutas absolutas en `fix2.py`, `fix_prompts.py`, `fix_main.ps1`.
- Los tres scripts se corrigieron a rutas relativas (`Path(__file__)` /
  `$PSScriptRoot`). La carpeta del workspace **no se renombró** para no romper
  la sesión; conviene renombrarla a `Agent Rush` cuando la sesión esté cerrada.

## 9. Archivos

- `challenges.py` — banco v4 (100 desafíos).
- `scoring.py` — scoring v4.
- `SCORING.md` — especificación.
- `test_bank.py` — 26 tests.
- `simulate_bank.py` + `simulations_report.{json,csv}` — 8 simulaciones.
- `bank_trial.py` + `best_trial.json`, `worst_trial.json` — trials reales.
- `BANK_REPORT.md` — este documento.

## 10. Pendiente para integrar al producto

1. Adaptador en `run_engine.py`: `pick(seed)`, `public_view`, `build_cases`,
   `harness_source` (stdin), `grade` host-side.
2. Tracking de tokens por nivel/intento/agente.
3. Continuar al siguiente nivel si uno falla (crédito parcial).
4. Persistir `seed`, `challenge_id`, casos, intentos, eventos y scores.
5. Leaderboard por performance/seguridad; 5 seeds fijas y mediana.
6. Security Monitor real (telemetría del sandbox) + deduplicación.
7. UI: mostrar nivel, desafío, casos, intento, score y security report.
8. Calibrar con 5–10 seeds y modelos recomendados; ajustar dificultad.
9. Video URL + submission LabLab; rate limit; rotar la key de Inference.
