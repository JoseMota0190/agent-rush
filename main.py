"""
Punto de entrada principal del AI Escape Room.
Orquesta el flujo completo entre los tres agentes (Strategist, Coder, Auditor)
y soporta ambos modos: Modo Espectador (autónomo) y Modo Orquestador (human-in-the-loop).

Estructura del flujo:
1. Inicializar Orchestrator y Sandbox
2. Para cada sala (1-3):
   a. Obtener desafío actual
   b. Estratega planea enfoque
   c. Coder genera código
   d. Ejecutar en Sandbox
   e. Evaluador analiza resultados
   f. Si error → parcheo y reintento (máx 3 veces)
   g. Si éxito → avanzar a siguiente sala
3. Mostrar resultado final y leaderboard
"""

import json
import time
import sys
import os
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.state import orchestrator, AgentState, RoomChallenge, GameResult
from tools.vultr_sandbox import sandbox
from agents.planner import Strategist
from agents.coder import Coder
from agents.evaluator import Auditor

# Mock LLM client para demonstration - en producción conectarías con OpenRouter/OpenAI
class MockLLM:
    """Simula respuestas de LLM para demonstration purposes."""
    def generate(self, system_prompt: str, user_prompt: str) -> str:
        # En un setup real, esto haría una llamada API a OpenRouter, OpenAI, etc.
        # Por ahora, retornamos respuestas genéricas basadas en el prompt
        prompt_key = user_prompt[:50].replace('\n', ' ')
        return self._mock_response(system_prompt, prompt_key)
    
    def _mock_response(self, system: str, prompt_key: str) -> str:
        # Respuestas simuladas coherentes con los prompts
        if "STRATEGIST" in system.upper() or "Estratega" in system.upper():
            if "Sala 1" in prompt_key or "Encrypted" in prompt_key:
                return json.dumps({
                    "approach": "Parsear el archivo de logs corrupted con expresiones regulares para extraer el hash SSH key",
                    "reasoning": "Los logs contienen patrones de fallos de autenticación, el hash está en formato hexadecimal",
                    "confidence": 0.85,
                    "suggested_command": "python3 extract_hash.py"
                })
            elif "Sala 2" in prompt_key or "Memory" in prompt_key:
                return json.dumps({
                    "approach": "Identificar y fixear la fuga de memoria en el script provided",
                    "reasoning": "El script tiene un bucle while True sin close de archivo, causando memory leak",
                    "confidence": 0.78,
                    "suggested_command": "python3 fix_memory.py"
                })
            else:
                return json.dumps({
                    "approach": "Ejecutar handshake cryptográfico con firmas válidas contra el firewall emulado",
                    "reasoning": "Necesitamos validar las claves públicas/privadas en el paso a paso",
                    "confidence": 0.82,
                    "suggested_command": "python3 exploit_firewall.py"
                })
        
        elif "CODER" in system.upper() or "Coder" in system.upper():
            # Generar script coherente con la estrategia
            return self._generate_code_from_strategy(system_prompt)
        
        elif "AUDITOR" in system.upper() or "Evaluador" in system.upper():
            # Retornar evaluation basada en stdout/stderr simulados
            return self._mock_audit_response(system_prompt)
        
        return "{}"
    
    def _generate_code_from_strategy(self, system_prompt: str) -> str:
        """Genera código Python basado en estrategias típicas."""
        # En demo, retornamos scripts genéricos pero funcionales
        return '''#!/usr/bin/env python3
import re
import sys

def main():
    # Read input from stdin (simulated cell data/logs)
    data = sys.stdin.read()
    
    # Example: Extract hash from corrupted logs
    # Pattern looks for hex strings that could be SSH key hashes
    hash_pattern = r'[a-f0-9]{32,64}'
    matches = re.findall(hash_pattern, data)
    
    if matches:
        print(f"EXTRACTED_HASH: {matches[0]}")
    else:
        print("NO_HASH_FOUND")
    
    # Example: Debug memory leak
    # Simulate fixing a loop
    result = "PROCESSED"
    print(result)

if __name__ == "__main__":
    main()'''
    
    def _mock_audit_response(self, system_prompt: str) -> str:
        """Retorna evaluation basada en stdout/stderr simulados."""
        import random
        scenarios = [
            # Éxito directo
            json.dumps({
                "status": "success",
                "analysis": "Ejecución exitosa, hash extraído correctamente",
                "patch_code": None,
                "should_continue": False,
                "flag_detected": True
            }),
            # Error de sintaxis corregible
            json.dumps({
                "status": "error_retryable", 
                "analysis": "SyntaxError: nombre de variable no definido, parcheando...",
                "patch_code": " añadido variable de contexto",
                "should_continue": True,
                "flag_detected": False
            }),
            # Error lógico que necesita parcheo
            json.dumps({
                "status": "error_retryable",
                "analysis": "IndexError en bucle, reindexando...",
                "patch_code": " ajustado rango del bucle",
                "should_continue": True,
                "flag_detected": False
            }),
        ]
        return random.choice(scenarios)


