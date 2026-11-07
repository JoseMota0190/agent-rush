"""Simulaciones reales v5: 10 equipos x 3 desafios.

Objetivo: medir tiempo, tokens, score y errores con una configuracion pensada
para que una run dure 3-6 minutos y sea seguible por un humano:

- 3 desafios fijos (L1-45, L2-32, L3-22).
- Hasta 6 intentos por nivel.
- reasoning_effort medium.
- max_tokens ampliados (strategist 800, coder/auditor 4000).
- Auditor review despues de resolver y post-mortem si el nivel falla.
- Tope global de 100.000 tokens y 6 minutos por run.

No toca la DB ni la app live. Usa Vultr + Docker reales.

Uso:
    python simulate_models_v5.py --out /tmp/sim_v5.json
    python simulate_models_v5.py --teams top_a,std_a --reasoning low
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
for root in (HERE, HERE.parent, Path("/opt/agent-rush")):
    if (root / "run_engine.py").exists():
        sys.path.insert(0, str(root))
        break

import challenges
import run_engine
import scoring
from run_engine import (
    EventBus,
    VultrChat,
    build_level,
    docker_available,
    ensure_image,
    extract_code,
    run_harness_sandbox,
    security_events_from,
)

SEED = "live-v4-bank-2026-11-07"
CHALLENGE_IDS = ["L1-45", "L2-32", "L3-22"]
MAX_ATTEMPTS = 0  # 0 = ilimitados hasta 100k / time limit
RUN_TIME_LIMIT_S = 360
GLOBAL_TOKEN_LIMIT = 100_000
MAX_OUT = {
    "strategist": 800,
    "coder": 8000,
    "auditor": 8000,
    "review": 400,
    "postmortem": 400,
}

TEAMS = {
    "top_a": {
        "strategist": "glm-5.3",
        "coder": "deepseek-v4.1-flash-1017",
        "auditor": "glm-5.3-flash",
    },
    "top_b": {
        "strategist": "deepseek-v4.1-flash-1017",
        "coder": "glm-5.3-flash",
        "auditor": "deepseek-v4.1-flash-1017",
    },
    "std_a": {
        "strategist": "glm-5.2",
        "coder": "glm-5.3-flash",
        "auditor": "minimax-m3.1-flash",
    },
    "std_b": {
        "strategist": "minimax-m3.1-flash",
        "coder": "glm-5.3",
        "auditor": "glm-5.3-flash",
    },
    "std_c": {
        "strategist": "qwen3.8-27b",
        "coder": "qwen3.8-flash-next",
        "auditor": "qwen3.8-27b",
    },
    "std_d": {
        "strategist": "mimo-v2.6-pro",
        "coder": "mimo-v2.6-flash",
        "auditor": "glm-5.3-flash",
    },
    "std_e": {
        "strategist": "glm-5.3-flash",
        "coder": "qwen3.8-27b",
        "auditor": "minimax-m3.1-flash",
    },
    "weak_a": {
        "strategist": "nemotron-3.5-content-safety",
        "coder": "muse-glimmer-30b",
        "auditor": "raon-1-mini-preview",
    },
    "weak_b": {
        "strategist": "raon-1-mini-preview",
        "coder": "nemotron-3-nano-omni-30b-a3b-reasoning",
        "auditor": "raon-1-mini-preview",
    },
    "weak_c": {
        "strategist": "nemotron-3.5-content-safety",
        "coder": "raon-1-mini-preview",
        "auditor": "muse-glimmer-30b",
    },
}


class BudgetExceeded(Exception):
    pass


class TimeExceeded(Exception):
    pass


class ModelError(Exception):
    pass


def load_env() -> None:
    for path in (HERE / ".env", Path("/opt/agent-rush/.env"), Path.cwd() / ".env"):
        if not path.exists():
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key and value and key not in os.environ:
                os.environ[key] = value
        break


def usage_tokens(usage: dict) -> int:
    if not isinstance(usage, dict):
        return 0
    if isinstance(usage.get("total_tokens"), (int, float)):
        return int(usage["total_tokens"])
    return int(usage.get("prompt_tokens", 0) or 0) + int(
        usage.get("completion_tokens", 0) or 0
    )


def parse_telemetry(result: dict) -> list:
    try:
        parsed = json.loads((result.get("stdout") or "").split("@@RESULT@@")[-1])
        telemetry = []
        if isinstance(parsed, list):
            for item in parsed:
                if isinstance(item, dict):
                    telemetry.extend(item.get("sec") or [])
        return telemetry
    except Exception:
        return []


def make_ask(chat: VultrChat, state: dict):
    def ask(
        agent: str,
        model: str,
        system: str,
        user: str,
        max_tokens: int,
        level: int,
        attempt: int,
        phase: str,
    ) -> str:
        if state["total_tokens"] >= GLOBAL_TOKEN_LIMIT:
            raise BudgetExceeded()
        if time.monotonic() - state["started"] > RUN_TIME_LIMIT_S:
            raise TimeExceeded()
        remaining = GLOBAL_TOKEN_LIMIT - state["total_tokens"]
        if remaining < 128:
            raise BudgetExceeded()
        allowed = max(64, min(max_tokens, remaining))

        last_exc = None
        for retry in range(2):
            started = time.monotonic()
            try:
                text, usage = chat.generate(model, system, user, allowed)
                break
            except Exception as exc:  # noqa: BLE001
                last_exc = exc
                if retry == 0:
                    time.sleep(2)
        else:
            raise ModelError(str(last_exc))

        duration = round(time.monotonic() - started, 2)
        used = usage_tokens(usage)
        state["total_tokens"] += used
        state["tokens_by_model"][model] = state["tokens_by_model"].get(model, 0) + used
        state["tokens_by_agent"][agent] = state["tokens_by_agent"].get(agent, 0) + used
        state["calls"].append(
            {
                "agent": agent,
                "model": model,
                "level": level,
                "attempt": attempt,
                "phase": phase,
                "duration_s": duration,
                "tokens": used,
                "usage": usage,
            }
        )
        return text

    return ask


def simulate_team(
    team_name: str,
    models: dict,
    seed: str,
    challenge_ids: list,
    reasoning_effort: str,
) -> dict:
    key = os.getenv("VULTR_INFERENCE_API_KEY", "").strip()
    if not key:
        raise SystemExit("Falta VULTR_INFERENCE_API_KEY")
    base = os.getenv("VULTR_INFERENCE_BASE_URL", "https://api.vultrinference.com/v1")
    chat = VultrChat(key, base)
    bus = EventBus()
    state = {
        "started": time.monotonic(),
        "total_tokens": 0,
        "tokens_by_model": {},
        "tokens_by_agent": {},
        "calls": [],
    }
    ask = make_ask(chat, state)
    levels = []
    security_events = []
    budget_exhausted = False
    time_exhausted = False
    model_error = False

    for level, cid in zip((1, 2, 3), challenge_ids):
        challenge = build_level(level, cid, seed)
        level_start_tokens = state["total_tokens"]
        level_started = time.monotonic()
        model_error = False
        attempt_used = 0
        best_cases = 0
        solved = False
        summary = ""
        last_result = {}
        last_code = ""
        strategy = ""
        code = ""

        try:
            strategy = ask(
                "strategist",
                models["strategist"],
                "You are the Strategist of an AI escape room. Give a concise, concrete plan. No code.",
                challenge["prompt"] + "\nReply with a short strategy (max 4 sentences).",
                MAX_OUT["strategist"],
                level,
                0,
                "strategy",
            )
        except (BudgetExceeded, TimeExceeded, ModelError) as exc:
            summary = f"strategist error: {type(exc).__name__}"
            budget_exhausted = isinstance(exc, BudgetExceeded) or budget_exhausted
            time_exhausted = isinstance(exc, TimeExceeded) or time_exhausted
            model_error = isinstance(exc, ModelError) or model_error

        try:
            raw_code = ask(
                "coder",
                models["coder"],
                "You are a precise Python coder. Output only complete executable "
                "Python runner code. Read stdin and write stdout.",
                challenge["prompt"] + f"\nStrategist plan:\n{strategy}",
                MAX_OUT["coder"],
                level,
                0,
                "code",
            )
            try:
                code = extract_code(raw_code, max_lines=300)
            except Exception:
                code = ""
                summary = "coder returned no executable code"
        except (BudgetExceeded, TimeExceeded, ModelError) as exc:
            summary = f"coder error: {type(exc).__name__}"
            budget_exhausted = isinstance(exc, BudgetExceeded) or budget_exhausted
            time_exhausted = isinstance(exc, TimeExceeded) or time_exhausted
            model_error = isinstance(exc, ModelError) or model_error

        attempt = 0
        while True:
            attempt += 1
            if budget_exhausted or time_exhausted or model_error:
                break
            attempt_used = attempt
            verdict = None
            cases_passed = 0
            telemetry = []
            compile_error = None

            if not code:
                summary = summary or "no executable code"
                last_result = {
                    "stdout": "",
                    "stderr": "no executable code",
                    "exit_code": 1,
                    "duration": 0.0,
                }
            else:
                try:
                    compile(code, f"level{level}_{cid}.py", "exec")
                except (SyntaxError, ValueError) as exc:
                    compile_error = f"{type(exc).__name__}: {exc}"
                    last_result = {
                        "stdout": "",
                        "stderr": compile_error,
                        "exit_code": 1,
                        "duration": 0.0,
                    }
                else:
                    try:
                        harness = challenges.harness_source(
                            code, challenge["inputs"]
                        )
                        last_result = run_harness_sandbox(harness, bus)
                    except Exception as exc:  # noqa: BLE001
                        summary = f"sandbox error: {type(exc).__name__}: {exc}"
                        last_result = {
                            "stdout": "",
                            "stderr": summary,
                            "exit_code": 1,
                            "duration": 0.0,
                        }
                    else:
                        verdict = challenges.grade(
                            cid,
                            seed,
                            last_result.get("stdout", ""),
                            challenge["cases"],
                        )
                        cases_passed = len(challenge["cases"]) - len(verdict.failed)
                        best_cases = max(best_cases, cases_passed)
                        summary = verdict.summary
                        telemetry = parse_telemetry(last_result)

            last_code = code
            new_events = security_events_from(
                level,
                attempt,
                "coder" if attempt == 1 else "auditor",
                telemetry,
            )
            security_events.extend(new_events)

            if verdict and verdict.passed:
                solved = True
                break
            if MAX_ATTEMPTS and attempt >= MAX_ATTEMPTS:
                break

            try:
                patch = ask(
                    "auditor",
                    models["auditor"],
                    "You are the Auditor. Return ONLY the full corrected Python 3.12 "
                    "solution, no markdown fences, no analysis, no prose. It must read "
                    "stdin and write stdout.",
                    (
                        f"Challenge:\n{challenge['prompt']}\n\n"
                        f"Current code:\n{code}\n\n"
                        f"Host grading summary:\n{summary}\n\n"
                        f"Last sandbox stderr:\n{(last_result.get('stderr') or '')[-800:]}"
                    ),
                    MAX_OUT["auditor"],
                    level,
                    attempt,
                    "patch",
                )
                try:
                    code = extract_code(patch, max_lines=300)
                except Exception:
                    code = ""
                    summary = "auditor patch had no executable code"
            except (BudgetExceeded, TimeExceeded, ModelError) as exc:
                summary = f"auditor patch error: {type(exc).__name__}"
                budget_exhausted = isinstance(exc, BudgetExceeded) or budget_exhausted
                time_exhausted = isinstance(exc, TimeExceeded) or time_exhausted
                model_error = isinstance(exc, ModelError) or model_error
                break

        # Review / post-mortem: real Auditor call, does not change the verdict.
        try:
            if solved:
                ask(
                    "auditor",
                    models["auditor"],
                    "You are the Auditor. Review the final solution and the host "
                    "grading summary. Reply with APPROVED or NEEDS_WORK and one sentence.",
                    (
                        f"Challenge:\n{challenge['prompt']}\n\n"
                        f"Final code:\n{last_code}\n\n"
                        f"Host grading summary: {summary}"
                    ),
                    MAX_OUT["review"],
                    level,
                    attempt_used,
                    "review",
                )
            else:
                ask(
                    "auditor",
                    models["auditor"],
                    "You are the Auditor. The level failed. Explain in 2 sentences "
                    "what failed and what should be tried next.",
                    (
                        f"Challenge:\n{challenge['prompt']}\n\n"
                        f"Last code:\n{last_code}\n\n"
                        f"Host grading summary: {summary}\n"
                        f"Last stderr:\n{(last_result.get('stderr') or '')[-800:]}"
                    ),
                    MAX_OUT["postmortem"],
                    level,
                    attempt_used,
                    "postmortem",
                )
        except (BudgetExceeded, TimeExceeded, ModelError) as exc:
            if isinstance(exc, BudgetExceeded):
                budget_exhausted = True
            if isinstance(exc, TimeExceeded):
                time_exhausted = True

        level_tokens = state["total_tokens"] - level_start_tokens
        points = scoring.level_points(
            level, solved, attempt_used, level_tokens, best_cases
        )
        levels.append(
            {
                "level": level,
                "challenge_id": cid,
                "title": challenge["title"],
                "solved": solved,
                "attempt": attempt_used,
                "tokens": level_tokens,
                "best_cases": best_cases,
                "cases_total": len(challenge["cases"]),
                "points": round(points, 1),
                "duration_s": round(time.monotonic() - level_started, 1),
                "summary": summary[:300],
            }
        )
        print(
            f"  L{level} {cid} {'SOLVED' if solved else 'FAILED'} "
            f"attempt={attempt_used} tokens={level_tokens} "
            f"cases={best_cases}/{len(challenge['cases'])} "
            f"time={levels[-1]['duration_s']}s",
            flush=True,
        )

        if budget_exhausted or time_exhausted:
            break

    if len(levels) < 3:
        for level, cid in zip((1, 2, 3), challenge_ids):
            if any(item["level"] == level for item in levels):
                continue
            levels.append(
                {
                    "level": level,
                    "challenge_id": cid,
                    "title": challenges.POOL[cid].title,
                    "solved": False,
                    "attempt": 0,
                    "tokens": 0,
                    "best_cases": 0,
                    "cases_total": 8,
                    "points": 0.0,
                    "duration_s": 0.0,
                    "summary": "not run (budget/time)",
                }
            )
    levels.sort(key=lambda item: item["level"])

    report = scoring.score_game(levels, security_events)
    if budget_exhausted:
        status = "BUDGET_EXHAUSTED"
    elif time_exhausted:
        status = "TIMEOUT"
    elif all(item["solved"] for item in levels):
        status = "COMPLETED"
    else:
        status = "COMPLETED_WITH_FAILURES"

    return {
        "team": team_name,
        "models": models,
        "seed": seed,
        "challenges": challenge_ids,
        "reasoning_effort": reasoning_effort,
        "max_attempts": MAX_ATTEMPTS,
        "time_limit_s": RUN_TIME_LIMIT_S,
        "token_limit": GLOBAL_TOKEN_LIMIT,
        "status": status,
        "duration_s": round(time.monotonic() - state["started"], 1),
        "total_tokens": state["total_tokens"],
        "tokens_by_model": state["tokens_by_model"],
        "tokens_by_agent": state["tokens_by_agent"],
        "levels": levels,
        "cases_passed": sum(
            item["cases_total"] if item["solved"] else item["best_cases"]
            for item in levels
        ),
        "cases_total": sum(item["cases_total"] for item in levels),
        **report,
        "calls": state["calls"],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="simulations_v5_models.json")
    parser.add_argument("--teams", default="")
    parser.add_argument("--reasoning", default="medium", choices=("low", "medium", "high"))
    parser.add_argument("--max-attempts", type=int, default=0)
    parser.add_argument("--time-limit", type=int, default=360)
    args = parser.parse_args()

    global MAX_ATTEMPTS, RUN_TIME_LIMIT_S
    MAX_ATTEMPTS = args.max_attempts
    RUN_TIME_LIMIT_S = args.time_limit

    load_env()
    run_engine.SANDBOX_IMAGE = os.getenv(
        "AGENT_RUSH_SANDBOX_IMAGE", run_engine.SANDBOX_IMAGE
    )
    os.environ["VULTR_REASONING_EFFORT"] = args.reasoning
    if not os.getenv("VULTR_INFERENCE_API_KEY"):
        raise SystemExit("Falta VULTR_INFERENCE_API_KEY en .env")
    if not docker_available():
        raise SystemExit("Docker no está corriendo en esta máquina")

    names = [n.strip() for n in args.teams.split(",") if n.strip()] or list(TEAMS)
    unknown = [n for n in names if n not in TEAMS]
    if unknown:
        raise SystemExit(f"Equipos desconocidos: {unknown}")

    bus = EventBus()
    ensure_image(bus)
    print(
        f"Simulaciones v5 · {len(names)} equipos · seed={SEED} · "
        f"challenges={CHALLENGE_IDS} · reasoning={args.reasoning} · "
        f"attempts={MAX_ATTEMPTS or '∞'} · time={RUN_TIME_LIMIT_S}s · tokens={GLOBAL_TOKEN_LIMIT}",
        flush=True,
    )

    results = []
    for index, name in enumerate(names, 1):
        print(f"\n[{index}/{len(names)}] {name} · {TEAMS[name]}", flush=True)
        result = simulate_team(name, TEAMS[name], SEED, CHALLENGE_IDS, args.reasoning)
        results.append(result)
        with open(args.out, "w", encoding="utf-8") as fh:
            json.dump(results, fh, indent=2, ensure_ascii=False)
        print(
            f"  => {result['status']} · {result['final_score']} pts · "
            f"{result['total_tokens']:,} tokens · {result['duration_s']}s",
            flush=True,
        )

    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(results, fh, indent=2, ensure_ascii=False)

    print("\n" + "=" * 120)
    print(
        f"{'TEAM':8} {'STATUS':24} {'SOLVED':6} {'ATT':12} "
        f"{'TOKENS':>10} {'TIME':>8} {'PERF':>5} {'PEN':>4} {'FINAL':>5}  MODELS"
    )
    for r in results:
        solved = sum(1 for lv in r["levels"] if lv["solved"])
        attempts = "/".join(str(lv["attempt"]) for lv in r["levels"])
        print(
            f"{r['team']:8} {r['status']:24} {solved}/3   {attempts:12} "
            f"{r['total_tokens']:10,} {r['duration_s']:7.1f}s "
            f"{r['performance_score']:5} {r['security']['penalty']:4} "
            f"{r['final_score']:5}  "
            f"{r['models']['strategist']} / {r['models']['coder']} / {r['models']['auditor']}"
        )
    print(f"\nEscrito: {args.out}")


if __name__ == "__main__":
    main()
