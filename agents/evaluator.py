"""
Agente Evaluador / Self-Healing Agent.
Inspecciona la ejecución en el Sandbox y gestiona la autocorrección.
"""

import json
from typing import Dict, Any, Optional, Tuple
from config.prompts import AUDITOR_SYSTEM_PROMPT


class Auditor:
    """Evalúa resultados y genera parches automáticos."""
    
    def __init__(self, llm_client, max_retries: int = 3):
        self.llm = llm_client
        self.max_retries = max_retries
        self.retry_count = 0
    
    def evaluate_execution(self, stdout: str, stderr: str, exit_code: int, 
                          room_challenge: Dict[str, Any]) -> Dict[str, Any]:
        """
        Evalúa la salida de la ejecución y determina la acción siguiente.
        
        Returns dict con:
        - status: "success", "error_retryable", "error_fatal"
        - analysis: análisis del resultado
        - patch_code: código parcheado si es necesario (o None)
        - should_continue: booleano para seguir Intentando
        """
        # Si éxito absoluto
        if exit_code == 0 and not stderr:
            return {
                "status": "success",
                "analysis": "Ejecución exitosa sin errores",
                "patch_code": None,
                "should_continue": False,
                "flag_detected": self._check_for_flag(stdout)
            }
        
        # Si fallo, generar análisis con LLM
        prompt = f"""
        Eres el Agente Evaluador para el AI Escape Room.
        
        Resultado de ejecución:
        - Exit code: {exit_code}
        - Stdout: {stdout[-500:] if stdout else 'empty'}
        - Stderr: {stderr[-500:] if stderr else 'empty'}
        
        Desafío de la Sala: {room_challenge.get('description', 'Unknown')}
        Criterios de éxito: {room_challenge.get('success_criteria', 'Unknown')}
        
        Analiza:
        1. Qué tipo de error es (syntax, runtime, lógica, timeout)
        2. Genera un script de parcheo que corrija el error
        3. Determina si es posible corregir (máximo {self.max_retries} intentos)
        
        Output SOLO JSON con estas claves:
        {{
            "status": "error_retryable" | "error_fatal" | "success",
            "analysis": "descripción del error y solución",
            "patch_code": "código corrigiendo el error o vacío",
            "should_continue": true/false,
            "flag_detected": true/false
        }}
        """
        
        response = self.llm.generate(
            system_prompt=AUDITOR_SYSTEM_PROMPT,
            user_prompt=prompt
        )
        
        try:
            result = json.loads(response.strip())
            # Validar campos
            if "status" not in result:
                result["status"] = "error_fatal"
            return result
        except json.JSONDecodeError:
            # Fallback conservador
            return {
                "status": "error_fatal",
                "analysis": f"Error parseando evaluador LLM: {response[:200]}",
                "patch_code": None,
                "should_continue": False,
                "flag_detected": False
            }
    
    def _check_for_flag(self, output: str) -> bool:
        """Detecta si la salida contiene una bandera/formato de éxito."""
        flag_patterns = ["FLAG{", "flag{", "SUCCESS", "CONGRATULATIONS", "COMPLETE"]
        output_upper = output.upper()
        return any(pattern in output_upper for pattern in flag_patterns)
    
    def should_attempt_retry(self, evaluation: Dict[str, Any]) -> bool:
        """Determina si debemos reintentar basándonos en el evaluation y el contador."""
        if evaluation.get("status") == "success":
            return False
        if self.retry_count >= self.max_retries:
            self.retry_count = 0  # Reset para próxima sala
            return False
        if evaluation.get("should_continue", False):
            self.retry_count += 1
            return True
        return False