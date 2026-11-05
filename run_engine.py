"""
AGENT RUSH — motor de partidas reales.

- Llama a Vultr Serverless Inference (OpenAI-compatible) con la key de la
  suscripción (`VULTR_INFERENCE_API_KEY`).
- Ejecuta el código del Coder en contenedores Docker efímeros y endurecidos.
- Valida la prueba de cada sala de forma determinista (server-side).
- Emite eventos para el SSE del frontend.

No hay logs ficticios: si una llamada o el sandbox fallan, se emite el error.
"""

from __future__ import annotations

import ast
import hashlib
import hmac
import json
import os
import queue
import random
import re
import secrets
import shutil
import sqlite3
import subprocess
import threading
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from config.budget import MAX_TOKENS_PER_RUN, MAX_TOKENS_PER_CALL
from llm.meter import TokenMeter, TokenBudgetExceeded

SERVER_SECRET = b"agent-rush-hackathon-2026-escape-room"
CHALLENGE_VERSION = "plan-c-v2"
MAX_ROOM_ATTEMPTS = 3

ROOMS = {
    1: {
        "title": "THE LOGS",
        "description": (
            "Two rotated auth logs and a manifest are on the terminal. The active "
            "session must be correlated with the header checksum to recover the token."
        ),
        "objective": (
            "Find the SHA256:<32 hex> candidate whose SHA-256(session + ':' + "
            "candidate) matches the manifest header checksum."
        ),
        "hint": "Parse both logs, dedupe candidates, and test the checksum formula.",
    },
    2: {
        "title": "MEMORY LEAK",
        "description": (
            "A chunked accumulator has a memory bug and its test suite is mounted. "
            "Repair the module without touching the tests."
        ),
        "objective": (
            "Write a corrected memory_leak.py, run the provided tests, and print "
            "the proof only after the tests pass."
        ),
        "hint": "Keep the tests unchanged; use /tmp for the module and test files.",
    },
    3: {
        "title": "FIREWALL",
        "description": (
            "A loopback firewall speaks HELLO → NONCE → HMAC. Complete the "
            "handshake and recover the access token."
        ),
        "objective": (
            "Implement the local server and client, sign the fresh nonce with "
            "HMAC-SHA256, and print the TOKEN returned after a valid handshake."
        ),
        "hint": "The nonce changes per connection; a bad signature returns a decoy.",
    },
}

