#!/usr/bin/env python3
"""
Sala 1: The Encrypted Terminal
-----------------------
Descripción: Parse corrupted logs to find the door password.

El referee genera una seed. El archivo de logs es corrupto y contiene
varios hashs SSH incorrectos. El agente debe usar expresiones regulares
para extraer el hash correcto que coincida con la flag esperada.

Seed usa: rooms/1/logs_corruptos_{seed}.log
Flag esperada: HMAC(SERVER_SECRET, f"room:1:seed:{seed}")[:32]
"""

import hashlib
import hmac
import json
import os
import re
import sys

# Simulación de datos del desafío (en producción real, estos vendrían del referee)
ROOM = 1

# Generar seed y flag esperada (esto lo hace el referee)
SERVER_SECRET = b"agent-rush-hackathon-2026-escape-room"
seed = os.urandom(16).hex()
expected_flag = hmac.new(SERVER_SECRET, f"room:{ROOM}:seed:{seed}".encode(), hashlib.sha256).hexdigest()[:32]

# Archivo de logs "corrupto" - en producción real, esto tendría errores intencionales
# Aquí simulamos con datos estructurados
log_data = f"""
2024-01-15 10:30:21 ERROR SSH attempted with key SHA256:{aabbccdd11223344}
2024-01-15 10:30:22 ERROR SSH failed password for root from 192.168.1.100
2024-01-15 10:30:23 ERROR SSH authentication failed for user admin
2024-01-15 10:30:24 ERROR SSH key SHA256: {expected_flag} does not match any known key
2024-01-15 10:30:25 ERROR SSH session timeout
2024-01-15 10:30:26 ERROR SSH connection reset by peer
2024-01-15 10:30:27 ERROR SSH invalid user
2024-01-15 10:30:28 ERROR SSH permission denied
2024-01-15 10:30:29 ERROR SSH too many authentication failures
2024-01-15 10:30:30 ERROR SSH public key timeout
"""

# Patrón para extraer hashes SSH (formato hexadecimal de 64 caracteres)
SSH_KEY_PATTERN = r'SHA256:([a-f0-9]{64})'

def find_correct_hash(log_text, expected_flag):
    """Encontrar el hash que coincide con la flag esperada."""
    matches = re.findall(SSH_KEY_PATTERN, log_text)
    print(f"Encontrados {len(matches)} hashes potenciales en los logs")
    
    for hash_val in matches:
        if hash_val == expected_flag:
            print(f"✓ Hash correcto encontrado: {hash_val}")
            return hash_val
    
    print("✗ Ningún hash coincidió con la flag esperada")
    print(f"Flag esperada: {expected_flag}")
    return None

if __name__ == "__main__":
    print(f"Sala {ROOM}: The Encrypted Terminal")
    print(f"Seed: {seed}")
    print(f"Flag esperada: {expected_flag}")
    print()
    print("Archivo de logs simulado:")
    print(log_data)
    print()
    
    result = find_correct_hash(log_data, expected_flag)
    if result:
        print(f"\nÉxito! Extraíste la bandera: {result}")
    else:
        print("\nFallo: No se encontró el hash correcto")
        sys.exit(1)