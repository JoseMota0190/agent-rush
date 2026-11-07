"""Trial real del banco v4 con un equipo de 3 modelos.

Uso:
    python bank_trial.py best
    python bank_trial.py worst
    python bank_trial.py best --seed trial-001

Cada trial juega UNA partida: `challenges.pick(seed)` elige un desafío por
nivel. El Strategist planifica, el Coder escribe la solución y el Auditor pide
parches. La solución corre en el sandbox Docker real y se gradúa en el host con
`challenges.grade`. El scoring se calcula con `scoring.py`.

Requiere Docker y VULTR_INFERENCE_API_KEY.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
CANDIDATE_ROOTS = [HERE, HERE.parent, HERE / "my-agent-system"]
for root in CANDIDATE_ROOTS:
    if (root / "run_engine.py").exists():
        sys.path.insert(0, str(root))
        break
sys.path.insert(0, str(HERE))

import challenges  # noqa: E402
import scoring  # noqa: E402
from run_engine import (  # noqa: E402
    EventBus,
    VultrChat,
    SANDBOX_FLAGS,
    SANDBOX_IMAGE,
    docker_available,
    ensure_image,
)


def run_bank_sandbox(code: str, bus: EventBus, timeout: int) -> dict:
    """Ejecuta el harness del banco pasando el código por stdin.

    `run_engine.run_sandbox` usa `python -c <code>`; con 8 casos grandes el
    argumento supera ARG_MAX. Acá usamos `python -` y enviamos el harness por
    stdin (el harness ya lleva los inputs embebidos).
    """
    if not docker_available():
        raise RuntimeError("Docker no está corriendo")
    ensure_image(bus)
    docker = shutil.which("docker")
    cmd = [docker, "run"] + SANDBOX_FLAGS + [SANDBOX_IMAGE, "python", "-"]
    started = time.time()
    proc = subprocess.run(
        cmd,
        input=code.encode("utf-8"),
        capture_output=True,
        timeout=timeout,
    )
    return {
        "stdout": proc.stdout.decode("utf-8", errors="replace")[:2_000_000],
        "stderr": proc.stderr.decode("utf-8", errors="replace")[-4000:],
        "exit_code": proc.returncode,
        "duration": round(time.time() - started, 2),
    }


def _load_env() -> None:
    for path in [HERE / ".env", HERE.parent / ".env", HERE / "my-agent-system" / ".env"]:
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


TEAMS = {
    "best": {
        "strategist": "deepseek-v4.1-flash-1017",
        "coder": "glm-5.3-flash",
        "auditor": "deepseek-v4.1-flash-1017",
    },
    "worst": {
        "strategist": "nemotron-3.5-content-safety",
        "coder": "muse-glimmer-30b",
        "auditor": "raon-1-mini-preview",
    },
}


def extract_solution(text: str):
    if not text:
        return None
    fence = re.search(r"```(?:python|py)?\s*(.*?)```", text, re.S | re.I)
    raw = fence.group(1) if fence else text
    try:
        compile(raw, "<solution>", "exec")
        return raw.strip()
    except (SyntaxError, ValueError):
        pass
    lines = text.splitlines()
    for start in range(len(lines)):
        candidate = "\n".join(lines[start:]).strip()
        try:
            compile(candidate, "<solution>", "exec")
            return candidate
        except (SyntaxError, ValueError):
            continue
    return None


def usage_tokens(usage: dict) -> int:
    if not isinstance(usage, dict):
        return 0
    if isinstance(usage.get("total_tokens"), (int, float)):
        return int(usage["total_tokens"])
    return int(usage.get("prompt_tokens", 0) or 0) + int(
        usage.get("completion_tokens", 0) or 0
    )


def run_trial(team_name: str, seed: str, model_overrides: dict | None = None) -> dict:
    _load_env()
    key = os.getenv("VULTR_INFERENCE_API_KEY", "").strip()
    if not key:
        raise SystemExit("Falta VULTR_INFERENCE_API_KEY")
    base = os.getenv("VULTR_INFERENCE_BASE_URL", "https://api.vultrinference.com/v1")
    chat = VultrChat(key, base)
    bus = EventBus()
    models = dict(TEAMS[team_name])
    if model_overrides:
        models.update({k: v for k, v in model_overrides.items() if v})

    picked = challenges.pick(seed)
    started = time.time()
    levels = []
    total_tokens = 0

    def ask(role: str, system: str, user: str, max_tokens: int) -> str:
        nonlocal total_tokens
        text, usage = chat.generate(models[role], system, user, max_tokens)
        total_tokens += usage_tokens(usage)
        return text

    for level, cid in zip((1, 2, 3), picked):
        view = challenges.public_view(cid)
        cases = challenges.build_cases(cid, seed)
        inputs = [inp for _, inp, _ in cases]
        level_tokens = 0
        before = total_tokens
        best_cases = 0
        solved = False
        attempt_used = 0
        summary = ""
        last_code = ""
        last_raw = ""
        last_stdout = ""
        last_stderr = ""

        try:
            plan = ask(
                "strategist",
                "You are the Strategist of an AI escape room. Give a concise, concrete plan. No code.",
                view + "\nReply with a short strategy (max 4 sentences).",
                600,
            )
            raw_code = ask(
                "coder",
                "You are the Coder. Your entire response must be valid Python 3.12 "
                "code. Do not include reasoning, analysis, prose or markdown fences. "
                "Read stdin and write stdout.",
                view + f"\nStrategist plan:\n{plan}",
                4000,
            )
            last_raw = raw_code
            code = extract_solution(raw_code)
        except Exception as exc:  # noqa: BLE001
            code = None
            summary = f"model error: {exc}"

        for attempt in range(1, challenges.MAX_ATTEMPTS + 1):
            attempt_used = attempt
            if code:
                try:
                    harness = challenges.harness_source(code, inputs)
                    result = run_bank_sandbox(
                        harness, bus, timeout=challenges.CONTAINER_TIMEOUT_S
                    )
                    verdict = challenges.grade(cid, seed, result.get("stdout", ""), cases)
                    best_cases = max(best_cases, 8 - len(verdict.failed))
                    summary = verdict.summary
                    last_code = code
                    last_stdout = (result.get("stdout") or "")[-1200:]
                    last_stderr = (result.get("stderr") or "")[-1200:]
                    if verdict.passed:
                        solved = True
                        break
                except Exception as exc:  # noqa: BLE001
                    summary = f"sandbox error: {exc}"
                    last_code = code
            else:
                best_cases = max(best_cases, 0)
                summary = summary or "no executable code"

            if attempt == challenges.MAX_ATTEMPTS:
                break

            try:
                patch = ask(
                    "auditor",
                    "You are the Auditor. Your entire response must be valid Python "
                    "3.12 code. No reasoning, no prose, no markdown fences.",
                    (
                        f"Challenge:\n{view}\n\nCurrent code:\n{code}\n\n"
                        f"Grading summary:\n{summary}\n\n"
                        "Return a complete self-contained Python 3.12 solution."
                    ),
                    2000,
                )
                last_raw = patch
                code = extract_solution(patch)
            except Exception as exc:  # noqa: BLE001
                summary = f"auditor error: {exc}"
                code = None

        level_tokens = total_tokens - before
        levels.append(
            {
                "level": level,
                "challenge_id": cid,
                "title": challenges.POOL[cid].title,
                "solved": solved,
                "attempt": attempt_used,
                "tokens": level_tokens,
                "best_cases": best_cases,
                "summary": summary,
                "last_code": last_code[-2000:],
                "last_raw": last_raw[-1500:],
                "last_stdout": last_stdout,
                "last_stderr": last_stderr,
            }
        )
        print(
            f"  L{level} {cid} {challenges.POOL[cid].title}: "
            f"{'SOLVED' if solved else 'FAILED'} attempt={attempt_used} "
            f"tokens={level_tokens} cases={best_cases}/8",
            flush=True,
        )

    report = scoring.score_game(levels, [])
    report.update(
        {
            "team": team_name,
            "models": models,
            "seed": seed,
            "challenges": picked,
            "levels": levels,
            "total_tokens": total_tokens,
            "duration_s": round(time.time() - started, 1),
        }
    )
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("team", choices=sorted(TEAMS))
    parser.add_argument("--seed", default="trial-2026-11-07")
    parser.add_argument("--out", default="bank_trial_results.json")
    parser.add_argument("--strategist")
    parser.add_argument("--coder")
    parser.add_argument("--auditor")
    args = parser.parse_args()

    overrides = {
        "strategist": args.strategist,
        "coder": args.coder,
        "auditor": args.auditor,
    }
    models = dict(TEAMS[args.team])
    models.update({k: v for k, v in overrides.items() if v})
    print(f"Trial {args.team} · seed={args.seed} · models={models}", flush=True)
    report = run_trial(args.team, args.seed, overrides)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=2, ensure_ascii=False)
    print(f"\nEscrito: {args.out}", flush=True)


if __name__ == "__main__":
    main()
