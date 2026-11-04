"""
Constantes de presupuesto y límites de tokens para el sistema LLM.

Lee variables de entorno o usa valores predeterminados para configurar:
- Límite máximo de tokens por ejecución de agente.
- Límite máximo de tokens por llamada a la API.
- Modo de gestión del presupuesto ("hard" = bloquear si se excede, "soft" = solo advertir).
"""

import os

# Límite máximo de tokens por ejecución completa (ejecución del agente)
MAX_TOKENS_PER_RUN = int(os.getenv("MAX_TOKENS_PER_RUN", "100000"))

# Límite máximo de tokens por llamada individual a la API (prompt + completion)
MAX_TOKENS_PER_CALL = int(os.getenv("MAX_TOKENS_PER_CALL", "1200"))

# Modo de aplicación del presupuesto: "hard" = rechazar si se supera, "soft" = advertir solo
TOKEN_BUDGET_MODE = os.getenv("TOKEN_BUDGET_MODE", "hard").lower()

__all__ = [
    "MAX_TOKENS_PER_RUN",
    "MAX_TOKENS_PER_CALL",
    "TOKEN_BUDGET_MODE",
]