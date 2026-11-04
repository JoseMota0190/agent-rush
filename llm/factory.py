"""
Factory para construir clientes LLM instrumentados y con control de presupuesto.

Proporciona utilidades para construir instancias de LLM instrumentadas por agente basadas en perfiles
incluyendo soporte para tanto VultrLLM real como un cliente simulado de respaldo cuando no hay clave de API.
"""

from typing import Dict, Any
from config.model_profiles import ModelProfile, resolve_api_key
from llm.vultr import VultrLLM, MockLLM
from llm.meter import TokenMeter, TokenBudgetExceeded
from config.budget import MAX_TOKENS_PER_RUN, MAX_TOKENS_PER_CALL
class MeteredLLM:
    """Envuelve un cliente LLM con aplicación del presupuesto de tokens."""

    def __init__(self, provider: Any, meter: TokenMeter, agent_name: str, max_per_call: int = 1200):
        """
        Args:
            provider: Un cliente LLM que implementa generate_with_usage(...).
            meter: TokenMeter instance que rastrea el uso.
            agent_name: Identificador del agente ("strategist", "coder", "auditor").
            max_per_call (int): Límite de tokens por llamada. Si meter.remaining() es menor, se usará ese valor.
        """
        self.provider = provider
        self.meter = meter
        self.agent_name = agent_name
        self.max_per_call = max_per_call

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        """
        Genera texto, aplicando el presupuesto antes de hacer la llamada.

        Raises:
            TokenBudgetExceeded: Si el límite hard se excedió previamente o si la remaining() actual es 0.
        """
        allowed = min(self.max_per_call, self.meter.remaining())
        if allowed <= 0:
            raise TokenBudgetExceeded(used=self.meter.used, budget=self.meter.budget, agent=self.agent_name, mode=self.meter.mode)
        text, usage = self.provider.generate_with_usage(system_prompt, user_prompt, max_tokens=allowed)
        self.meter.add(self.agent_name, usage)
        return text
def build_all(profiles: Dict[str, ModelProfile], meter: TokenMeter) -> Dict[str, MeteredLLM]:
    """
    Construye una instancia de MeteredLLM por cada perfil de agente, seleccionando
    el proveedor adecuado según si hay una clave de API resuelta.

    Args:
        profiles (Dict[str, ModelProfile]): Mapeo de agent -> ModelProfile.
        meter (TokenMeter): TokenMeter compartido para todos los agentes.

    Returns:
        Dict[str, MeteredLLM]: Instancias instrumentadas listas para su uso.
    """
    result: Dict[str, MeteredLLM] = {}
    for agent, profile in profiles.items():
        api_key = resolve_api_key(profile)
        if api_key:
            # Usar el proveedor real de Vultr
            provider = VultrLLM(api_key=api_key, base_url=profile.base_url, model=profile.model_id)
        else:
            # Usar el simulado cuando no hay clave
            provider = MockLLM()
        metered = MeteredLLM(provider, meter, agent, max_per_call=profile.max_tokens)
        result[agent] = metered
    return result