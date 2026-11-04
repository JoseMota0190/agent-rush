"""
Módulo de modelos Vultr Inference API.

Proporciona funciones para descubrir modelos disponibles y devuelve un conjunto de respaldo
cuando la API no está disponible o falla.
"""

import json
import urllib.error
import urllib.request
import os
from typing import List, Dict, Any, Optional

# Modelos de respaldo cuando falla la conexión a la API
FALLBACK_CHAT_MODELS: List[Dict[str, str]] = [
    {"id": "deepseek-v4.1-flash-1017", "name": "deepseek-v4.1-flash-1017", "description": "Modelo de chat de alto rendimiento"},
    {"id": "glm-5.3", "name": "glm-5.3", "description": "Modelo GLM 5.3 para generación"},
    {"id": "glm-5.3-flash", "name": "glm-5.3-flash", "description": "Versión rápida del modelo GLM 5.3"},
    {"id": "qwen3.8-27b", "name": "qwen3.8-27b", "description": "Modelo Qwen 3.8 con 27 mil millones de parámetros"},
    {"id": "qwen3.8-flash-next", "name": "qwen3.8-flash-next", "description": "Versión flash del modelo Qwen 3.8"},
    {"id": "mimo-v2.6-pro", "name": "mimo-v2.6-pro", "description": "Modelo MIMO v2.6 Pro para tareas complejas"},
    {"id": "mimo-v2.6-flash", "name": "mimo-v2.6-flash", "description": "Modelo MIMO v2.6 Flash para respuestas rápidas"},
    {"id": "minimax-h3", "name": "minimax-h3", "description": "Modelo Minimax H3 para razonamiento"},
    {"id": "muse-glimmer-30b", "name": "muse-glimmer-30b", "description": "Modelo Muse Glimmer con 30 mil millones de parámetros"},
    {"id": "nemotron-3-nano-omni-30b-a3b-reasoning", "name": "nemotron-3-nano-omni-30b-a3b-reasoning", "description": "Modelo Nemotron 3 Nano Omni para razonamiento y tareas generales"},
]

# Modelos predeterminados para cada agente (usados cuando no se ha seleccionado ningún modelo específico)
AGENT_DEFAULTS: Dict[str, str] = {
    "strategist": "deepseek-v4.1-flash-1017",
    "coder": "qwen3.8-27b",
    "auditor": "nemotron-3-nano-omni-30b-a3b-reasoning",
}

# Conjuntos preestablecidos de asignaciones de modelos para diferentes objetivos
PRESETS: Dict[str, Dict[str, str]] = {
    "balanced": {
        "strategist": "deepseek-v4.1-flash-1017",
        "coder": "qwen3.8-27b",
        "auditor": "nemotron-3-nano-omni-30b-a3b-reasoning",
    },
    "fast": {
        "strategist": "deepseek-v4.1-flash-1017",
        "coder": "glm-5.3-flash",
        "auditor": "minimax-h3",
    },
    "quality": {
        "strategist": "nemotron-3-nano-omni-30b-a3b-reasoning",
        "coder": "muse-glimmer-30b",
        "auditor": "qwen3.8-27b",
    },
}


def discover_models(api_key: Optional[str] = None, base_url: str = "https://api.vultrinference.com/v1", timeout: int = 20) -> List[Dict[str, str]]:
    """
    Descubre modelos de chat disponibles desde la API de Vultr Inference.

    Args:
        api_key (Optional[str]): Clave de autorización opcional para la API (no requerida para esta enpoint).
        base_url (str): URL base de la API de Vultr Inference.
        timeout (int): Timeout en segundos para la petición HTTP.

    Returns:
        List[Dict[str, str]]: Lista de diccionarios con claves 'id', 'name' y 'description'.
                              Si la petición falla, devuelve FALLBACK_CHAT_MODELS formateados igual.
    """
    url = f"{base_url.rstrip('/')}/models"
    headers = {}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    req = urllib.request.Request(url, headers=headers)

    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            models_raw = data.get("data", [])
            result = []
            for item in models_raw:
                # Filtrar solo modelos de chat
                if "output_modalities" in item:
                    # Incluir solo si algún output_modality tiene type == "text"
                    modalities = item.get("output_modalities", [])
                    if not any(m.get("type") == "text" for m in modalities):
                        continue
                # Agregar modelo
                model_id = item.get("id")
                if not model_id:
                    continue
                result.append({
                    "id": model_id,
                    "name": item.get("name", model_id),
                    "description": item.get("description", ""),
                })
            return result
    except (urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError, KeyError, OSError):
        # Si falla la petición, devolver el conjunto de respaldo
        return FALLBACK_CHAT_MODELS.copy()