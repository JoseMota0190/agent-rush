"""
Punto de entrada principal del AI Escape Room (AGENT RUSH).

Integra:
- Selección de modelo por agente (3 IAs) con menú CLI y presets.
- Presupuesto de tokens por partida como "energía" del equipo (100k por defecto).
- Descalificación automática cuando la energía llega a cero (corte duro).
- Llamadas LLM vía Vultr Serverless Inference (modo estricto) o mock (desarrollo).
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime
from typing import Dict

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.budget import MAX_TOKENS_PER_RUN, MAX_TOKENS_PER_CALL
from config.models import discover_models, PRESETS
from config.model_profiles import (
    ModelProfile,
    DEFAULT_PROFILES,
    load_selection,
    save_selection,
    resolve_api_key,
)
from core.state import orchestrator, AgentState, RoomChallenge, GameResult, Orchestrator
from tools.vultr_sandbox import sandbox
from agents.planner import Strategist
from agents.coder import Coder
from agents.evaluator import Auditor
from llm.meter import TokenMeter, TokenBudgetExceeded
from llm.factory import build_all

AGENT_KEYS = ["strategist", "coder", "auditor"]

FALLBACK_CODE = """#!/usr/bin/env python3
import sys
data = sys.stdin.read()
print("PROCESSING...")
print("NO_CODE_GENERATED")"""


# ---- Cargar variables de .env (si existe) ----
def _load_env(path: str = ".env"):
    """Carga variables de un archivo .env sin depender de python-dotenv."""
    if not os.path.exists(path):
        return
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = value


_load_env()


# ---- Energía / contador ----
def print_energy(meter: TokenMeter) -> None:
    """Imprime el contador de energía (tokens) del equipo y por agente."""
    pct = (meter.used / meter.budget * 100) if meter.budget else 0.0
    snap = meter.snapshot()
    parts = " · ".join(f"{a[:5]} {snap.get(a, 0):,}" for a in AGENT_KEYS)
    print(f"   ENERGÍA equipo  {meter.used:,}/{meter.budget:,} tokens ({pct:.1f}%)  · {parts}")


def _models_used(profiles: Dict[str, ModelProfile]) -> list:
    return [f"{agent}:{profiles[agent].model_id}" for agent in AGENT_KEYS]


# ---- Utilidades de menú ----
def _safe_input(prompt: str, default: str = "") -> str:
    try:
        value = input(prompt)
    except EOFError:
        return default
    return value if value.strip() else default


def _print_models(models: list) -> None:
    for i, model in enumerate(models):
        print(f"  [{i}] {model['id']}  — {model.get('name', '')}")


def _choose_model_for_agent(agent: str, profile: ModelProfile, models: list) -> ModelProfile:
    print(f"\nAgente {agent} — modelo actual: {profile.model_id}")
    if models:
        _print_models(models)
    raw = _safe_input("  Número de la lista o id directo (Enter = mantener): ", "").strip()
    if not raw:
        return profile
    if raw.isdigit() and models and int(raw) < len(models):
        new_id = models[int(raw)]["id"]
    else:
        new_id = raw
    return ModelProfile(
        agent=agent,
        model_id=new_id,
        base_url=profile.base_url,
        api_key_env=profile.api_key_env,
        temperature=profile.temperature,
        max_tokens=profile.max_tokens,
    )


def menu_configurar_modelos(allow_mock: bool) -> Dict[str, ModelProfile]:
    """Menú interactivo para asignar un modelo a cada uno de los 3 agentes."""
    profiles = load_selection()
    models: list = []

    while True:
        print("\n=== CONFIGURACIÓN DE MODELOS (3 AGENTES) ===")
        print("  1. Ver modelos disponibles en Vultr (en vivo)")
        print("  2. Elegir modelo por agente")
        print("  3. Aplicar preset (balanced / fast / quality)")
        print("  4. Ver selección actual")
        print("  5. Guardar y continuar")
        if allow_mock:
            print("  0. Usar modo mock (solo desarrollo)")
        opt = _safe_input("Opción: ", "5").strip()

        if opt == "1":
            print("\nConsultando modelos en Vultr...")
            models = discover_models(api_key=os.getenv("VULTR_INFERENCE_API_KEY"))
            print(f"{len(models)} modelos de chat disponibles:")
            _print_models(models)
        elif opt == "2":
            for agent in AGENT_KEYS:
                profiles[agent] = _choose_model_for_agent(agent, profiles[agent], models)
        elif opt == "3":
            name = _safe_input("Preset (balanced/fast/quality): ", "balanced").strip().lower()
            if name in PRESETS:
                for agent in AGENT_KEYS:
                    base = profiles[agent]
                    profiles[agent] = ModelProfile(
                        agent=agent,
                        model_id=PRESETS[name][agent],
                        base_url=base.base_url,
                        api_key_env=base.api_key_env,
                        temperature=base.temperature,
                        max_tokens=base.max_tokens,
                    )
                print(f"Preset '{name}' aplicado.")
            else:
                print("Preset inválido.")
        elif opt == "4":
            for agent in AGENT_KEYS:
                p = profiles[agent]
                print(f"  {agent:10s} -> {p.model_id}  ({p.base_url})")
        elif opt == "0" and allow_mock:
            for agent in AGENT_KEYS:
                base = profiles[agent]
                profiles[agent] = ModelProfile(
                    agent=agent, model_id="mock",
                    base_url=base.base_url, api_key_env=base.api_key_env,
                    temperature=base.temperature, max_tokens=base.max_tokens,
                )
            print("Modo mock activado.")
            return profiles
        elif opt == "5":
            save_selection(profiles)
            return profiles
        else:
            print("Opción inválida.")


def _validate_vultr(profiles: Dict[str, ModelProfile], allow_mock: bool) -> None:
    """Modo estricto: los 3 agentes deben usar Vultr con API key válida."""
    if allow_mock:
        return
    problems = []
    for agent in AGENT_KEYS:
        p = profiles[agent]
        if not resolve_api_key(p):
            problems.append(f"{agent}: falta {p.api_key_env}")
        if "vultr" not in p.base_url.lower():
            problems.append(f"{agent}: base_url no es Vultr ({p.base_url})")
    if problems:
        print("\n❌ Configuración inválida (modo estricto Vultr):")
        for problem in problems:
            print("   -", problem)
        print("   Define VULTR_INFERENCE_API_KEY en .env o usa --allow-mock para desarrollo.")
        sys.exit(1)


# ---- Partida ----
def _build_orchestrator():
    orch = Orchestrator()
    orch.state = AgentState(start_time=datetime.now())
    orch.state.token_budget = MAX_TOKENS_PER_RUN
    orch.room_challenges = {
        1: RoomChallenge(
            id=1, name="The Encrypted Terminal",
            description="Parse corrupted logs to find the door password",
            success_criteria="Extract valid hash from logs",
        ),
        2: RoomChallenge(
            id=2, name="The Memory Enigma",
            description="Debug and fix the memory leak script",
            success_criteria="Script runs without errors and outputs FLAG",
        ),
        3: RoomChallenge(
            id=3, name="Network Hack",
            description="Bypass the emulated firewall with correct signatures",
            success_criteria="Successful API handshake and FLAG retrieved",
        ),
    }
    orch.current_room = 1
    orch.start_time = datetime.now()
    return orch


def run_escape_room(mode: str, profiles: Dict[str, ModelProfile], allow_mock: bool = False) -> GameResult:
    """Ejecuta la partida completa con presupuesto de energía por partida."""
    print("\n" + "=" * 60)
    print("🔐 AI ESCAPE ROOM - AGENT RUSH HACKATHON")
    print("=" * 60)
    print(f"Modo: {mode.upper()}")
    print("Objetivo: escapar de 3 salas resolviendo puzzles de código")
    print("Iniciando en 3...")
    time.sleep(0.5)

    orch = _build_orchestrator()

    meter = TokenMeter(MAX_TOKENS_PER_RUN, MAX_TOKENS_PER_CALL)
    llms = build_all(profiles, meter)
    strategist = Strategist(llms["strategist"])
    coder = Coder(llms["coder"], sandbox)
    auditor = Auditor(llms["auditor"], max_retries=3)

    print("\nModelos por agente:")
    for agent in AGENT_KEYS:
        print(f"   {agent:10s} -> {profiles[agent].model_id}  ({type(llms[agent].provider).__name__})")
    print_energy(meter)
    print("\n--- INICIANDO PARTIDA ---\n")

    def sync_state():
        orch.state.tokens_used = meter.used
        orch.state.tokens_by_agent = meter.snapshot()
        orch.state.token_budget = meter.budget

    def check_energy():
        if meter.remaining() <= 0:
            raise TokenBudgetExceeded(meter.used, meter.budget, "team", meter.mode)

    def finish(success: bool, reason: str = "") -> GameResult:
        orch.state.end_time = datetime.now()
        orch.state.total_time = (orch.state.end_time - orch.state.start_time).total_seconds()
        sync_state()
        return GameResult(
            success=success,
            rooms_solved=sum(1 for v in orch.state.room_status.values() if v == "solved"),
            total_time=orch.state.total_time,
            attempts_total=sum(orch.state.attempts_per_room.values()),
            models_used=_models_used(profiles),
            final_flag="FLAG{ESCAPE_ROOM_COMPLETED}" if success else None,
            tokens_used=meter.used,
            token_budget=meter.budget,
            disqualified=orch.state.disqualified,
        )

    try:
        while not orch.is_game_over():
            challenge = orch.get_current_challenge()
            room_num = orch.state.current_room

            print(f"\n{'=' * 50}")
            print(f"SALA {room_num}: {challenge.name}")
            print(f"Descripción: {challenge.description}")
            print(f"Criterios de éxito: {challenge.success_criteria}")
            print(f"Intentos actuales: {orch.state.attempts_per_room[room_num]}/{challenge.max_attempts}")
            print(f"{'=' * 50}")

            # Paso 1: Estratega
            check_energy()
            print("\n[1/5] Estratega analizando reto...")
            strategy = strategist.plan_for_room(room_num, challenge.description, challenge.input_data)
            print(f"   Enfoque: {strategy['approach']}")
            sync_state()
            print_energy(meter)

            # Paso 2: Coder
            check_energy()
            print("\n[2/5] Coder generando script...")
            code, code_error = coder.generate_code(strategy, {
                "description": challenge.description,
                "success_criteria": challenge.success_criteria,
            })
            if code is None:
                print(f"   ❌ Error generando código: {code_error}")
                code = FALLBACK_CODE
            print(f"   Código generado ({len(code)} chars)")
            sync_state()
            print_energy(meter)

            # Paso 3: Sandbox
            print("\n[3/5] Ejecutando en Vultr Sandbox...")
            sandbox_result = sandbox.execute_code(code, timeout=10)
            print(f"   Exit code: {sandbox_result['exit_code']}")
            print(f"   Stdout: {sandbox_result['stdout'][:200]}...")
            if sandbox_result["stderr"]:
                print(f"   Stderr: {sandbox_result['stderr'][:200]}...")

            # Paso 4: Auditor
            check_energy()
            print("\n[4/5] Evaluador analizando resultado...")
            evaluation = auditor.evaluate_execution(
                sandbox_result["stdout"],
                sandbox_result["stderr"],
                sandbox_result["exit_code"],
                {"description": challenge.description, "success_criteria": challenge.success_criteria},
            )
            print(f"   Status: {evaluation['status']}")
            print(f"   Análisis: {str(evaluation.get('analysis', ''))[:150]}...")
            sync_state()
            print_energy(meter)

            # Paso 5: Resultado
            if evaluation["status"] == "success" and evaluation.get("flag_detected", False):
                print("\n🎉 ¡SALA RESUELTA!")
                orch.state.room_status[room_num] = "solved"
                orch.state.attempts_per_room[room_num] = 0
                if room_num < 3:
                    orch.advance_room()
                    print(f"   Avanzando a Sala {room_num + 1}...")
                    time.sleep(0.5)
                else:
                    print("\n" + "=" * 60)
                    print("🏆 ¡FELICIDADES! HAS ESCAPADO TODAS LAS SALAS")
                    print("=" * 60)
                    return finish(True)

            elif evaluation["status"] in ("error_retryable", "success"):
                print("\n[5/5] Generando parche y reintentando...")
                auditor.retry_count += 1
                patch = evaluation.get("patch_code")

                if patch:
                    code_patched = code + f"\n# Patch aplicado: {patch}"
                    print(f"   Parche aplicado: {patch}")
                    print("\nReejecutando código con parche...")
                    sandbox_result = sandbox.execute_code(code_patched, timeout=10)
                    check_energy()
                    evaluation = auditor.evaluate_execution(
                        sandbox_result["stdout"],
                        sandbox_result["stderr"],
                        sandbox_result["exit_code"],
                        {"description": challenge.description, "success_criteria": challenge.success_criteria},
                    )
                    sync_state()

                    if evaluation["status"] == "success" and evaluation.get("flag_detected", False):
                        print("🎉 ¡Parche exitoso! Sala resuelta.")
                        orch.state.room_status[room_num] = "solved"
                        orch.state.attempts_per_room[room_num] = 0
                        if room_num < 3:
                            orch.advance_room()
                        else:
                            return finish(True)
                    else:
                        print("❌ Error persistente después de parcheo.")
                        orch.state.room_status[room_num] = "failed"
                        return finish(False, "Max retries exceeded")
                else:
                    orch.state.attempts_per_room[room_num] += 1
                    if orch.state.attempts_per_room[room_num] >= challenge.max_attempts:
                        print("❌ Se agotaron los intentos para esta sala.")
                        orch.state.room_status[room_num] = "failed"
                        return finish(False, "Max attempts exceeded")
                    print(f"   Reintentando sala {room_num}...")
                    time.sleep(0.5)
                    continue
            else:
                print(f"❌ Error fatal: {evaluation.get('analysis', 'Unknown error')}")
                orch.state.room_status[room_num] = "failed"
                return finish(False, "Non-retryable error")

    except TokenBudgetExceeded as exc:
        sync_state()
        orch.state.disqualified = True
        orch.state.room_status[orch.state.current_room] = "failed"
        print("\n" + "!" * 60)
        print("💀 EQUIPO DESCALIFICADO — SIN ENERGÍA")
        print(f"   Energía agotada: {exc.used:,}/{exc.budget:,} tokens")
        print("   El equipo no pudo completar el escape.")
        print("!" * 60)
        return finish(False, "token budget exceeded")

    except KeyboardInterrupt:
        print("\n⚡ Partida interrumpida por el usuario")
        return finish(False, "interrupted")

    return finish(False, "unknown")


def _print_summary(result: GameResult) -> None:
    print("\n" + "=" * 60)
    print("RESUMEN DE PARTIDA")
    print("=" * 60)
    print(f"Éxito: {'SÍ' if result.success else 'NO'}")
    print(f"Salas resueltas: {result.rooms_solved}/3")
    if result.total_time:
        minutes = int(result.total_time // 60)
        seconds = int(result.total_time % 60)
        print(f"Tiempo total: {minutes}:{seconds:02d}")
    print(f"Intentos totales: {result.attempts_total}")
    print(f"Modelos usados: {', '.join(result.models_used) if result.models_used else 'N/A'}")
    if result.token_budget:
        pct = result.tokens_used / result.token_budget * 100
        print(f"Energía: {result.tokens_used:,}/{result.token_budget:,} tokens ({pct:.1f}%)")
    if result.disqualified:
        print("Estado: DESCALIFICADO (sin energía)")
    if result.final_flag:
        print(f"Bandera final: {result.final_flag}")
    print("=" * 60)


def _apply_preset(profiles: Dict[str, ModelProfile], preset: str) -> Dict[str, ModelProfile]:
    for agent in AGENT_KEYS:
        base = profiles[agent]
        profiles[agent] = ModelProfile(
            agent=agent,
            model_id=PRESETS[preset][agent],
            base_url=base.base_url,
            api_key_env=base.api_key_env,
            temperature=base.temperature,
            max_tokens=base.max_tokens,
        )
    save_selection(profiles)
    return profiles


def main() -> None:
    parser = argparse.ArgumentParser(description="AGENT RUSH — AI Escape Room")
    parser.add_argument("--mode", choices=["spectator", "orchestrator"], default="spectator")
    parser.add_argument("--allow-mock", action="store_true", help="Permite modo mock sin Vultr (desarrollo)")
    parser.add_argument("--no-menu", action="store_true", help="No abrir el menú interactivo")
    parser.add_argument("--preset", choices=list(PRESETS.keys()), default=None)
    args = parser.parse_args()

    print("=== AI ESCAPE ROOM - CONFIGURACIÓN ===")
    profiles = load_selection()

    if args.preset:
        profiles = _apply_preset(profiles, args.preset)
        print(f"Preset aplicado: {args.preset}")
    elif not args.no_menu:
        profiles = menu_configurar_modelos(args.allow_mock)

    _validate_vultr(profiles, args.allow_mock)
    result = run_escape_room(args.mode, profiles, args.allow_mock)
    _print_summary(result)


if __name__ == "__main__":
    main()
