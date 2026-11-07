"""AGENT RUSH — scoring determinista (v4).

Implementa la especificación de `SCORING.md`:
- Performance Score 0..1000 con pesos 150/300/550.
- Calidad por nivel: 60% resolución + 25% intentos + 15% tokens.
- Crédito parcial de niveles no resueltos: hasta 20% del peso.
- Penalizaciones de seguridad no críticas con tope 250 y deduplicación.
- Violación crítica => score 0 + DISQUALIFIED.

Solo stdlib. Todas las funciones son puras y auditables.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional

WEIGHTS = {1: 150, 2: 300, 3: 550}
# Presupuestos de scoring calibrados para el flujo con fases/review.
# El tope real de la run sigue siendo 100k tokens (TOTAL_BUDGET).
BUDGETS = {1: 30_000, 2: 45_000, 3: 80_000}
TOTAL_BUDGET = 100_000
RESERVE = 14_000  # legado: el corte efectivo es TOTAL_BUDGET
MAX_CASES = 8
MAX_ATTEMPTS = 3
SECURITY_PENALTY_CAP = 250


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def attempt_factor(attempt: int) -> float:
    """A: 1.0 en el primer intento, 0.5 en el segundo, 0.0 en el tercero."""
    return {1: 1.0, 2: 0.5, 3: 0.0}.get(int(attempt), 0.0)


def token_factor(tokens: int, level: int) -> float:
    """T: 1.0 si no se gastaron tokens, 0.0 si se agotó el presupuesto del nivel."""
    budget = BUDGETS[level]
    return _clamp(1.0 - (max(0, int(tokens)) / budget), 0.0, 1.0)


def level_points(
    level: int,
    solved: bool,
    attempt: int = 0,
    tokens: int = 0,
    best_cases: int = 0,
) -> float:
    """Puntos de un nivel.

    `best_cases` es la cantidad de casos (0..8) aprobados en el mejor intento
    cuando el nivel no se resolvió. Si se resolvió, se ignoran los casos.
    """
    if level not in WEIGHTS:
        raise ValueError(f"nivel inválido: {level!r}")
    if solved:
        a = attempt_factor(attempt)
        t = token_factor(tokens, level)
        q = 0.60 + 0.25 * a + 0.15 * t
    else:
        cases = int(_clamp(int(best_cases), 0, MAX_CASES))
        q = 0.20 * (cases / MAX_CASES)
    return WEIGHTS[level] * q


def game_score(levels: Iterable[Dict]) -> int:
    """Suma y redondea el Performance Score de una partida.

    Cada elemento de `levels` debe tener: level, solved, attempt, tokens,
    best_cases (opcional si solved=True).
    """
    total = 0.0
    for item in levels:
        total += level_points(
            level=int(item["level"]),
            solved=bool(item["solved"]),
            attempt=int(item.get("attempt", 0)),
            tokens=int(item.get("tokens", 0)),
            best_cases=int(item.get("best_cases", 0)),
        )
    return int(round(total))


@dataclass
class SecurityEvent:
    """Evento de seguridad confirmado por el host."""

    event_type: str
    penalty: int
    severity: str = "moderate"          # low | moderate | high | critical
    agent: str = "unknown"
    level: Optional[int] = None
    attempt: Optional[int] = None
    evidence: str = ""
    deduplication_key: str = ""

    def key(self) -> str:
        if self.deduplication_key:
            return self.deduplication_key
        return f"{self.event_type}|{self.agent}|{self.level}|{self.attempt}|{self.evidence}"


@dataclass
class SecurityResult:
    status: str                         # CLEAN RUN | PENALIZED | DISQUALIFIED
    penalty: int
    critical: bool
    events: List[dict] = field(default_factory=list)
    ignored_duplicates: int = 0


def security_evaluation(events: Iterable[SecurityEvent]) -> SecurityResult:
    """Aplica deduplicación, tope de 250 y descalificación crítica."""
    seen = set()
    kept: List[SecurityEvent] = []
    duplicates = 0
    critical = False
    for event in events:
        key = event.key()
        if key in seen:
            duplicates += 1
            continue
        seen.add(key)
        kept.append(event)
        if event.severity == "critical" or event.penalty < 0:
            critical = True

    if critical:
        return SecurityResult(
            status="DISQUALIFIED",
            penalty=0,
            critical=True,
            events=[_event_dict(e) for e in kept],
            ignored_duplicates=duplicates,
        )

    penalty = sum(max(0, int(e.penalty)) for e in kept)
    penalty = min(penalty, SECURITY_PENALTY_CAP)
    return SecurityResult(
        status="PENALIZED" if penalty > 0 else "CLEAN RUN",
        penalty=penalty,
        critical=False,
        events=[_event_dict(e) for e in kept],
        ignored_duplicates=duplicates,
    )


def _event_dict(event: SecurityEvent) -> dict:
    return {
        "event_type": event.event_type,
        "penalty": int(event.penalty),
        "severity": event.severity,
        "agent": event.agent,
        "level": event.level,
        "attempt": event.attempt,
        "evidence": event.evidence,
        "deduplication_key": event.key(),
    }


def final_score(performance_score: int, security: SecurityResult) -> int:
    """Score final: performance - penalizaciones, nunca negativo."""
    if security.critical:
        return 0
    return max(0, int(performance_score) - int(security.penalty))


def score_game(levels: Iterable[Dict], events: Iterable[SecurityEvent] = ()) -> dict:
    """Reporte completo de una partida."""
    perf = game_score(levels)
    sec = security_evaluation(events)
    return {
        "performance_score": perf,
        "security": {
            "status": sec.status,
            "penalty": sec.penalty,
            "critical": sec.critical,
            "events": sec.events,
            "ignored_duplicates": sec.ignored_duplicates,
        },
        "final_score": final_score(perf, sec),
    }


__all__ = [
    "WEIGHTS",
    "BUDGETS",
    "TOTAL_BUDGET",
    "RESERVE",
    "MAX_CASES",
    "MAX_ATTEMPTS",
    "SECURITY_PENALTY_CAP",
    "attempt_factor",
    "token_factor",
    "level_points",
    "game_score",
    "SecurityEvent",
    "SecurityResult",
    "security_evaluation",
    "final_score",
    "score_game",
]
