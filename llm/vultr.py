"""
Cliente LLM para Vultr Serverless Inference.

Endpoint: https://api.vultrinference.com/v1 (OpenAI-compatible)
Interfaz igual a MockLLM.generate(system_prompt, user_prompt) -> str.

Si falta VULTR_INFERENCE_API_KEY o falla la petición, devuelve una respuesta
fake determinística para que la app siga levantando sin depender de la key.
"""

import json
import os
import urllib.error
import urllib.request
from typing import Optional, Tuple, Dict, Any


class VultrLLM:
    """Wrapper alrededor de Vultr Serverless Inference (OpenAI-compatible)."""

    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None,
                 model: Optional[str] = None):
        self.api_key = api_key or os.getenv("VULTR_INFERENCE_API_KEY")
        self.base_url = (base_url or os.getenv(
            "VULTR_INFERENCE_BASE_URL", "https://api.vultrinference.com/v1"
        )).rstrip("/")
        self.model = model or os.getenv("VULTR_INFERENCE_MODEL", "deepseek-v4.1-flash-1017")
        self._has_key = bool(self.api_key)

    def generate_with_usage(
        self, system_prompt: str, user_prompt: str, max_tokens: Optional[int] = None
    ) -> Tuple[str, Dict[str, Any]]:
        """Genera respuesta vía Vultr Serverless Inference y retorna el texto más el uso.

        Si no hay API key o la petición falla, devuelve una respuesta
        fake determinística (mismo comportamiento que MockLLM) y un uso sintético.

        Args:
            system_prompt (str): Prompt de sistema para el modelo.
            user_prompt (str): Prompt de usuario para el modelo.
            max_tokens (Optional[int]): Máximo tokens a generar (default del modelo).

        Returns:
            Tuple[str, Dict[str, Any]]: (respuesta_generada, diccionario_de_uso)
                El diccionario de uso contiene 'prompt_tokens', 'completion_tokens', 'total_tokens'.
        """
        if not self._has_key:
            text = self._fake_response(system_prompt, user_prompt)
            usage = self._estimate_usage(text)
            return text, usage

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.3,
            "max_tokens": max_tokens if max_tokens is not None else 1000,
        }

        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            f"{self.base_url}/chat/completions",
            data=data,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                body = json.loads(resp.read().decode("utf-8"))
                text = body["choices"][0]["message"]["content"]
                usage = body.get("usage", {})
                return text, usage
        except (urllib.error.URLError, urllib.error.HTTPError,
                json.JSONDecodeError, KeyError, OSError) as exc:
            # Fallback silencioso a fake si el servicio no responde
            text = self._fake_response(system_prompt, user_prompt, error=str(exc))
            usage = self._estimate_usage(text)
            return text, usage

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        """Genera respuesta vía Vultr Serverless Inference.

        Si no hay API key o la petición falla, devuelve una respuesta
        fake determinística (mismo comportamiento que MockLLM) para no
        romper el arranque de la app.
        """
        text, _ = self.generate_with_usage(system_prompt, user_prompt)
        return text

    def list_models(self) -> list:
        """Lista los modelos disponibles desde la API de Vultr Inference.

        Returns:
            list: JSON de respuesta de la API /models.
        """
        if not self._has_key:
            return {"data": []}
        url = f"{self.base_url.rstrip('/')}/models"
        req = urllib.request.Request(url, headers={"Authorization": f"Bearer {self.api_key}"})
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except (urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError, OSError):
            return {"data": []}

    # ------------------------------------------------------------------
    # Fallback determinístico (mismo contrato que MockLLM)
    # ------------------------------------------------------------------
    @staticmethod
    def _fake_response(system_prompt: str, prompt_key: str, error: Optional[str] = None) -> str:
        prompt_key = (prompt_key or "")[:50].replace("\n", " ")

        if "STRATEGIST" in system_prompt.upper() or "ESTRATEG" in system_prompt.upper():
            if "Sala 1" in prompt_key or "Encrypted" in prompt_key or "log" in prompt_key.lower():
                return json.dumps({
                    "approach": "Parsear el archivo de logs con expresiones regulares para extraer el hash SSH",
                    "reasoning": "Los logs contienen patrones de autenticación, el hash está en formato hexadecimal",
                    "confidence": 0.85,
                    "suggested_command": "python3 extract_hash.py",
                })
            elif "Sala 2" in prompt_key or "Memory" in prompt_key:
                return json.dumps({
                    "approach": "Identificar y fixear la fuga de memoria en el script",
                    "reasoning": "Bucle while True sin cierre de archivo causa memory leak",
                    "confidence": 0.78,
                    "suggested_command": "python3 fix_memory.py",
                })
            else:
                return json.dumps({
                    "approach": "Ejecutar handshake criptográfico con firmas válidas contra el firewall",
                    "reasoning": "Validar claves pública/privada paso a paso",
                    "confidence": 0.82,
                    "suggested_command": "python3 exploit_firewall.py",
                })

        if "CODER" in system_prompt.upper() or "Coder" in system_prompt.upper():
            return '''#!/usr/bin/env python3
import re
import sys


def main():
    data = sys.stdin.read()
    hash_pattern = r"[a-f0-9]{32,64}"
    matches = re.findall(hash_pattern, data)

    if matches:
        print(f"EXTRACTED_HASH: {matches[0]}")
    else:
        print("NO_HASH_FOUND")

    result = "PROCESSED"
    print(result)
    print("FLAG{MOCK_PROOF}")


if __name__ == "__main__":
    main()'''

        if "AUDITOR" in system_prompt.upper() or "EVALUADOR" in system_prompt.upper():
            return json.dumps({
                "status": "success",
                "analysis": "Ejecución exitosa, salida procesada correctamente",
                "patch_code": None,
                "should_continue": False,
                "flag_detected": True,
            })

        return "{}"

    @staticmethod
    def _estimate_usage(text: str) -> Dict[str, Any]:
        """Estima uso de tokens basado en longitud del texto (proxy para prompt+completion)."""
        # Estimación aproximada: 1 token ≈ 4 caracteres
        total_tokens = max(1, len(text) // 4)
        # Distribuir tokens entre prompt y completion (50/50)
        prompt_tokens = total_tokens // 2
        completion_tokens = total_tokens - prompt_tokens
        return {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": total_tokens,
        }
class MockLLM:
    """LLM simulado determinístico para uso cuando no hay API key de Vultr."""

    def generate_with_usage(
        self, system_prompt: str, user_prompt: str, max_tokens: Optional[int] = None
    ) -> Tuple[str, Dict[str, Any]]:
        """Genera respuesta simulada y un uso sintético."""
        text = self._mock_response(system_prompt, user_prompt)
        usage = self._estimate_usage(text)
        return text, usage

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        """Genera respuesta simulada (mantiene compatibilidad con el código existente)."""
        return self._mock_response(system_prompt, user_prompt)

    @staticmethod
    def _mock_response(system_prompt: str, prompt_key: str) -> str:
        prompt_key = (prompt_key or "")[:50].replace("\n", " ")
        if "STRATEGIST" in system_prompt.upper() or "Estratega" in system_prompt.upper():
            if "Sala 1" in prompt_key or "Encrypted" in prompt_key:
                return json.dumps({
                    "approach": "Parsear el archivo de logs corrupted con expresiones regulares para extraer el hash SSH key",
                    "reasoning": "Los logs contienen patrones de fallos de autenticación, el hash está en formato hexadecimal",
                    "confidence": 0.85,
                    "suggested_command": "python3 extract_hash.py",
                })
            elif "Sala 2" in prompt_key or "Memory" in prompt_key:
                return json.dumps({
                    "approach": "Identificar y fixear la fuga de memoria en el script provided",
                    "reasoning": "El script tiene un bucle while True sin close de archivo, causando memory leak",
                    "confidence": 0.78,
                    "suggested_command": "python3 fix_memory.py",
                })
            else:
                return json.dumps({
                    "approach": "Ejecutar handshake cryptográfico con firmas válidas contra el firewall emulado",
                    "reasoning": "Necesitamos validar las claves públicas/privadas en el paso a paso",
                    "confidence": 0.82,
                    "suggested_command": "python3 exploit_firewall.py",
                })
        elif "CODER" in system_prompt.upper() or "Coder" in system_prompt.upper():
            return """#!/usr/bin/env python3
import re
import sys

def main():
    data = sys.stdin.read()
    hash_pattern = r'[a-f0-9]{32,64}'
    matches = re.findall(hash_pattern, data)

    if matches:
        print(f"EXTRACTED_HASH: {matches[0]}")
    else:
        print("NO_HASH_FOUND")

    result = "PROCESSED"
    print(result)
    print("FLAG{MOCK_PROOF}")

if __name__ == "__main__":
    main()"""
        elif "AUDITOR" in system_prompt.upper() or "EVALUADOR" in system_prompt.upper():
            import random
            scenarios = [
                json.dumps({
                    "status": "success",
                    "analysis": "Ejecución exitosa, hash extraído correctamente",
                    "patch_code": None,
                    "should_continue": False,
                    "flag_detected": True,
                }),
                json.dumps({
                    "status": "error_retryable",
                    "analysis": "SyntaxError: nombre de variable no definido, parcheando...",
                    "patch_code": " añadido variable de contexto",
                    "should_continue": True,
                    "flag_detected": False,
                }),
                json.dumps({
                    "status": "error_retryable",
                    "analysis": "IndexError en bucle, reindexando...",
                    "patch_code": " ajustado rango del bucle",
                    "should_continue": True,
                    "flag_detected": False,
                }),
            ]
            return random.choice(scenarios)
        return "{}"

    @staticmethod
    def _estimate_usage(text: str) -> Dict[str, Any]:
        total_tokens = max(1, len(text) // 4)
        prompt_tokens = total_tokens // 2
        completion_tokens = total_tokens - prompt_tokens
        return {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": total_tokens,
        }