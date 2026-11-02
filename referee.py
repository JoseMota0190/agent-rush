"""
Referee Determinista - Validador de flags y gestor de estado del juego.

Este es el corazón de la seguridad del sistema. El referee:
- NUNCA usa LLM para tomar decisiones
- Valida flags usando HMAC-SHA256 con secreto del servidor
- Es el ÚNICO autoridad para declarar "sala resuelta"
- Mantiene el estado event-sourced para replay y auditoría
"""

import hashlib
import hmac
import time
import json
from datetime import datetime, timezone
from collections import defaultdict

# Secreto del servidor (nunca se comparte con los agentes)
SERVER_SECRET = b"agent-rush-hackathon-2026-escape-room"

# Configuración de las salas
ROOMS_CONFIG = {
    1: {
        "name": "The Encrypted Terminal",
        "description": "Parse corrupted logs to find the door password",
        "success_criteria": "Extract valid hash from logs",
    },
    2: {
        "name": "The Memory Enigma", 
        "description": "Debug and fix the memory leak script",
        "success_criteria": "Script runs without errors and outputs FLAG",
    },
    3: {
        "name": "Network Hack",
        "description": "Bypass the emulated firewall with correct signatures", 
        "success_criteria": "Successful API handshake and FLAG retrieved",
    }
}

class GameReferee:
    """
    Referee determinista que valida el progreso del juego.
    
    Responsabilidades:
    1. Validar flags HMAC contra secretos server-side
    2. Avanzar de sala cuando se cumple el criteria
    3. Generar proofs criptográficos para leaderboard
    4. Auditar el historial de ejecuciones
    """
    
    def __init__(self, server_secret: bytes = SERVER_SECRET):
        self.server_secret = server_secret
        # Estado event-sourced: lista de eventos en orden cronológico
        self.event_log = []  # [(timestamp, event_type, data)]
        self.current_room = 1
        self.rooms_completed = 0
        self.total_attempts = defaultdict(int)
        self.start_time = datetime.now(timezone.utc)
        self.end_time = None
        
    def log_event(self, event_type: str, data: dict):
        """Registra un evento en el log append-only."""
        event = (datetime.now(timezone.utc), event_type, data)
        self.event_log.append(event)
    
    def generate_challenge_seed(self, room_num: int) -> dict:
        """
        Genera una seed criptográfica para una sala.
        La seed determina el desafío pero NO se revela a los agentes.
        """
        import os
        seed = os.urandom(16).hex()  # 32 hex chars = 128 bits de entropía
        # Derivar la flag esperada usando HMAC con el secreto server-side
        expected_flag = hmac.new(
            self.server_secret, 
            f"room:{room_num}:seed:{seed}".encode(), 
            hashlib.sha256
        ).hexdigest()[:32]  # Flag formateada como hex
        
        return {
            "seed": seed,
            "expected_flag": expected_flag,
            "room_num": room_num,
        }
    
    def validate_flag(self, room_num: int, player_flag: str, seed: str) -> dict:
        """
        Valida la flag de un jugador.
        
        Returns:
        - valid: bool
        - expected: la flag esperada (para debugging)
        - proof: proof object para el leaderboard
        """
        expected = hmac.new(
            self.server_secret, 
            f"room:{room_num}:seed:{seed}".encode(), 
            hashlib.sha256
        ).hexdigest()[:32]
        
        valid = hmac.compare_digest(player_flag, expected)
        
        self.log_event("flag_validated", {
            "room": room_num,
            "valid": valid,
            "player_flag": player_flag[:16] + "..." if len(player_flag) > 16 else player_flag,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        
        return {
            "valid": valid,
            "expected": expected,
            "proof": {
                "room": room_num,
                "seed": seed,
                "flag": expected,
                "validated_at": datetime.now(timezone.utc).isoformat(),
            }
        }
    
    def advance_room(self) -> dict:
        """Avanzar a la siguiente sala."""
        if self.current_room < 3:
            self.current_room += 1
            self.rooms_completed += 1
            return {
                "success": True,
                "new_room": self.current_room,
                "rooms_completed": self.rooms_completed,
            }
        else:
            return {
                "success": False,
                "error": "Ya completaste todas las salas",
            }
    
    def get_room_challenge(self, room_num: int) -> dict:
        """Obtener descripción del desafío de una sala."""
        return ROOMS_CONFIG.get(room_num, {})
    
    def get_stats(self) -> dict:
        """Estadísticas del juego."""
        return {
            "total_rooms": 3,
            "rooms_completed": self.rooms_completed,
            "current_room": self.current_room,
            "total_attempts": dict(self.total_attempts),
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "event_count": len(self.event_log),
        }
    
    def finish(self):
        """Marcar fin de partida."""
        self.end_time = datetime.now(timezone.utc)
        self.log_event("game_finished", {
            "total_rooms": self.rooms_completed,
            "final_stats": self.get_stats(),
        })


# Instancia global para uso en la aplicación
referee = GameReferee()