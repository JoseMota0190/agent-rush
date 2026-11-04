"""
Monitoreo y aplicación del presupuesto de tokens para las llamadas a LLM.

Proporciona un contador thread-safe que registra el consumo de tokens por agente,
verifica los límites configurados y lanza una excepción si se supera el límite,
según el modo de presupuesto (hard vs soft).
"""

import threading
from typing import Dict, Any
from config.budget import MAX_TOKENS_PER_RUN, TOKEN_BUDGET_MODE
class TokenBudgetExceeded(Exception):
    """Excepción lanzada cuando el presupuesto total de tokens se excede en modo hard."""

    def __init__(self, used: int, budget: int, agent: str, mode: str):
        self.used = used
        self.budget = budget
        self.agent = agent
        self.mode = mode
        super().__init__(
            f"TokenBudgetExceeded: agente '{agent}' ha usado {used} tokens, superando el límite de {budget} tokens en modo '{mode}'."
        )
class TokenMeter:
    """
    Contador thread-safe de tokens usados por agente.

    Campos:
        budget (int): Límite máximo total de tokens por ejecución.
        max_per_call (int): Límite máximo de tokens por llamada (enviado al modelo).
        used (int): Total de tokens usados hasta el momento.
        per_agent (Dict[str, int]): Tokens usados por agente.
        mode (str): "hard" o "soft".
        _lock (threading.Lock): Protección para actualizaciones concurrentes.

    Métodos:
        remaining(): int – tokens restantes antes de alcanzar el límite.
        snapshot(): Dict[str, int] – copia del consumo actual por agente.
        add(agent: str, usage: Dict[str, Any]) – registra el usage (prompt+completion) para un agente.
        disqualified (propiedad): Si el límite total de hard se excede.
    """

    def __init__(self, budget: int, max_per_call: int = 1200):
        self.budget = budget
        self.max_per_call = max_per_call
        self.mode = TOKEN_BUDGET_MODE
        self.used = 0
        self.per_agent: Dict[str, int] = {}
        self._lock = threading.Lock()

    def remaining(self) -> int:
        """Retorna los tokens restantes antes de alcanzar el límite total."""
        with self._lock:
            return max(0, self.budget - self.used)

    def snapshot(self) -> Dict[str, int]:
        """Retorna una copia del consumo actual por agente."""
        with self._lock:
            return self.per_agent.copy()

    def add(self, agent: str, usage: Dict[str, Any]) -> None:
        """
        Suma los tokens usados desde la entrada `usage` al contador.

        El diccionario `usage` puede contener las claves 'prompt_tokens' y/o 'completion_tokens'.
        Si alguna de estas claves no está presente, se asume 0.
        En modo hard, lanza TokenBudgetExceeded si el total excede el límite después de agregar.

        Args:
            agent (str): Identificador del agente que generó el uso.
            usage (Dict[str, Any]): Uso reportado por la llamada LLM.
        """
        prompt_tokens = usage.get("prompt_tokens", 0)
        completion_tokens = usage.get("completion_tokens", 0)
        total_tokens = prompt_tokens + completion_tokens

        with self._lock:
            self.per_agent[agent] = self.per_agent.get(agent, 0) + total_tokens
            self.used += total_tokens

            if self.mode == "hard" and self.used > self.budget:
                raise TokenBudgetExceeded(
                    used=self.used,
                    budget=self.budget,
                    agent=agent,
                    mode=self.mode,
                )

    @property
    def disqualified(self) -> bool:
        """
        Indica si el presupuesto total de hard se ha excedido.

        Returns:
            bool: True si el modo es "hard" y se ha superado el presupuesto total.
        """
        if self.mode != "hard":
            return False
        with self._lock:
            return self.used > self.budget