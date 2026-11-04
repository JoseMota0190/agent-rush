"""
Core module del sistema: Orchestrator y State Management.
Define el contrato de datos estricto y la lógica de routing entre agentes.
Usa Pydantic para tipos fuertes y gestión explícita del estado.
"""

from pydantic import BaseModel, Field
from typing import Literal, Optional, Dict, Any
from datetime import datetime
import json

# ---- STATE MODELS ----

class AgentState(BaseModel):
    """Estado global compartido entre todos los agentes."""
    version: str = "1.0.0"
    current_room: int = 1  # 1, 2, or 3
    room_status: Dict[int, Literal["pending", "in_progress", "solved", "failed"]] = Field(default_factory=lambda: {1: "pending", 2: "pending", 3: "pending"})
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    total_time: Optional[float] = None
    attempts_per_room: Dict[int, int] = Field(default_factory=lambda: {1: 0, 2: 0, 3: 0})
    model_usage: Dict[str, int] = Field(default_factory=dict)  # track token usage per model
    token_budget: int = 0
    tokens_used: int = 0
    tokens_by_agent: Dict[str, int] = Field(default_factory=dict)
    disqualified: bool = False
    
    class Config:
        frozen = False  # Allow updates but structured


class RoomChallenge(BaseModel):
    """Descripción de un reto de sala (caja negra - la IA no ve el código del servidor)."""
    id: int
    name: str
    description: str
    input_data: Optional[Dict[str, Any]] = None  # Lo que la IA puede leer/usar
    success_criteria: str  # Qué significa "resuelto"
    max_attempts: int = 5
    current_attempts: int = 0


class AgentAction(BaseModel):
    """Acción específica de un agente."""
    agent_type: Literal["strategist", "coder", "auditor"]
    room_id: int
    action: str  # "analyze", "generate_code", "evaluate", "patch"
    payload: Optional[Dict[str, Any]] = None
    timestamp: datetime = Field(default_factory=datetime.now)
    model_used: str  # Nombre del modelo LLM


class GameResult(BaseModel):
    """Resultado final de una partida completada."""
    success: bool
    rooms_solved: int
    total_time: float
    attempts_total: int
    models_used: list
    final_flag: Optional[str] = None
    tokens_used: int = 0
    token_budget: int = 0
    disqualified: bool = False


# ---- ORCHESTRATOR LOGIC ----

class Orchestrator:
    """Supervisor central que mantiene el estado y decide el flujo."""
    
    def __init__(self):
        self.state = AgentState(start_time=datetime.now())
        self.room_challenges = {
            1: RoomChallenge(id=1, name="The Encrypted Terminal", description="Parse corrupted logs to find the door password", success_criteria="Extract valid hash from logs"),
            2: RoomChallenge(id=2, name="The Memory Enigma", description="Debug and fix the memory leak script", success_criteria="Script runs without errors and outputs FLAG"),
            3: RoomChallenge(id=3, name="Network Hack", description="Bypass the emulated firewall with correct signatures", success_criteria="Successful API handshake and FLAG retrieved"),
        }
        self.current_agent: Optional[str] = None  # quién está activo ahora
    
    def get_current_challenge(self) -> RoomChallenge:
        """Retorna el reto actual de la sala."""
        return self.room_challenges[self.state.current_room]
    
    def advance_room(self) -> None:
        """Avanzar a la siguiente sala."""
        if self.state.current_room < 3:
            self.state.current_room += 1
            self.state.room_status[self.state.current_room] = "pending"
            self.state.attempts_per_room[self.state.current_room] = 0
    
    def reset_room(self) -> None:
        """Reiniciar la sala actual (mantenemos el número de sala)."""
        self.state.room_status[self.state.current_room] = "pending"
        self.state.attempts_per_room[self.state.current_room] = 0
    
    def record_attempt(self) -> None:
        """Incrementar contador de intentos de la sala actual."""
        self.state.attempts_per_room[self.state.current_room] += 1
    
    def is_game_over(self) -> bool:
        """Verificar si se completaron las 3 salas o se agotaron intentos."""
        if self.state.current_room > 3:
            return True
        current = self.get_current_challenge()
        if self.state.attempts_per_room[self.state.current_room] >= current.max_attempts:
            return True
        return False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertir estado a diccionario para serialización."""
        return {
            "version": self.state.version,
            "current_room": self.state.current_room,
            "room_status": {k: v for k, v in self.state.room_status.items()},
            "start_time": self.state.start_time.isoformat() if self.state.start_time else None,
            "end_time": self.state.end_time.isoformat() if self.state.end_time else None,
            "total_time": self.state.total_time,
            "attempts_per_room": self.state.attempts_per_room,
            "model_usage": self.state.model_usage,
        }


# ---- STATE INSTANCE ----

# Instancia global del orquestador (se inicializa en main.py)
orchestrator = Orchestrator()