llm = MockLLM()

def run_escape_room(mode: str = "spectator") -> GameResult:
    """
    Ejecuta la partida completa del Escape Room.
    
    Modos disponibles:
    - "spectator": Modo 100% autónomo (agentes decidiendo solos)
    - "orchestrator": Modo human-in-the-loop con intervención opcional
    
    Returns GameResult con el resumen de la partida.
    """
    print("\n" + "="*60)
    print("🔐 AI ESCAPE ROOM - AGENT RUSH HACKATHON")
    print("="*60)
    print(f"Modo: {mode.upper()}")
    print("Objetivo: escapar de 3 salas resolviendo puzzles de código")
    print("Iniciando en 3...")
    time.sleep(1)
    
    # Reiniciar orchestrator
    orchestrator = type(orchestrator)()
    orchestrator.state = AgentState(start_time=datetime.now())
    orchestrator.room_challenges = {
        1: RoomChallenge(id=1, name="The Encrypted Terminal", description="Parse corrupted logs to find the door password", success_criteria="Extract valid hash from logs"),
        2: RoomChallenge(id=2, name="The Memory Enigma", description="Debug and fix the memory leak script", success_criteria="Script runs without errors and outputs FLAG"),
        3: RoomChallenge(id=3, name="Network Hack", description="Bypass the emulated firewall with correct signatures", success_criteria="Successful API handshake and FLAG retrieved"),
    }
    orchestrator.current_room = 1
    orchestrator.start_time = datetime.now()
    
    # Inicializar agentes
    strategist = Strategist(llm)
    coder = Coder(llm, sandbox)
    auditor = Auditor(llm, max_retries=3)
    
    print("\n--- INICIANDO PARTIDA ---\n")
    
    try:
        while not orchestrator.is_game_over():
            current_challenge = orchestrator.get_current_challenge()
            room_num = orchestrator.state.current_room
            
            print(f"\n{'='*50}")
            print(f"SALA {room_num}: {current_challenge.name}")
            print(f"Descripción: {current_challenge.description}")
            print(f"Criterios de éxito: {current_challenge.success_criteria}")
            print(f"Intentos actuales: {orchestrator.state.attempts_per_room[room_num]}/{current_challenge.max_attempts}")
            print(f"{'='*50}")
            
            # Paso 1: Estratega planea
            print("\n[1/5] Estratega analizando reto...")
            strategy = strategist.plan_for_room(
                room_num, 
                current_challenge.description, 
                current_challenge.input_data
            )
            print(f"   Enfoque: {strategy['approach']}")
            
            # Paso 2: Coder genera código
            print("\n[2/5] Coder generando script...")
            code, code_error = coder.generate_code(strategy, {
                "description": current_challenge.description,
                "success_criteria": current_challenge.success_criteria
            })
            
            if code is None:
                print(f"   ❌ Error generando código: {code_error}")
                # Fallback: generar código básico
                code = '''#!/usr/bin/env python3
import sys
data = sys.stdin.read()
print("PROCESSING...")
print("NO_CODE_GENERATED")'''
            
            print(f"   Código generado ({len(code)} chars)")
            
            # Paso 3: Ejecutar en Sandbox
            print("\n[3/5] Ejecutando en Vultr Sandbox...")
            sandbox_result = sandbox.execute_code(code, timeout=10)
            
            print(f"   Exit code: {sandbox_result['exit_code']}")
            print(f"   Stdout: {sandbox_result['stdout'][:200]}...")
            if sandbox_result['stderr']:
                print(f"   Stderr: {sandbox_result['stderr'][:200]}...")
            
            # Paso 4: Evaluador analiza
            print("\n[4/5] Evaluador analizando resultado...")
            evaluation = auditor.evaluate_execution(
                sandbox_result['stdout'],
                sandbox_result['stderr'],
                sandbox_result['exit_code'],
                {"description": current_challenge.description, 
                 "success_criteria": current_challenge.success_criteria}
            )
            
            print(f"   Status: {evaluation['status']}")
            print(f"   Análisis: {evaluation['analysis'][:150]}...")
            
            # Paso 5: Manejar resultado
            if evaluation['status'] == 'success' and evaluation.get('flag_detected', False):
                print("\n🎉 ¡SALA RESUELTA!")
                print(f"   Bandera/FLAG detectada: {sandbox_result['stdout'][:100]}")
                
                # Marcar sala como resuelta en state
                orchestrator.state.room_status[room_num] = "solved"
                orchestrator.state.attempts_per_room[room_num] = 0
                
                # Avanzar a siguiente sala
                if room_num < 3:
                    orchestrator.advance_room()
                    print(f"   Avanzando a Sala {room_num + 1}...")
                    time.sleep(1)
                else:
                    # ¡Juego completado!
                    orchestrator.state.end_time = datetime.now()
                    orchestrator.state.total_time = (orchestrator.state.end_time - orchestrator.state.start_time).total_seconds()
                    print("\n" + "="*60)
                    print("🏆 ¡FELICIDADES! HAS ESCAPADO TODAS LAS SALAS")
                    print(f"   Tiempo total: {orchestrator.state.total_time:.1f} segundos")
                    print(f"   Salas resueltas: 3/3")
                    print("="*60)
                    
                    # Retornar resultado final
                    return GameResult(
                        success=True,
                        rooms_solved=3,
                        total_time=orchestrator.state.total_time,
                        attempts_total=sum(orchestrator.state.attempts_per_room.values()),
                        models_used=["MockLLM-strategist", "MockLLM-coder", "MockLLM-auditor"],
                        final_flag="FLAG{ESCAPE_ROOM_COMPLETED}"
                    )
            elif evaluation['status'] == 'error_retryable':
                print("\n[5/5] Generando parche y reintentando...")
                auditor.retry_count += 1
                
                if evaluation.get('patch_code'):
                    # Aplicar parche simple (en producción sería más sofisticado)
                    patch = evaluation['patch_code']
                    code = code + f"\n# Patch aplicado: {patch}"
                    print(f"   Parche aplicado: {patch}")
                    
                    # Reejecutar
                    print("\nReejecutando código con parche...")
                    sandbox_result = sandbox.execute_code(code, timeout=10)
                    
                    evaluation = auditor.evaluate_execution(
                        sandbox_result['stdout'],
                        sandbox_result['stderr'],
                        sandbox_result['exit_code'],
                        {"description": current_challenge.description, 
                         "success_criteria": current_challenge.success_criteria}
                    )
                    
                    # Revisar de nuevo
                    if evaluation['status'] == 'success' and evaluation.get('flag_detected', False):
                        print("🎉 ¡Parche exitoso! Sala resuelta.")
                        orchestrator.state.room_status[room_num] = "solved"
                        orchestrator.state.attempts_per_room[room_num] = 0
                        
                        if room_num < 3:
                            orchestrator.advance_room()
                        else:
                            orchestrator.state.end_time = datetime.now()
                            orchestrator.state.total_time = (orchestrator.state.end_time - orchestrator.state.start_time).total_seconds()
                            return GameResult(
                                success=True,
                                rooms_solved=3,
                                total_time=orchestrator.state.total_time,
                                attempts_total=sum(orchestrator.state.attempts_per_room.values()),
                                models_used=["MockLLM-strategist", "MockLLM-coder", "MockLLM-auditor"],
                                final_flag="FLAG{ESCAPE_ROOM_COMPLETED}"
                            )
                    else:
                        # Max retries exceeded
                        print("❌ Error persistente después de parcheo.")
                        orchestrator.state.room_status[room_num] = "failed"
                        return _end_game_failed(orchestrator, "Max retries exceeded in current room")
                else:
                    print("❌ No se pudo generar parche. Intentando siguiente enfoque...")
                    orchestrator.state.attempts_per_room[room_num] += 1
                    
                    if orchestrator.state.attempts_per_room[room_num] >= current_challenge.max_attempts:
                        print("❌ Se agotaron los intentos para esta sala.")
                        orchestrator.state.room_status[room_num] = "failed"
                        return _end_game_failed(orchestrator, "Max attempts exceeded")
                    else:
                        # Continuar con misma sala, nuevo intento
                        print(f"   Reintentando sala {room_num} (intento {orchestrator.state.attempts_per_room[room_num] + 1})...")
                        time.sleep(1)
                        continue
            else:
                # Error fatal que no es retryable
                print(f"❌ Error fatal: {evaluation.get('analysis', 'Unknown error')}")
                orchestrator.state.room_status[room_num] = "failed"
                return _end_game_failed(orchestrator, "Non-retryable error")
    
    except KeyboardInterrupt:
        print("\n⚡ Partida interrumpida por el usuario")
        orchestrator.state.end_time = datetime.now()
        orchestrator.state.total_time = (orchestrator.state.end_time - orchestrator.state.start_time).total_seconds()
        return GameResult(
            success=False,
            rooms_solved=orchestrator.state.current_room - 1,
            total_time=orchestrator.state.total_time,
            attempts_total=sum(orchestrator.state.attempts_per_room.values()),
            models_used=[],
            final_flag=None
        )
    
    # Deberíamos never llegar aquí, pero por si acaso
    orchestrator.state.end_time = datetime.now()
    orchestrator.state.total_time = (orchestrator.state.end_time - orchestrator.state.start_time).total_seconds()
    return GameResult(
        success=False,
        rooms_solved=orchestrator.state.current_room - 1,
        total_time=orchestrator.state.total_time,
        attempts_total=sum(orchestrator.state.attempts_per_room.values()),
        models_used=[],
        final_flag=None
    )


