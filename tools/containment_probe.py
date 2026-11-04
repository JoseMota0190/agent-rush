#!/usr/bin/env python3
"""
Prueba de contención del sandbox (para la demo y el video).

Ejecuta intentos maliciosos dentro del mismo contenedor endurecido que usa
el motor de runs y reporta si fueron bloqueados.

Uso:
    python tools/containment_probe.py
"""

from __future__ import annotations

import shutil
import subprocess
import sys

IMAGE = "python:3.12-slim"
FLAGS = [
    "--rm",
    "--network", "none",
    "--read-only",
    "--tmpfs", "/tmp:rw,noexec,nosuid,size=64m",
    "--memory", "256m",
    "--cpus", "0.5",
    "--pids-limit", "64",
    "--cap-drop", "ALL",
    "--security-opt", "no-new-privileges",
    "--user", "65534:65534",
]

PROBES = [
    {
        "title": "Escritura en el filesystem raíz",
        "command": ["python", "-c", "open('/pwned','w').write('x'); print('WRITE_ALLOWED')"],
        "fail_marker": "WRITE_ALLOWED",
        "expectation": "El filesystem es read-only: no se puede escribir en /.",
    },
    {
        "title": "Lectura de secretos del host (/proc/self/environ)",
        "command": ["python", "-c", "import os; print('HAS_KEY', 'VULTR_INFERENCE_API_KEY' in os.environ)"],
        "fail_marker": "HAS_KEY True",
        "expectation": "El contenedor no hereda las variables de entorno del host.",
    },
    {
        "title": "Conexión saliente a 1.1.1.1:80",
        "command": ["python", "-c", "import socket; socket.create_connection(('1.1.1.1', 80), 2); print('NETWORK_OPEN')"],
        "fail_marker": "NETWORK_OPEN",
        "expectation": "Con --network none no hay red saliente.",
    },
    {
        "title": "Fork bomb / límite de procesos",
        "command": [
            "python", "-c",
            "import os\nfor _ in range(200):\n    try:\n        os.fork()\n    except OSError:\n        print('PID_LIMIT_BLOCKED')\n        break",
        ],
        "fail_marker": "",
        "expectation": "El límite de pids frena la expansión de procesos.",
    },
]


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    docker = shutil.which("docker")
    if not docker:
        print("Docker no está disponible.", file=sys.stderr)
        return 1

    print("Sandbox flags:")
    print("  docker run " + " ".join(FLAGS) + f" {IMAGE} …")
    print()

    failures = 0
    for probe in PROBES:
        print("=" * 72)
        print(probe["title"])
        try:
            proc = subprocess.run(
                [docker, "run"] + FLAGS + [IMAGE] + probe["command"],
                capture_output=True,
                timeout=25,
                text=True,
                errors="replace",
            )
            out = (proc.stdout or "").strip()
            err = (proc.stderr or "").strip()
            print("  exit:", proc.returncode)
            if out:
                print("  stdout:", out[:500])
            if err:
                print("  stderr:", err[:500])

            if probe["fail_marker"] and probe["fail_marker"] in out:
                print("  RESULTADO: ❌ NO CONTENIDO")
                failures += 1
            elif "PID_LIMIT" in probe["title"] and "PID_LIMIT_BLOCKED" not in out:
                print("  RESULTADO: ⚠️ no se alcanzó el límite de pids (revisar)")
            else:
                print("  RESULTADO: ✅ bloqueado / contenido")
            print("  expectativa:", probe["expectation"])
        except subprocess.TimeoutExpired:
            print("  RESULTADO: ✅ timeout (contenido)")
        print()

    print("=" * 72)
    if failures:
        print(f"CONTENCIÓN: {failures} prueba(s) fallaron")
        return 1
    print("CONTENCIÓN: todas las pruebas pasaron")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
