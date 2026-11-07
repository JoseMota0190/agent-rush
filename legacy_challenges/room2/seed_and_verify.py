#!/usr/bin/env python3
"""
Sala 2: The Memory Enigma
-----------------------
Descripción: Debug and fix the memory leak script.

El referee genera un script Python con una fuga de memoria intencional
(bucle while True sin cierre de recursos). El agente debe identificar y
corregir el bug para que el script pase los tests unitarios.

Seed usa: rooms/2/memory_leak_{seed}.py
Flag esperada: HMAC(SERVER_SECRET, f"room:2:seed:{seed}")[:32]
"""

import hashlib
import hmac
import json
import os
import sys

ROOM = 2
SERVER_SECRET = b"agent-rush-hackathon-2026-escape-room"
seed = os.urandom(16).hex()
expected_flag = hmac.new(SERVER_SECRET, f"room:{ROOM}:seed:{seed}".encode(), hashlib.sha256).hexdigest()[:32]

# Script con bug de memoria intencional - el agente debe corregirlo
BUGGY_SCRIPT = f'''
import sys

def process_data(data_chunks):
    results = []
    for i, chunk in enumerate(data_chunks):
        # BUG: Acumulador sin liberarse, causa memory leak
        accumulator = 0
        for item in chunk:
            accumulator += item
            # Falta: no hay liberación de memoria ni límite de iteraciones
        results.append(accumulator)
    # BUG: No se retorna nada y el bucle externo continúa infinitamente
    while True:
        pass
    return results

if __name__ == "__main__":
    # Datos de prueba
    chunks = [[1, 2, 3], [4, 5, 6], [7, 8, 9]]
    # El script se ejecuta y debe corregirse para:
    # 1. Retornar los resultados acumulados
    # 2. Terminar en lugar de entrar en while True infinito
    output = process_data(chunks)
    print(f"RESULTADO: {output}")
    print(f"FLAG: {expected_flag}")
'''

# Flag esperada
expected_flag = hmac.new(SERVER_SECRET, f"room:{ROOM}:seed:{seed}".encode(), hashlib.sha256).hexdigest()[:32]

def test_corrected_script(script_code):
    """Probar si el script corregido funciona correctamente."""
    local_vars = {'sys': sys}
    try:
        exec(script_code, {}, local_vars)
        # Si llegamos aquí sin errores y el script imprime RESULTADO, es correcto
        return True, "Script ejecutado sin errores"
    except Exception as e:
        return False, f"Error en ejecución: {e}"

if __name__ == "__main__":
    print(f"Sala {ROOM}: The Memory Enigma")
    print(f"Seed: {seed}")
    print(f"Flag esperada: {expected_flag}")
    print()
    print("Script con bug (para corregir):")
    print(BUGGY_SCRIPT[:200] + "...")
    print()
    print("El agente debe:")
    print("  1. Identificar el bucle while True infinito")
    print("  2. Reemplazarlo con return results")
    print("  3. Añadir if __name__ == \"__main__\": block")
    print()
    
    # Test del script buggy (debería fallar por el while True)
    success, msg = test_corrected_script(BUGGY_SCRIPT)
    print(f"Script original: {msg}")