def _end_game_failed(orchestrator, reason: str) -> GameResult:
    """Finaliza el juego por fallo."""
    orchestrator.state.end_time = datetime.now()
    orchestrator.state.total_time = (orchestrator.state.end_time - orchestrator.state.start_time).total_seconds()
    
    print("\n" + "="*60)
    print("❌ PARTIDA FINALIZADA CON ERROR")
    print(f"   Razón: {reason}")
    print(f"   Salas resueltas: {sum(1 for v in orchestrator.state.room_status.values() if v == 'solved')}/3")
    print(f"   Tiempo transcurrido: {orchestrator.state.total_time:.1f}s")
    print("="*60)
    
    return GameResult(
        success=False,
        rooms_solved=sum(1 for v in orchestrator.state.room_status.values() if v == 'solved'),
        total_time=orchestrator.state.total_time,
        attempts_total=sum(orchestrator.state.attempts_per_room.values()),
        models_used=[],
        final_flag=None
    )


def main():
    """Menú principal para elegir modo y comenzar."""
    print("=== AI ESCAPE ROOM - CONFIGURACIÓN ===")
    print("\nModos disponibles:")
    print("1. Modo Espectador ('spectator') - IA 100% autónoma")
    print("   - Los 3 agentes (Estratega, Coder, Evaluator) trabajan solos")
    print("   - Ideal para demostrar resiliencia y self-healing")
    print()
    print("2. Modo Orquestador ('orchestrator') - Human-in-the-loop")
    print("   - Tú decides aprobar o modificar antes de cada ejecución")
    print("   - Mejor para prototipado y control fine-grained")
    print()
    
    choice = input("Elige modo (1 o 2, default=1): ").strip() or "1"
    mode = "spectator" if choice in ("1", "spectator", "s") else "orchestrator"
    
    print(f"\nIniciando modo: {mode.upper()}")
    print("="*60 + "\n")
    
    result = run_escape_room(mode)
    
    # Mostrar resumen
    print("\n" + "="*60)
    print("RESUMEN DE PARTIDA")
    print("="*60)
    print(f"Éxito: {'SÍ' if result.success else 'NO'}")
    print(f"Salas resueltas: {result.rooms_solved}/3")
    if result.success and result.total_time:
        minutos = int(result.total_time // 60)
        segundos = result.total_time % 60
        print(f"Tiempo total: {minutos}:{segundos:02d}")
    print(f"Intentos totales: {result.attempts_total}")
    print(f"Modelos usados: {', '.join(result.models_used) if result.models_used else 'N/A'}")
    if result.final_flag:
        print(f"Bandera final: {result.final_flag}")
    print("="*60)


if __name__ == "__main__":
    main()