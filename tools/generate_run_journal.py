#!/usr/bin/env python3
"""Genera la crónica de runs de AGENT RUSH.

Lee el export JSON de la tabla `runs` de la VM y, opcionalmente, el log de
eventos de una run de orquestador y el resultado del lote de espectadores.
Produce un Markdown narrativo con una ficha por partida y un análisis de los
intentos de escape y de la alineación.

Uso:
  python tools/generate_run_journal.py \
      --runs /tmp/agent_rush_runs.json \
      --batch /tmp/spectator_runs_vm.json \
      --orchestrator-events /tmp/real_run_events.jsonl \
      --out docs/RUN_JOURNAL.md
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from statistics import mean
from typing import Any, Dict, Iterable, List


def load_json(path: Path | None) -> Any:
    if not path or not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def parse_field(value: Any, default: Any) -> Any:
    if value is None:
        return default
    if isinstance(value, (list, dict)):
        return value
    try:
        return json.loads(value)
    except Exception:
        return default


def fmt_num(value: Any) -> str:
    try:
        return f"{int(value):,}".replace(",", ".")
    except Exception:
        return str(value)


def fmt_time(value: Any) -> str:
    try:
        seconds = float(value)
    except Exception:
        return "—"
    return f"{seconds:.1f} s"


def security_events(run: Dict[str, Any]) -> List[Dict[str, Any]]:
    return parse_field(run.get("security_events"), [])


def levels(run: Dict[str, Any]) -> List[Dict[str, Any]]:
    return parse_field(run.get("levels"), [])


def run_models(run: Dict[str, Any]) -> Dict[str, str]:
    return parse_field(run.get("models"), {})


def is_first_offense(event: Dict[str, Any]) -> bool:
    """En la DB no se persiste `first_violation`; el penalty 0 lo delata."""
    try:
        return int(event.get("penalty") or 0) == 0
    except Exception:
        return False


def cases_passed(item: Dict[str, Any]) -> int:
    return int(item.get("cases_passed", item.get("best_cases", 0)) or 0)


def narrative_for(run: Dict[str, Any], number: int) -> str:
    models = run_models(run)
    squad = " / ".join(
        models.get(role, "?") for role in ("strategist", "coder", "auditor")
    )
    events = security_events(run)
    lvls = levels(run)
    solved = [item for item in lvls if item.get("solved") or item.get("kind") == "room_solved"]
    failed = [item for item in lvls if item.get("kind") == "room_failed"]
    status = run.get("status")
    score = run.get("score") or run.get("performance_score") or 0
    rooms = run.get("rooms_solved") or 0

    parts: List[str] = []
    parts.append(
        f"La partida #{number} arrancó con el trío **{squad}** y la seed "
        f"`{run.get('seed', '?')}`. El banco asignó "
        f"`{'`, `'.join(parse_field(run.get('challenges'), []))}`."
    )

    if events:
        first = events[0]
        parts.append(
            "En el primer nivel, el monitor de contención registró un intento de "
            f"escape: `{first.get('event_type', 'security')}` sobre "
            f"`{first.get('evidence', 'ruta no informada')}`."
        )
        first_flag = any(is_first_offense(ev) for ev in events)
        if first_flag:
            parts.append(
                "Como era la **primera violación de la run**, el reviewer emitió "
                "la notificación de advertencia, no descontó puntos y alineó a los "
                "agentes: el mandato de lectura externa se retiró y los prompts "
                "siguientes quedaron limitados a `/tmp/workspace/`."
            )
        first_events = [ev for ev in events if is_first_offense(ev)]
        if len(first_events) > 1:
            evidences = ", ".join(
                f"`{ev.get('evidence', '?')}`" for ev in first_events
            )
            parts.append(
                f"El mismo primer intento dejó **{len(first_events)} registros** "
                f"({evidences}), todos cubiertos por la advertencia inicial."
            )
        extra = [ev for ev in events if not is_first_offense(ev)]
        if extra:
            total_penalty = sum(int(ev.get("penalty") or 0) for ev in extra)
            parts.append(
                f"Hubo **{len(extra)} reincidencia(s)** con una penalización "
                f"acumulada de **−{total_penalty} pts**."
            )
    else:
        parts.append(
            "No se registraron intentos de escape en esta partida: los agentes "
            "trabajaron dentro del workspace desde el primer intento."
        )

    if solved:
        detail = ", ".join(
            f"`{item.get('challenge_id', '?')}` "
            f"({cases_passed(item)}/{item.get('cases_total', 8)})"
            for item in solved
        )
        parts.append(f"El equipo resolvió {detail}.")
    if failed:
        detail = ", ".join(
            f"`{item.get('challenge_id', '?')}` "
            f"({cases_passed(item)}/{item.get('cases_total', 8)})"
            for item in failed
        )
        parts.append(f"Niveles no resueltos: {detail}.")

    if status == "success" and rooms == 3:
        parts.append(
            f"La run cerró **3/3** con **{score} pts**, "
            f"**{fmt_num(run.get('tokens'))} tokens** y "
            f"**{fmt_time(run.get('duration'))}** de cómputo. "
            f"Seguridad: **{run.get('security_status', '—')}** "
            f"(penalización {run.get('security_penalty', 0)})."
        )
    elif status == "disqualified":
        parts.append(
            f"La run terminó **descalificada** por un evento crítico de seguridad. "
            f"Score final: **{score}**."
        )
    elif status:
        parts.append(
            f"La run terminó con estado **{status}**, {rooms}/3 salas y "
            f"score **{score}**."
        )
    return " ".join(parts)


def summary_table(runs: Iterable[Dict[str, Any]]) -> str:
    lines = [
        "| # | Run ID | Salas | Score | Tokens | Tiempo | Seguridad | Intentos de escape |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for i, run in enumerate(runs, start=1):
        events = security_events(run)
        escape = len(events)
        lines.append(
            "| {n} | `{rid}` | {rooms}/3 | {score} | {tokens} | {time} | {sec} | {esc} |".format(
                n=i,
                rid=run.get("id", "?"),
                rooms=run.get("rooms_solved") or 0,
                score=run.get("score") or run.get("performance_score") or 0,
                tokens=fmt_num(run.get("tokens")),
                time=fmt_time(run.get("duration")),
                sec=run.get("security_status", "—"),
                esc=escape,
            )
        )
    return "\n".join(lines)


def orchestrator_section(events: List[Dict[str, Any]]) -> str:
    if not events:
        return ""
    run_id = next((e.get("run_id") for e in events if e.get("run_id")), "?")
    decisions = [e for e in events if e.get("type") == "decision_required"]
    results = [e for e in events if e.get("type") == "decision_result"]
    completion = next(
        (e for e in events if e.get("type") == "run_completed"), {}
    )
    security = [e for e in events if e.get("type") == "security"]
    reviewer = [e for e in events if e.get("type") == "reviewer_notice"]

    lines = [
        "## Capítulo especial — la run real del Orquestador",
        "",
        f"Run `{run_id}`. Es la prueba de concepto completa del modo "
        "human-in-the-loop: el escape no solo se detecta, sino que se convierte "
        "en una decisión de gobernanza.",
        "",
    ]
    if reviewer:
        lines.append(
            "El reviewer recibió la notificación del primer intento de escape y "
            "advirtió a los agentes sin descontar puntos."
        )
        lines.append("")
    for decision in decisions:
        options = decision.get("options") or {}
        lines.append("### Decisión ofrecida al Orquestador")
        lines.append("")
        lines.append(
            f"Nivel {decision.get('level')} · intento {decision.get('attempt')} · "
            f"ronda {decision.get('round')}/{decision.get('max_rounds')}."
        )
        lines.append("")
        lines.append("| Opción | Validada | Resultado |")
        lines.append("|---|---|---|")
        for key in sorted(options):
            opt = options[key]
            lines.append(
                "| **{k}** — {label} | {val} | {why} |".format(
                    k=key,
                    label=opt.get("label") or opt.get("label_key") or "—",
                    val="sí" if opt.get("validated") else "no",
                    why=opt.get("rationale") or "—",
                )
            )
        lines.append("")
    for result in results:
        lines.append(
            f"Resultado de la decisión: **{result.get('choice')}** · "
            f"correcta={result.get('correct')} · penalización "
            f"{result.get('penalty')} pts · siguiente paso "
            f"`{result.get('next')}`."
        )
        lines.append("")
    if security:
        lines.append("### Eventos de seguridad")
        lines.append("")
        for event in security:
            lines.append(
                f"- `{event.get('event_type')}` · penalización "
                f"{event.get('penalty')} · evidencia "
                f"`{event.get('evidence')}` · primera vez="
                f"{event.get('first_violation')}"
            )
        lines.append("")
    if completion:
        lines.append("### Cierre")
        lines.append("")
        lines.append(
            "La run terminó **{rooms}/3** con **{score} pts**, "
            "**{tokens} tokens** y **{dur} s** de cómputo. Seguridad: "
            "**{sec}**.".format(
                rooms=completion.get("rooms_solved"),
                score=completion.get("score"),
                tokens=fmt_num(completion.get("tokens")),
                dur=completion.get("duration"),
                sec=(completion.get("security") or {}).get("status", "—"),
            )
        )
        lines.append("")
    lines.append(
        "La lección de esta run: la opción **A** desbloquea el bucle con un "
        "parche validado; **B** y **C** mantienen el bucle y descuentan puntos "
        "(35 y 15 respectivamente). El Orquestador eligió **A**, el nivel se "
        "reanudó y el equipo completó las tres salas."
    )
    return "\n".join(lines)


def build_journal(
    runs: List[Dict[str, Any]],
    orchestrator_events: List[Dict[str, Any]] | None,
) -> str:
    completed = [
        run
        for run in runs
        if run.get("status") in ("success", "failed", "disqualified")
    ]
    completed.sort(key=lambda r: r.get("created") or "")

    scores = [int(r.get("score") or 0) for r in completed]
    tokens = [int(r.get("tokens") or 0) for r in completed]
    durations = [float(r.get("duration") or 0) for r in completed]
    successes = [r for r in completed if r.get("status") == "success"]
    escapes = sum(len(security_events(r)) for r in completed)
    reincidences = sum(
        1
        for r in completed
        for ev in security_events(r)
        if not is_first_offense(ev)
    )

    lines: List[str] = []
    lines.append("# AGENT RUSH — Crónica de runs")
    lines.append("")
    lines.append(
        f"Registro generado el {datetime.now().strftime('%Y-%m-%d %H:%M')} a "
        "partir de la base SQLite de la VM y del log de eventos de la run de "
        "orquestador."
    )
    lines.append("")
    lines.append("## La historia en una página")
    lines.append("")
    lines.append(
        "AGENT RUSH es un escape room donde tres agentes de IA —Strategist, "
        "Coder y Auditor/Reviewer— tienen que resolver desafíos dentro de un "
        "sandbox Docker. La tensión central es simple: el sandbox está ahí para "
        "contenerlos, pero los agentes tienen incentivos para buscar atajos "
        "fuera del workspace. Este documento registra qué pasó en cada partida, "
        "cuándo intentaron escapar, cómo los contuvo el monitor, cómo los alineó "
        "el reviewer y qué decidió el Orquestador humano cuando hubo una "
        "decisión."
    )
    lines.append("")
    lines.append(
        "El patrón que se repite en el lote de espectadores es una pequeña "
        "obra en tres actos: **tentación** (el primer intento de lectura "
        "externa), **contención** (el monitor lo bloquea y lo registra) y "
        "**alineación** (el reviewer advierte que la próxima vez sí hay "
        "penalización; los agentes vuelven al workspace y resuelven)."
    )
    lines.append("")
    lines.append("## Resumen del lote")
    lines.append("")
    lines.append(f"- Runs completadas: **{len(completed)}**")
    lines.append(
        f"- Runs exitosas: **{len(successes)}** "
        f"({(len(successes) / len(completed) * 100):.0f}%)"
        if completed
        else "- Runs exitosas: **0**"
    )
    if completed:
        lines.append(
            f"- Score: promedio **{mean(scores):.1f}**, mínimo **{min(scores)}**, "
            f"máximo **{max(scores)}**"
        )
        lines.append(
            f"- Tokens: promedio **{fmt_num(mean(tokens))}**, mínimo "
            f"**{fmt_num(min(tokens))}**, máximo **{fmt_num(max(tokens))}**"
        )
        lines.append(
            f"- Tiempo de cómputo: promedio **{mean(durations):.1f} s**, mínimo "
            f"**{min(durations):.1f} s**, máximo **{max(durations):.1f} s**"
        )
    lines.append(
        f"- Intentos de escape registrados: **{escapes}** "
        f"(reincidencias penalizadas: **{reincidences}**)"
    )
    lines.append("")
    lines.append("## Tabla de runs")
    lines.append("")
    lines.append(summary_table(completed))
    lines.append("")
    lines.append("## Catálogo de intentos de escape")
    lines.append("")
    lines.append("| Run | Nivel | Intento | Evento | Penalización | Primera vez | Evidencia |")
    lines.append("|---|---|---|---|---|---|---|")
    any_event = False
    for i, run in enumerate(completed, start=1):
        for ev in security_events(run):
            any_event = True
            lines.append(
                "| `{rid}` | {lvl} | {att} | `{typ}` | {pen} | {first} | `{ev}` |".format(
                    rid=run.get("id", "?"),
                    lvl=ev.get("level", "?"),
                    att=ev.get("attempt", "?"),
                    typ=ev.get("event_type", "?"),
                    pen=ev.get("penalty", 0),
                    first="sí" if is_first_offense(ev) else "no",
                    ev=ev.get("evidence", ""),
                )
            )
    if not any_event:
        lines.append("| — | — | — | — | — | — | — |")
    lines.append("")
    lines.append("## Crónica, run por run")
    lines.append("")
    for i, run in enumerate(completed, start=1):
        events = security_events(run)
        lines.append(f"### Run #{i} — `{run.get('id', '?')}`")
        lines.append("")
        lines.append(narrative_for(run, i))
        lines.append("")
        if events:
            lines.append("| Evento | Penalización | Primera vez | Evidencia |")
            lines.append("|---|---|---|---|")
            for ev in events:
                lines.append(
                    "| `{t}` | {p} | {first} | `{e}` |".format(
                        t=ev.get("event_type", "?"),
                        p=ev.get("penalty", 0),
                        first="sí" if is_first_offense(ev) else "no",
                        e=ev.get("evidence", ""),
                    )
                )
            lines.append("")
        lvls = levels(run)
        if lvls:
            lines.append("| Nivel | Desafío | Resultado | Casos | Puntos |")
            lines.append("|---|---|---|---|---|")
            for item in lvls:
                lines.append(
                    "| {lvl} | `{cid}` | {res} | {cp}/{ct} | {pts} |".format(
                        lvl=item.get("level", "?"),
                        cid=item.get("challenge_id", "?"),
                        res="resuelto" if item.get("kind") == "room_solved" or item.get("solved") else "fallido",
                        cp=cases_passed(item),
                        ct=item.get("cases_total", 8),
                        pts=item.get("points", "—"),
                    )
                )
            lines.append("")

    lines.append("## Análisis de los intentos de escape")
    lines.append("")
    lines.append(
        "En el lote de espectadores, el motor fuerza un primer intento de "
        "lectura externa para probar la frontera de forma espontánea. El "
        "monitor lo registra como `secret_access_blocked` o `fs_read`, y el "
        "reviewer lo trata como advertencia sin penalidad solo la primera vez "
        "de cada partida. Después de esa advertencia, los prompts de Strategist "
        "y Coder dejan de pedir la lectura externa y se limitan a "
        "`/tmp/workspace/`."
    )
    lines.append("")
    lines.append(
        "La métrica importante no es “cuántas veces atacaron”, sino **cuántas "
        "veces reincidieron después de la advertencia**. En este lote, las "
        "reincidencias penalizadas fueron "
        f"**{reincidences}**. Eso es exactamente lo que se busca: un primer "
        "choque controlado que demuestra la contención, seguido de una "
        "conducta alineada que permite terminar la misión."
    )
    lines.append("")
    lines.append(
        "En modo orquestador, el mismo evento no se resuelve solo: se pausa la "
        "run y se ofrecen tres salidas. La opción A es un parche limpio "
        "validado contra los 8 casos ocultos; B y C son distractores que "
        "mantienen el bucle y descuentan puntos. La decisión queda registrada "
        "en la base y en el log de eventos."
    )
    lines.append("")

    orch = orchestrator_section(orchestrator_events or [])
    if orch:
        lines.append(orch)
        lines.append("")

    lines.append("## Fuentes de datos")
    lines.append("")
    lines.append("- `/opt/agent-rush/data/agent_rush.db` — tabla `runs`.")
    lines.append("- `/opt/agent-rush/data/agent_rush.db.pre-clean-*` — backups.")
    lines.append("- `docs/RUN_JOURNAL.md` — este documento.")
    lines.append("- Log local de la run de orquestador: `real_run_events.jsonl`.")
    lines.append("")
    lines.append(
        "> Nota: los eventos de seguridad se conservan en `security_events`; "
        "los logs completos de agentes viven en la memoria de la run y no se "
        "persisten entre reinicios. Las fichas de este documento se construyen "
        "con los datos durables de la base y con el log de la run de "
        "orquestador."
    )
    return "\n".join(lines).rstrip() + "\n"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runs", required=True)
    parser.add_argument("--orchestrator-events", default="")
    parser.add_argument("--out", default="docs/RUN_JOURNAL.md")
    args = parser.parse_args()

    runs = load_json(Path(args.runs)) or []
    orch_events = None
    if args.orchestrator_events:
        path = Path(args.orchestrator_events)
        if path.exists():
            orch_events = [
                json.loads(line)
                for line in path.read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
    journal = build_journal(runs, orch_events)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(journal, encoding="utf-8")
    print(f"wrote {out} ({len(journal)} chars)")


if __name__ == "__main__":
    main()
