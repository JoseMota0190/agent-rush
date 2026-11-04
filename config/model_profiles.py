"""
Definiciones de perfiles para modelos LLM y utilidades de selección/guardado.

Proporciona una clase dataclass para representar un modelo asignado a un agente específico, junto con
sus parámetros específicos (temperatura, límites de tokens, URL de la API, etc.) y herramientas
para persistir la selección del usuario a través de sesiones.
"""

import json
import os
from dataclasses import dataclass, asdict
from typing import Dict, Any, Optional

# Importar constantes predeterminadas de modelos
from .models import AGENT_DEFAULTS

# Ruta del archivo de selección de perfil (almacenado en el mismo directorio)
SELECTION_FILE = os.path.join(os.path.dirname(__file__), "model_selection.json")
@dataclass
class ModelProfile:
    """
    Representa un modelo LLM asignado a un agente específico.

    Atributos:
        agent (str): Tipo de agente ("strategist", "coder" o "auditor").
        model_id (str): Identificador del modelo como se espera por la API.
        base_url (str): URL base de la API de inferencia (default: Vultr Inference).
        api_key_env (str): Nombre de la variable de entorno que contiene la clave de API.
        temperature (float): Factor de temperatura para el modelo de generación.
        max_tokens (int): Máximo de tokens permitidos por llamada.
    """

    agent: str
    model_id: str
    base_url: str = "https://api.vultrinference.com/v1"
    api_key_env: str = "VULTR_INFERENCE_API_KEY"
    temperature: float = 0.3
    max_tokens: int = 1000

    def to_dict(self) -> Dict[str, Any]:
        """Convierte el perfil a un diccionario plano (útil para serializar)."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ModelProfile":
        """Crea una instancia de ModelProfile a partir de un diccionario."""
        # Asegurar que los campos obligatorios existan
        agent = data.get("agent", "")
        model_id = data.get("model_id", "")
        # Cargar valores predeterminados para los campos opcionales si no están presentes
        defaults = {
            "base_url": "https://api.vultrinference.com/v1",
            "api_key_env": "VULTR_INFERENCE_API_KEY",
            "temperature": 0.3,
            "max_tokens": 1000,
        }
        kwargs = {"agent": agent, "model_id": model_id}
        for key, default_val in defaults.items():
            kwargs[key] = data.get(key, default_val)
        return cls(**kwargs)
# Perfiles predeterminados construidos a partir de AGENT_DEFAULTS (los modelos predeterminados)
DEFAULT_PROFILES: Dict[str, ModelProfile] = {
    agent: ModelProfile(agent=agent, model_id=model_id)
    for agent, model_id in AGENT_DEFAULTS.items()
}
def load_selection() -> Dict[str, "ModelProfile"]:
    """
    Carga los perfiles seleccionados por el usuario desde model_selection.json.

    Returns:
        Dict[str, ModelProfile]: Mapeo de agent -> perfil, con los valores por
        defecto aplicados para los agentes ausentes en el archivo.
    """
    profiles: Dict[str, "ModelProfile"] = {k: v for k, v in DEFAULT_PROFILES.items()}
    if not os.path.exists(SELECTION_FILE):
        return profiles
    try:
        with open(SELECTION_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            return profiles
        for agent, raw in data.items():
            if agent not in profiles:
                continue
            if isinstance(raw, str):
                profiles[agent] = ModelProfile(agent=agent, model_id=raw)
            elif isinstance(raw, dict):
                merged = profiles[agent].to_dict()
                for key in ("model_id", "base_url", "api_key_env", "temperature", "max_tokens"):
                    if key in raw:
                        merged[key] = raw[key]
                profiles[agent] = ModelProfile.from_dict(merged)
        return profiles
    except (json.JSONDecodeError, OSError):
        return profiles


def save_selection(selection: Dict[str, Any]) -> None:
    """
    Guarda la asignación seleccionada por el usuario en model_selection.json.

    Acepta tanto ModelProfile como diccionarios. Nunca guarda la API key.
    """
    payload: Dict[str, Dict[str, Any]] = {}
    for agent, prof in selection.items():
        data = prof.to_dict() if isinstance(prof, ModelProfile) else dict(prof)
        data.pop("api_key", None)
        payload[agent] = {
            key: data[key]
            for key in ("model_id", "base_url", "api_key_env", "temperature", "max_tokens")
            if key in data
        }
    os.makedirs(os.path.dirname(SELECTION_FILE), exist_ok=True)
    with open(SELECTION_FILE, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
def resolve_api_key(profile: ModelProfile) -> Optional[str]:
    """
    Obtiene la clave de API del entorno según la variable configurada en el perfil.

    Args:
        profile (ModelProfile): Perfil que contiene api_key_env.

    Returns:
        Optional[str]: El valor de la variable de entorno si existe, None en caso contrario.
    """
    return os.getenv(profile.api_key_env)