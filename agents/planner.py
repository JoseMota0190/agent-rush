"""
Agente Planificador (Strategist Agent).
Responsable de analizar el reto de cada sala y determinar la estrategia.
Output JSON con el enfoque planificado.
"""

import json
from typing import Dict, Any, Optional
from config.prompts import STRATEGIST_SYSTEM_PROMPT


class Strategist:
    """El cerebro de planificación del equipo."""
    
    def __init__(self, llm_client):
        self.llm = llm_client
    
    def plan_for_room(self, room_number: int, room_description: str, input_data: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Genera un plan estructurado para la sala dada.
        
        Returns dict con:
        - approach: estrategia descriptiva
        - reasoning: por qué eligió este enfoque
        - confidence: nivel de confianza (0-1)
        - suggested_tools: herramientas sugeridas (sandbox commands, etc.)
        """
        prompt = f"""
        Eres el Estratega Principal para el AI Escape Room.
        
        Descripción de la Sala {room_number}: {room_description}
        
        Datos de entrada disponibles: {json.dumps(input_data or {}, ensure_ascii=False)}
        
        Tu tarea:
        1. Analiza el problema y determina el mejor enfoque técnico
        2. Output UN solo enfoque técnico concreto
        3. Considera qué comandos Bash/Python serían más efectivos
        4. Sé directo y práctico
        
        Responde SOLO con un objeto JSON con estas claves:
        {{
            "approach": "tu estrategia técnica concreta",
            "reasoning": "por qué este enfoque",
            "confidence": 0.0-1.0,
            "suggested_command": "comando principal a ejecutar (opcional)"
        }}
        """
        
        response = self.llm.generate(
            system_prompt=STRATEGIST_SYSTEM_PROMPT,
            user_prompt=prompt
        )
        
        try:
            result = json.loads(response.strip())
            # Validar campos obligatorios
            if "approach" not in result:
                raise ValueError("Missing 'approach' in response")
            return result
        except (json.JSONDecodeError, ValueError) as e:
            # Fallback: estrategia por defecto
            return {
                "approach": "Análisis de logs con expresiones regulares para extraer patrones",
                "reasoning": f"Fallback por error de LLM: {str(e)}",
                "confidence": 0.3,
                "suggested_command": "python3 -c \"import re; ...\""
            }