DB_PATH = Path(os.getenv("AGENT_RUSH_DB", "data/agent_rush.db"))
SANDBOX_IMAGE = os.getenv("AGENT_RUSH_SANDBOX_IMAGE", "python:3.12-slim")
SANDBOX_FLAGS = [
    "--rm",
    "-i",
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
_PROBE_LOCK = threading.Lock()


class EngineError(RuntimeError):
    """Error controlado del motor (se muestra al usuario)."""


class InferenceError(EngineError):
    """Vultr rechazó o no respondió la llamada."""


class SandboxError(EngineError):
    """Docker no está disponible o el contenedor falló de forma inesperada."""


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def hmac_flag(room: int, seed: str) -> str:
    return hmac.new(
        SERVER_SECRET, f"room:{room}:seed:{seed}".encode(), hashlib.sha256
    ).hexdigest()[:32]


def _build_room1(flag: str) -> Dict[str, Any]:
    """Rotated auth logs + a manifest checksum. Easy-medium correlation."""
    rng = random.SystemRandom()
    active_session = secrets.token_hex(6)
    header_checksum = hashlib.sha256(
        f"{active_session}:{flag}".encode()
    ).hexdigest()

    decoys = [secrets.token_hex(16) for _ in range(9)]
    candidates = decoys + [flag]
    rng.shuffle(candidates)

    lines: List[str] = []
    for i, ticket in enumerate(candidates):
        # The valid ticket is always tied to the active session so a
        # session filter cannot accidentally discard it. Several decoys
        # also share that session, so finding it is not enough.
        if ticket == flag:
            session = active_session
        else:
            session = active_session if rng.random() < 0.45 else secrets.token_hex(6)
        user = rng.choice(["root", "deploy", "backup", "ops", "auditor"])
        ip = f"203.0.113.{rng.randint(10, 250)}"
        lines.append(
            "2026-11-04T%02d:%02d:%02d INFO sshd[%d]: "
            "session=%s user=%s from=%s event=publickey "
            "SHA256:%s"
            % (
                rng.randint(0, 23),
                rng.randint(0, 59),
                rng.randint(0, 59),
                1000 + i,
                session,
                user,
                ip,
                ticket,
            )
        )

    # Corrupt / malformed entries: truncated, uppercase, wrong length, not hex.
    corrupt = [
        flag[:19],
        flag.upper(),
        secrets.token_hex(24),
        "deadbeef" * 8,
        "not-a-sha256-value",
        "",
    ]
    for i, value in enumerate(corrupt):
        lines.append(
            "2026-11-04T23:%02d:%02d WARN audit[%d]: "
            "session=%s malformed=SHA256:%s"
            % (i * 7 % 60, i * 11 % 60, 2000 + i, secrets.token_hex(6), value)
        )

    # Ordinary noise, duplicate decoys and a short rotated-log header.
    for i in range(8):
        lines.append(
            "2026-11-04T22:%02d:%02d INFO systemd[1]: "
            "rotated auth segment %d accepted; sync=ok"
            % (i * 6, i * 9 % 60, i + 1)
        )
    lines.append(
        "2026-11-04T23:59:59 INFO sshd[9999]: session=%s user=root "
        "event=publickey SHA256:%s"
        % (active_session, rng.choice(decoys))
    )

    rng.shuffle(lines)
    split = max(1, len(lines) // 2)
    manifest = {
        "active_session": active_session,
        "header_checksum": header_checksum,
        "algorithm": "sha256(active_session + ':' + ticket)",
        "note": (
            "Only a 32-char lowercase hex ticket can match. Other SHA256 values "
            "are decoys, truncated, uppercase, or malformed."
        ),
    }
    files = {
        "manifest.json": json.dumps(manifest, indent=2),
        "auth.log": "\n".join(lines[:split]) + "\n",
        "auth.log.1": "\n".join(lines[split:]) + "\n",
    }
    return {
        "data": json.dumps({"files": files}, indent=2),
        "proof": flag,
        "prompt": (
            "stdin is JSON with a `files` object containing manifest.json, "
            "auth.log and auth.log.1. Each log line may contain session=<id> and "
            "SHA256:<ticket>. The manifest gives active_session and "
            "header_checksum, where header_checksum = "
            "SHA-256(active_session + ':' + ticket). Find the 32-char lowercase "
            "hex ticket whose checksum matches. Ignore malformed, truncated, "
            "uppercase or 64-hex values. Read stdin and print ONLY the ticket."
        ),
    }


def _build_room2(flag: str) -> Dict[str, Any]:
    """A real buggy module + tests. The agent repairs the module, not the tests."""
    buggy_module = '''"""
memory_leak.py — chunked accumulator.

Contract:
- chunk_sum(values, size) returns the sum of every integer in values.
- Values are processed in chunks of at most `size` items.
- size <= 0 returns 0.
- The input list must not be mutated.
"""


def chunk_sum(values, size):
    if size < 0:
        raise ValueError("size must be positive")
    total = 0
    for i in range(0, len(values) - size + 1, size):
        chunk = values[i:i + size]
        total += abs(sum(chunk))
    return total
'''
    tests = '''from memory_leak import chunk_sum

CASES = [
    ([], 3, 0),
    ([1, 2, 3, 4, 5], 2, 15),
    ([-1, -2, -3], 2, -6),
    ([10], 5, 10),
    ([0] * 1000, 7, 0),
    ([1] * 100000, 7, 100000),
    ([1, 2, 3], 0, 0),
    ([1, 2, 3], -3, 0),
]

for values, size, expected in CASES:
    snapshot = list(values)
    got = chunk_sum(values, size)
    assert got == expected, f"chunk_sum({values[:8]}..., {size})={got}, expected {expected}"
    assert values == snapshot, "input list was mutated"

print("TESTS_OK")
'''
    return {
        "mode": "module",
        "tests": tests,
        "data": json.dumps(
            {
                "module": buggy_module,
                "tests": tests,
                "proof": flag,
                "instructions": (
                    "Return ONLY the corrected memory_leak.py module. The harness "
                    "writes it to /tmp/memory_leak.py and runs the provided tests."
                ),
            },
            indent=2,
        ),
        "proof": flag,
        "prompt": (
            "stdin is JSON with `module` (a buggy memory_leak.py), `tests` (the "
            "authoritative test suite), `proof`, and `instructions`. Return ONLY the "
            "corrected Python module that defines `chunk_sum(values, size)`. Do not "
            "write files, do not run tests, do not print the proof, and do not return "
            "a runner: the harness writes your module to /tmp/memory_leak.py and runs "
            "the tests unchanged. Handle empty input, negative values, size <= 0, "
            "partial chunks and a 100k element list efficiently; never mutate the "
            "input. Return code only, starting with the function definition."
        ),
    }


def _build_room3(flag: str) -> Dict[str, Any]:
    """Loopback HELLO/NONCE/HMAC handshake with a decoy and limited attempts."""
    key = secrets.token_hex(16)
    decoy = secrets.token_hex(16)
    return {
        "data": json.dumps(
            {
                "protocol": {
                    "transport": "TCP loopback 127.0.0.1 (bind ephemeral port 0)",
                    "key_hex": key,
                    "max_invalid_attempts": 3,
                    "decoy_token": decoy,
                    "token": flag,
                    "steps": [
                        "client connects and sends: HELLO\\n",
                        "server sends: NONCE <32 lowercase hex>\\n (fresh per connection)",
                        "client sends: AUTH <hmac_sha256_hex(key, nonce)>\\n",
                        "server sends: TOKEN <32 lowercase hex>\\n on a valid signature",
                        "server sends: DECOY <32 lowercase hex>\\n on a bad signature",
                        "after 3 invalid AUTH attempts the server sends LOCKOUT and closes",
                    ],
                }
            },
            indent=2,
        ),
        "proof": flag,
        "prompt": (
            "stdin is JSON describing a loopback firewall protocol. Write one Python "
            "script that starts a TCP server on 127.0.0.1 with an ephemeral port and "
            "a client thread/connection in the same process. The server must send a "
            "fresh NONCE per connection, verify AUTH = HMAC-SHA256(key, nonce), return "
            "TOKEN <token> on success or DECOY <decoy> on failure, and lock out after "
            "3 invalid attempts. The client must send HELLO, read the nonce, compute "
            "the HMAC, send AUTH, read the response, and print ONLY the TOKEN value. "
            "Use socket timeouts so the script cannot hang; do not print the key, the "
            "decoy, or debug lines."
        ),
    }


def build_challenge(room: int) -> Dict[str, Any]:
    """Genera el artefacto y la prueba esperada de cada sala."""
    seed = secrets.token_hex(16)
    meta = ROOMS[room]
    challenge: Dict[str, Any] = {
        "room": room,
        "title": meta["title"],
        "description": meta["description"],
        "objective": meta["objective"],
        "hint": meta["hint"],
        "seed": seed,
        "flag": hmac_flag(room, seed),
        "challenge_version": CHALLENGE_VERSION,
    }
    generated = {1: _build_room1, 2: _build_room2, 3: _build_room3}[room](
        challenge["flag"]
    )
    challenge.update(generated)
    return challenge


class EventBus:
    """Historial + cola para SSE, thread-safe."""

    def __init__(self) -> None:
        self._queue: "queue.Queue[Optional[dict]]" = queue.Queue()
        self._history: List[dict] = []
        self._lock = threading.Lock()
        self.closed = False
        self.cancelled = threading.Event()
        self._seq = 0

    def emit(self, event: Dict[str, Any]) -> None:
        event = dict(event)
        event.setdefault("ts", time.time())
        with self._lock:
            if self.closed:
                return
            self._seq += 1
            event["seq"] = self._seq
            self._history.append(event)
        self._queue.put(event)

    def close(self) -> None:
        with self._lock:
            if self.closed:
                return
            self.closed = True
            history = list(self._history)
        self._queue.put(None)

    def history(self) -> List[dict]:
        with self._lock:
            return list(self._history)

    def next_event(self, timeout: float = 15.0) -> Optional[dict]:
        try:
            return self._queue.get(timeout=timeout)
        except queue.Empty:
            return None


class VultrChat:
    """Cliente estricto: si Vultr falla, se levanta excepción (sin mock)."""

    def __init__(self, api_key: str, base_url: str) -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")

    def generate(
        self,
        model: str,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int,
    ) -> tuple[str, Dict[str, Any]]:
        import urllib.error
        import urllib.request

        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.2,
            "max_tokens": max(64, int(max_tokens)),
            # Vultr thinking models otherwise spend the whole completion budget
            # on hidden reasoning before emitting code. Low effort keeps the
            # demo fast and inside the per-run token budget.
            "reasoning_effort": os.getenv("VULTR_REASONING_EFFORT", "low"),
        }
        req = urllib.request.Request(
            f"{self.base_url}/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=90) as resp:
                body = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")[:300]
            raise InferenceError(f"Vultr HTTP {exc.code}: {detail}") from exc
        except Exception as exc:  # red, timeout, JSON
            raise InferenceError(f"No se pudo llamar a Vultr: {exc}") from exc

        try:
            message = body["choices"][0]["message"]
            text = (message.get("content") or "").strip()
            if not text:
                text = (
                    message.get("reasoning")
                    or message.get("reasoning_content")
                    or ""
                ).strip()
        except (KeyError, IndexError) as exc:
            raise InferenceError("Respuesta de Vultr sin choices válidos") from exc

        usage = body.get("usage") or {}
        if not text:
            raise InferenceError("El modelo devolvió una respuesta vacía")
        return text, usage


def _has_code_lines(text: str) -> bool:
    for line in text.splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith("#"):
            return True
    return False


def _parse_python_segment(text: str) -> Optional[str]:
    """Busca el prefijo/sufijo/subsegmento más largo que sea Python válido.

    Los modelos a veces agregan prosa antes o después del código. En vez de
    confiar en el primer `import`, se prueba con `ast.parse` y se descarta la
    prosa. Es barato: los scripts tienen menos de 150 líneas.
    """
    raw = text.strip().replace("```python", "").replace("```py", "").replace("```", "")
    lines = raw.splitlines()
    if not lines:
        return None

    def valid(candidate: str) -> bool:
        if not candidate.strip() or not _has_code_lines(candidate):
            return False
        try:
            ast.parse(candidate)
        except SyntaxError:
            return False
        return True

    # 1) Leading prose: try every suffix.
    for start in range(len(lines)):
        candidate = "\n".join(lines[start:]).strip()
        if valid(candidate):
            return candidate

    # 2) Trailing prose: try every prefix.
    for end in range(len(lines), 0, -1):
        candidate = "\n".join(lines[:end]).strip()
        if valid(candidate):
            return candidate

    # 3) Both: start at a code marker and trim trailing prose.
    markers = ("import ", "from ", "def ", "class ", "#!/", "# ", "@")
    for start, line in enumerate(lines):
        if not any(line.lstrip().startswith(m) for m in markers):
            continue
        for end in range(len(lines), start, -1):
            candidate = "\n".join(lines[start:end]).strip()
            if valid(candidate):
                return candidate
    return None


def extract_code(text: str) -> str:
    """Extrae un script Python de una respuesta del LLM."""
    code = _parse_python_segment(text)
    if not code:
        raise EngineError("El Coder no devolvió código ejecutable")
    if len(code.splitlines()) > 150:
        raise EngineError("El código generado es demasiado largo (máx. 150 líneas)")
    return code


def extract_module_code(text: str) -> str:
    """Extrae el módulo corregido de una respuesta que puede traer prosa extra.

    Los LLM a veces devuelven la función, luego explican y recién después el
    runner. Para la sala de tipo `module` solo se necesita `chunk_sum`; se toma
    la FunctionDef de nivel superior y se descarta el resto.
    """
    raw = text.strip()
    fence = re.search(r"```(?:python|py)?\s*(.*?)```", raw, re.S | re.I)
    if fence:
        raw = fence.group(1).strip()

    lines = raw.splitlines()
    candidates: List[str] = []
    # Try the whole response first, then trimmed prefixes.
    for end in range(len(lines), 0, -1):
        candidate = "\n".join(lines[:end]).strip()
        if not candidate:
            continue
        try:
            tree = ast.parse(candidate)
        except SyntaxError:
            continue
        candidates.append(candidate)
        for node in tree.body:
            if isinstance(node, ast.FunctionDef) and node.name == "chunk_sum":
                segment = ast.get_source_segment(candidate, node)
                if segment and segment.strip():
                    return segment.strip()
        break

    # Fallback: start at the first `def chunk_sum` line and trim trailing prose.
    start = next(
        (i for i, line in enumerate(lines) if line.lstrip().startswith("def chunk_sum")),
        None,
    )
    if start is not None:
        for end in range(len(lines), start, -1):
            candidate = "\n".join(lines[start:end]).strip()
            try:
                tree = ast.parse(candidate)
            except SyntaxError:
                continue
            for node in tree.body:
                if isinstance(node, ast.FunctionDef) and node.name == "chunk_sum":
                    segment = ast.get_source_segment(candidate, node)
                    if segment and segment.strip():
                        return segment.strip()
            break

    if candidates:
        return candidates[0]
    raise EngineError("El Coder no devolvió un módulo ejecutable")


def module_runner(module_code: str, tests_code: str, proof: str) -> str:
    """Runner determinista que ejecuta los tests contra el módulo del agente."""
    return (
        "import subprocess, sys\n"
        f"module_code = {json.dumps(module_code)}\n"
        f"tests_code = {json.dumps(tests_code)}\n"
        "open('/tmp/memory_leak.py', 'w', encoding='utf-8').write(module_code)\n"
        "open('/tmp/test_memory_leak.py', 'w', encoding='utf-8').write(tests_code)\n"
        "proc = subprocess.run(\n"
        "    [sys.executable, '/tmp/test_memory_leak.py'],\n"
        "    cwd='/tmp', capture_output=True, text=True,\n"
        ")\n"
        "sys.stdout.write(proc.stdout)\n"
        "sys.stderr.write(proc.stderr)\n"
        "if 'TESTS_OK' in proc.stdout:\n"
        f"    print('PROOF:{proof}')\n"
    )


_DOCKER_OK: Optional[bool] = None
_DOCKER_LOCK = threading.Lock()


def docker_available() -> bool:
    global _DOCKER_OK
    with _DOCKER_LOCK:
        if _DOCKER_OK is not None:
            return _DOCKER_OK
        docker = shutil.which("docker")
        if not docker:
            _DOCKER_OK = False
            return False
        try:
            result = subprocess.run(
                [docker, "info"], capture_output=True, timeout=20
            )
            _DOCKER_OK = result.returncode == 0
        except Exception:
            _DOCKER_OK = False
        return bool(_DOCKER_OK)


def ensure_image(bus: EventBus) -> None:
    docker = shutil.which("docker")
    if not docker:
        raise SandboxError("Docker no está instalado o no está en PATH.")
    try:
        check = subprocess.run(
            [docker, "image", "inspect", SANDBOX_IMAGE],
            capture_output=True,
            timeout=20,
        )
        if check.returncode != 0:
            bus.emit({"type": "sandbox", "msg": f"pulling image {SANDBOX_IMAGE}…"})
            pull = subprocess.run(
                [docker, "pull", SANDBOX_IMAGE],
                capture_output=True,
                timeout=300,
            )
            if pull.returncode != 0:
                raise SandboxError(
                    "No se pudo descargar la imagen del sandbox: "
                    + pull.stderr.decode("utf-8", errors="replace")[-300:]
                )
    except subprocess.TimeoutExpired as exc:
        raise SandboxError("Timeout preparando la imagen del sandbox") from exc


def run_sandbox(code: str, stdin_data: str, bus: EventBus, timeout: int = 15) -> Dict[str, Any]:
    """Ejecuta código en un contenedor efímero y endurecido."""
    if not docker_available():
        raise SandboxError(
            "Docker no está corriendo. Iniciá Docker Desktop o el daemon en la VM."
        )
    ensure_image(bus)

    docker = shutil.which("docker")
    cmd = [docker, "run"] + SANDBOX_FLAGS + [SANDBOX_IMAGE, "python", "-c", code]

    bus.emit({"type": "sandbox", "msg": "spin_up · fresh container · net=none · read-only · 256m"})
    started = time.time()
    try:
        proc = subprocess.run(
            cmd,
            input=stdin_data.encode("utf-8"),
            capture_output=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        bus.emit({"type": "sandbox", "msg": f"timeout ({timeout}s) · container destroyed", "cls": "is-error"})
        return {"stdout": "", "stderr": f"timeout after {timeout}s", "exit_code": 124, "duration": time.time() - started}
    except Exception as exc:
        raise SandboxError(f"No se pudo ejecutar el sandbox: {exc}") from exc

    stdout = proc.stdout.decode("utf-8", errors="replace")[:8000]
    stderr = proc.stderr.decode("utf-8", errors="replace")[:8000]
    return {
        "stdout": stdout,
        "stderr": stderr,
        "exit_code": proc.returncode,
        "duration": round(time.time() - started, 2),
    }


def sandbox_probe() -> List[Dict[str, Any]]:
    """Corre intentos maliciosos en el sandbox y reporta si fueron contenidos."""
    if not docker_available():
        raise SandboxError("Docker no está corriendo.")

    probes = [
        {
            "name": "Root filesystem write",
            "command": ["python", "-c", "open('/pwned','w').write('x'); print('WRITE_ALLOWED')"],
            "marker": "WRITE_ALLOWED",
        },
        {
            "name": "Host secrets exposure",
            "command": ["python", "-c", "import os; print('HAS_KEY', 'VULTR_INFERENCE_API_KEY' in os.environ)"],
            "marker": "HAS_KEY True",
        },
        {
            "name": "Outbound network",
            "command": [
                "python", "-c",
                "import socket; socket.create_connection(('1.1.1.1', 80), 2); print('NETWORK_OPEN')",
            ],
            "marker": "NETWORK_OPEN",
        },
    ]

    docker = shutil.which("docker")
    results = []
    with _PROBE_LOCK:
        for probe in probes:
            try:
                proc = subprocess.run(
                    [docker, "run"] + SANDBOX_FLAGS + [SANDBOX_IMAGE] + probe["command"],
                    capture_output=True,
                    timeout=25,
                )
                out = proc.stdout.decode("utf-8", errors="replace")
                err = proc.stderr.decode("utf-8", errors="replace")
                results.append(
                    {
                        "name": probe["name"],
                        "blocked": probe["marker"] not in out,
                        "exit_code": proc.returncode,
                        "output": (out + err)[:800],
                    }
                )
            except subprocess.TimeoutExpired:
                results.append(
                    {
                        "name": probe["name"],
                        "blocked": True,
                        "exit_code": 124,
                        "output": "timeout (contained)",
                    }
                )
    return results


class RunManager:
    """Crea runs, guarda eventos y expone el leaderboard."""

    def __init__(self) -> None:
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        self._db_lock = threading.Lock()
        self._init_db()
        self._runs: Dict[str, Dict[str, Any]] = {}
        self._active_id: Optional[str] = None
        self._lock = threading.Lock()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(DB_PATH), timeout=10)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._db_lock, self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS runs (
                    id TEXT PRIMARY KEY,
                    mode TEXT NOT NULL,
                    models TEXT NOT NULL,
                    status TEXT NOT NULL,
                    rooms_solved INTEGER NOT NULL DEFAULT 0,
                    tokens INTEGER NOT NULL DEFAULT 0,
                    duration REAL,
                    created TEXT NOT NULL,
                    finished TEXT,
                    challenge_version TEXT
                )
                """
            )
            columns = {
                row["name"]
                for row in conn.execute("PRAGMA table_info(runs)").fetchall()
            }
            if "challenge_version" not in columns:
                conn.execute("ALTER TABLE runs ADD COLUMN challenge_version TEXT")

    def api_key(self) -> str:
        return os.getenv("VULTR_INFERENCE_API_KEY", "").strip()

    def base_url(self) -> str:
        return os.getenv("VULTR_INFERENCE_BASE_URL", "https://api.vultrinference.com/v1")

    def is_busy(self) -> bool:
        with self._lock:
            return bool(self._active_id and self._runs.get(self._active_id, {}).get("busy"))

    def get_run(self, run_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            return self._runs.get(run_id)

    def start(self, mode: str, models: Dict[str, str]) -> Dict[str, Any]:
        if not self.api_key():
            raise EngineError(
                "Falta VULTR_INFERENCE_API_KEY (key de la suscripción de Inference)."
            )
        with self._lock:
            if self._active_id:
                active = self._runs.get(self._active_id)
                if active and active.get("busy"):
                    raise EngineError("Ya hay una partida en curso. Esperá a que termine.")
            run_id = uuid.uuid4().hex[:12]
            bus = EventBus()
            self._runs[run_id] = {
                "id": run_id,
                "mode": mode,
                "models": models,
                "bus": bus,
                "busy": True,
                "started": time.time(),
            }
            self._active_id = run_id

        with self._db_lock, self._connect() as conn:
            conn.execute(
                "INSERT INTO runs "
                "(id, mode, models, status, created, challenge_version) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (
                    run_id,
                    mode,
                    json.dumps(models),
                    "running",
                    utc_now(),
                    CHALLENGE_VERSION,
                ),
            )

        thread = threading.Thread(
            target=self._worker,
            args=(run_id, mode, models, bus),
            daemon=True,
            name=f"run-{run_id}",
        )
        thread.start()
        return self._runs[run_id]

    def _worker(self, run_id: str, mode: str, models: Dict[str, str], bus: EventBus) -> None:
        started = time.time()
        meter = TokenMeter(MAX_TOKENS_PER_RUN, MAX_TOKENS_PER_CALL)
        chat = VultrChat(self.api_key(), self.base_url())
        rooms_solved = 0
        total_tokens = 0
        status = "failed"

        def emit_energy() -> None:
            bus.emit(
                {
                    "type": "energy",
                    "tokens": meter.used,
                    "by_agent": meter.snapshot(),
                    "budget": meter.budget,
                }
            )

        def ask(agent: str, model: str, system: str, user: str, max_tokens: int) -> str:
            nonlocal total_tokens
            if bus.cancelled.is_set():
                raise EngineError("Partida abortada por el usuario")
            remaining = meter.remaining()
            if remaining <= 0:
                raise TokenBudgetExceeded(
                    used=meter.used, budget=meter.budget, agent=agent, mode=meter.mode
                )
            allowed = max(64, min(max_tokens, remaining))
            text, usage = chat.generate(model, system, user, allowed)
            try:
                meter.add(agent, usage)
            except TokenBudgetExceeded:
                emit_energy()
                raise
            total_tokens = meter.used
            emit_energy()
            return text

        def request_patch(
            room: int,
            challenge: Dict[str, Any],
            current_code: str,
            result: Dict[str, Any],
            patch_index: int,
        ) -> str:
            bus.emit(
                {
                    "type": "agent",
                    "agent": "auditor",
                    "msg": (
                        "auditor → proof missing; requesting patch "
                        f"({patch_index}/{MAX_ROOM_ATTEMPTS - 1})"
                    ),
                }
            )
            if challenge.get("mode") == "module":
                patch_prompt = (
                    "You are the Auditor. The tests failed. Return ONLY the corrected "
                    "Python module that defines `chunk_sum(values, size)`. No runner, "
                    "no file writes, no prose, no markdown fences.\n\n"
                    f"Challenge: {challenge['prompt']}\n"
                    f"Current module:\n{current_code}\n\n"
                    f"Test stdout:\n{(result.get('stdout') or '')[-1600:]}\n"
                    f"Test stderr:\n{(result.get('stderr') or '')[-1600:]}\n"
                    f"Input data:\n{challenge['data']}\n"
                )
                auditor_system = (
                    "You are the Auditor. Output only the corrected Python module "
                    "with chunk_sum. No prose, no markdown, no runner."
                )
                extractor = extract_module_code
            else:
                patch_prompt = (
                    "You are the Auditor. The sandbox output did not contain the "
                    "expected proof. Return ONLY the full corrected Python 3 runner, "
                    "no markdown fences, no analysis, no prose. The runner must be "
                    "complete and self-contained; never return just a helper function.\n\n"
                    f"Challenge: {challenge['prompt']}\n"
                    f"Current code:\n{current_code}\n\n"
                    f"Exit code: {result.get('exit_code')}\n"
                    f"stdout:\n{(result.get('stdout') or '')[-1200:]}\n"
                    f"stderr:\n{(result.get('stderr') or '')[-1200:]}\n"
                    f"Input data:\n{challenge['data']}\n"
                )
                auditor_system = (
                    "You are the Auditor. Output only the complete executable Python "
                    "runner. No prose, no markdown, no analysis."
                )
                extractor = extract_code
            raw_patch = ask(
                "auditor",
                models["auditor"],
                auditor_system,
                patch_prompt,
                4000,
            )
            try:
                new_code = extractor(raw_patch)
            except EngineError:
                bus.emit(
                    {
                        "type": "agent",
                        "agent": "auditor",
                        "msg": "auditor → patch did not contain executable code",
                    }
                )
                new_code = ""
            bus.emit(
                {
                    "type": "agent",
                    "agent": "auditor",
                    "msg": f"auditor → patch applied ({len(new_code.splitlines())} lines)",
                    "code": new_code,
                    "filename": f"room{room}.py",
                    "lines": len(new_code.splitlines()),
                }
            )
            return new_code

        bus.emit(
            {
                "type": "run_started",
                "run_id": run_id,
                "mode": mode,
                "models": models,
                "challenge_version": CHALLENGE_VERSION,
                "message": "run started",
            }
        )

        try:
            if not docker_available():
                raise SandboxError(
                    "Docker no está corriendo. Iniciá Docker Desktop o el daemon en la VM."
                )

            for room in (1, 2, 3):
                if bus.cancelled.is_set():
                    raise EngineError("Partida abortada por el usuario")

                challenge = build_challenge(room)
                room_started = time.time()
                bus.emit(
                    {
                        "type": "challenge",
                        "room": room,
                        "index": room - 1,
                        "title": challenge["title"],
                        "description": challenge["description"],
                        "objective": challenge["objective"],
                    }
                )
                bus.emit(
                    {
                        "type": "agent",
                        "agent": "system",
                        "msg": f"INITIATING LEVEL {room} ({challenge['title']})",
                    }
                )

                strategy = ask(
                    "strategist",
                    models["strategist"],
                    "You are the Strategist of an AI escape room. Give a concise, concrete plan. No code.",
                    (
                        f"Room {room}: {challenge['description']}\n"
                        f"Objective: {challenge['objective']}\n"
                        f"Data available on stdin:\n{challenge['data']}\n"
                        "Reply with a short strategy (max 4 sentences)."
                    ),
                    600,
                )
                bus.emit(
                    {
                        "type": "agent",
                        "agent": "strategist",
                        "msg": "strategist → " + " ".join(strategy.split())[:240],
                    }
                )

                if challenge.get("mode") == "module":
                    code_prompt = (
                        "You are the Coder of an AI escape room. Return ONLY the "
                        "corrected Python module that defines `chunk_sum(values, size)`. "
                        "No explanations, no markdown fences, no test runner, no file "
                        "writes. The harness writes your module to /tmp/memory_leak.py "
                        "and runs the authoritative tests unchanged. Return code only, "
                        "starting with the function definition.\n\n"
                        f"Challenge: {challenge['prompt']}\n"
                        f"Strategist plan: {strategy}\n"
                        f"Input data (also provided on stdin):\n{challenge['data']}\n"
                    )
                    coder_system = (
                        "You are a precise Python coder. Output only the corrected "
                        "module code."
                    )
                else:
                    code_prompt = (
                        "You are the Coder of an AI escape room. Return ONLY one "
                        "complete, self-contained Python 3 runner. No explanations, no "
                        "markdown fences, no partial helper functions. The runner is "
                        "what the sandbox executes: it reads stdin and prints the "
                        "requested proof to stdout.\n\n"
                        f"Challenge: {challenge['prompt']}\n"
                        f"Strategist plan: {strategy}\n"
                        f"Input data (also provided on stdin):\n{challenge['data']}\n"
                    )
                    coder_system = (
                        "You are a precise Python coder. Output only complete "
                        "executable Python runner code."
                    )
                raw_code = ask(
                    "coder",
                    models["coder"],
                    coder_system,
                    code_prompt,
                    4000,
                )
                try:
                    if challenge.get("mode") == "module":
                        code = extract_module_code(raw_code)
                    else:
                        code = extract_code(raw_code)
                except EngineError:
                    code = ""
                    bus.emit(
                        {
                            "type": "agent",
                            "agent": "coder",
                            "msg": "coder → response did not contain executable code",
                            "raw": raw_code[-2000:],
                        }
                    )
                bus.emit(
                    {
                        "type": "agent",
                        "agent": "coder",
                        "msg": f"coder → generated script ({len(code.splitlines())} lines)",
                        "code": code,
                        "filename": f"room{room}.py",
                        "lines": len(code.splitlines()),
                    }
                )

                solved = False
                last_output: Dict[str, Any] = {}
                for attempt in range(1, MAX_ROOM_ATTEMPTS + 1):
                    if bus.cancelled.is_set():
                        raise EngineError("Partida abortada por el usuario")

                    # Plan C: reject unparseable generations before spending a
                    # sandbox attempt. The Auditor gets a chance to repair it.
                    compile_error: Optional[str] = None
                    try:
                        compile(code, f"room{room}.py", "exec")
                    except (SyntaxError, ValueError) as exc:
                        compile_error = f"{type(exc).__name__}: {exc}"
                        result = {
                            "stdout": "",
                            "stderr": compile_error,
                            "exit_code": 1,
                            "duration": 0.0,
                        }
                    else:
                        sandbox_code = (
                            module_runner(
                                code, challenge["tests"], challenge["proof"]
                            )
                            if challenge.get("mode") == "module"
                            else code
                        )
                        result = run_sandbox(sandbox_code, challenge["data"], bus)
                    last_output = result
                    output_blob = (
                        (result.get("stdout") or "")
                        + "\n"
                        + (result.get("stderr") or "")
                    )
                    bus.emit(
                        {
                            "type": "sandbox",
                            "msg": (
                                f"compile error · attempt {attempt}/{MAX_ROOM_ATTEMPTS}"
                                if compile_error
                                else (
                                    f"exit={result['exit_code']} · "
                                    f"{result.get('duration')}s · "
                                    f"attempt {attempt}/{MAX_ROOM_ATTEMPTS}"
                                )
                            ),
                            "stdout": (result.get("stdout") or "")[-2000:],
                            "stderr": (result.get("stderr") or "")[-2000:],
                            "exit_code": result.get("exit_code"),
                            "duration": result.get("duration"),
                            "attempt": attempt,
                            "max_attempts": MAX_ROOM_ATTEMPTS,
                            "room": room,
                            "cls": (
                                "is-ok"
                                if not compile_error and result.get("exit_code") == 0
                                else "is-error"
                            ),
                        }
                    )
                    if challenge["proof"] in output_blob:
                        solved = True
                        break

                    if attempt == MAX_ROOM_ATTEMPTS:
                        break
                    code = request_patch(
                        room, challenge, code, result, patch_index=attempt
                    )

                if not solved:
                    raise EngineError(
                        "No se encontró la prueba de la sala %d. stderr: %s"
                        % (room, (last_output.get("stderr") or "")[-300:])
                    )

                rooms_solved = room
                elapsed = time.time() - room_started
                bus.emit(
                    {
                        "type": "room_solved",
                        "room": room,
                        "index": room - 1,
                        "time": time.strftime("%M:%S", time.gmtime(elapsed)),
                        "flag": challenge["flag"][:8] + "…",
                    }
                )
                bus.emit(
                    {
                        "type": "agent",
                        "agent": "referee",
                        "msg": f"proof validated · room={room} · ROOM {room} SOLVED",
                    }
                )

            status = "success"
            bus.emit(
                {
                    "type": "run_completed",
                    "rooms_solved": rooms_solved,
                    "tokens": meter.used,
                    "duration": round(time.time() - started, 1),
                    "models": models,
                }
            )
        except TokenBudgetExceeded as exc:
            status = "disqualified"
            bus.emit(
                {
                    "type": "disqualified",
                    "message": f"Token budget exceeded ({exc.used}/{exc.budget})",
                    "tokens": meter.used,
                }
            )
        except EngineError as exc:
            status = "aborted" if bus.cancelled.is_set() else "failed"
            bus.emit(
                {
                    "type": "aborted" if bus.cancelled.is_set() else "run_failed",
                    "message": str(exc),
                    "rooms_solved": rooms_solved,
                }
            )
        except Exception as exc:  # noqa: BLE001
            status = "failed"
            bus.emit(
                {
                    "type": "run_failed",
                    "message": f"Error inesperado: {type(exc).__name__}: {exc}",
                    "rooms_solved": rooms_solved,
                }
            )
        finally:
            duration = round(time.time() - started, 1)
            try:
                with self._db_lock, self._connect() as conn:
                    conn.execute(
                        "UPDATE runs SET status=?, rooms_solved=?, tokens=?, duration=?, finished=? WHERE id=?",
                        (status, rooms_solved, meter.used, duration, utc_now(), run_id),
                    )
            except Exception:
                pass
            with self._lock:
                if run_id in self._runs:
                    self._runs[run_id]["busy"] = False
                if self._active_id == run_id:
                    self._active_id = None
            time.sleep(0.1)
            bus.close()

    def abort(self, run_id: str) -> bool:
        with self._lock:
            entry = self._runs.get(run_id)
        if not entry:
            return False
        entry["bus"].cancelled.set()
        entry["bus"].emit(
            {"type": "aborted", "message": "Run aborted by the user."}
        )
        return True

    def leaderboard(self) -> Dict[str, Any]:
        with self._db_lock, self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM runs WHERE status='success' AND challenge_version=? "
                "ORDER BY duration ASC, tokens ASC LIMIT 20",
                (CHALLENGE_VERSION,),
            ).fetchall()

        def to_row(row: sqlite3.Row) -> Dict[str, Any]:
            models = json.loads(row["models"] or "{}")
            squad = " + ".join(
                str(models.get(k, "?")) for k in ("strategist", "coder", "auditor")
            )
            duration = row["duration"] or 0
            return {
                "rank": 0,
                "squad": squad.upper(),
                "time": time.strftime("%M:%S", time.gmtime(duration)),
                "tokens": int(row["tokens"] or 0),
                "success": True,
                "mode": row["mode"],
            }

        rows = [to_row(r) for r in rows]
        spectator = [r for r in rows if r["mode"] == "spectator"]
        orchestrator = [r for r in rows if r["mode"] == "orchestrator"]
        for index, row in enumerate(spectator, 1):
            row["rank"] = index
        for index, row in enumerate(orchestrator, 1):
            row["rank"] = index
        return {
            "challenge_version": CHALLENGE_VERSION,
            "spectator": {
                "mode": "spectator",
                "rows": spectator,
                "has_runs": bool(spectator),
            },
            "orchestrator": {
                "mode": "orchestrator",
                "rows": orchestrator,
                "has_runs": bool(orchestrator),
            },
        }


MANAGER = RunManager()
