"""
Agente Ejecutor / Coder Agent.
Traduce la estrategia del Estratega en código Python o Bash ejecutable
dentro del Sandbox aislado de Vultr.
"""

import subprocess
import json
import sys
from typing import Dict, Any, Optional, Tuple
from config.prompts import CODER_SYSTEM_PROMPT


class Coder:
    """Traduce estrategias en código ejecutable."""
    
    def __init__(self, llm_client, sandbox_runner):
        self.llm = llm_client
        self.sandbox = sandbox_runner
    
    def generate_code(self, strategy: Dict[str, Any], room_challenge: Dict[str, Any]) -> Tuple[Optional[str], str]:
        """
        Genera código Python/Bash basado en la estrategia del Estratega.
        
        Returns:
            Tuple de (codigo_generado, error_message)
            - codigo_generado: script listo para ejecutar o None si error
            - error_message: mensaje de error o cadena vacía
        """
        approach = strategy.get("approach", "")
        suggested_cmd = strategy.get("suggested_command", "")
        
        prompt = f"""
        Eres el Agente Coder para el AI Escape Room.
        
        Enfoque del Estratega: {approach}
        Comando sugerido: {suggested_cmd}
        
        Desafío de la Sala: {room_challenge.get('description', 'Unknown')}
        Criterios de éxito: {room_challenge.get('success_criteria', 'Unknown')}
        
        Genera un script Python o Bash que:
        1. Procesa la entrada disponible y logra el criterio de éxito
        2. Escribe SOLO código ejecutable (no explicaciones largas)
        3. Usa stdin/stdout para entrada/salida estándar
        4. Maneja errores gracefully (try/except)
        5. No requiere APIs externas o credenciales dentro del sandbox
        6. Tiene un máximo de 50 líneas para mantener eficiencia
        
        Output estrictamente en formato de script. Ejemplo:
        
        ```python
        #!/usr/bin/env python3
        import re
        import sys
        
        def main():
            data = sys.stdin.read()
            # ... lógica de solución
            result = "FLAG{example}"
            print(result)
        
        if __name__ == "__main__":
            main()
        ```
        """
        
        system_prompt = CODER_SYSTEM_PROMPT
        user_prompt = prompt
        
        response = self.llm.generate(system_prompt=system_prompt, user_prompt=user_prompt)
        
        # Extraer solo el código del response (quitar bloques ``` if existan)
        code = response.strip()
        # Remover bloques de código markdown si vienen
        if code.startswith("```"):
            lines = code.split('\n')
            # Find first non-fence line and last non-fence line
            start_idx = 0
            end_idx = len(lines) - 1
            while start_idx < len(lines) and lines[start_idx].strip().startswith("```"):
                start_idx += 1
            while end_idx > start_idx and lines[end_idx].strip().startswith("```"):
                end_idx -= 1
            code = '\n'.join(lines[start_idx:end_idx+1]).strip()
        
        # Validar que el código tiene sintaxis básica de Python
        if not any(keyword in code.lower() for keyword in ['def ', 'import ', 'print ', '#!']):
            # Intentar usar el comando sugerido como fallback
            if suggested_cmd:
                return suggested_cmd, "Using suggested command as fallback"
            return None, "Generated code lacks Python syntax basics"
        
        return code, ""
    
    def execute_locally(self, code: str, timeout: int = 10) -> Dict[str, Any]:
        """
        Ejecuta el código localmente para preview antes de enviar al sandbox.
        Retorna stdout, stderr y exit code.
        """
        try:
            result = subprocess.run(
                [sys.executable, "-c", code],
                capture_output=True,
                text=True,
                timeout=timeout
            )
            return {
                "stdout": result.stdout,
                "stderr": result.stderr,
                "exit_code": result.returncode,
                "success": result.returncode == 0
            }
        except subprocess.TimeoutExpired:
            return {
                "stdout": "",
                "stderr": "TIMEOUT: Código excedió los límite de ejecución",
                "exit_code": -1,
                "success": False
            }
        except Exception as e:
            return {
                "stdout": "",
                "stderr": str(e),
                "exit_code": -1,
                "success": False
            }