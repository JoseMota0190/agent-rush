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

ROOMS = {
    1: {
        "title": "THE LOGS",
        "description": "The access terminal is locked. Parse the corrupted auth.log and recover the access token.",
        "objective": "Find the valid SHA256 token hidden among the decoys.",
        "hint": "Use a regular expression for SHA256:<32 hex chars>.",
    },
    2: {
        "title": "MEMORY LEAK",
        "description": "The accumulator lost values in memory. Recompute the checksum from the surviving data.",
        "objective": "Print the SHA-256 hex digest of the decimal sum of the numbers.",
        "hint": "Read JSON from stdin, sum the list, hash the decimal string.",
    },
    3: {
        "title": "FIREWALL",
        "description": "The firewall only accepts requests signed with HMAC-SHA256. Forge the correct signature.",
        "objective": "Print the lowercase HMAC-SHA256 hex digest of the message using the given key.",
        "hint": "Use hmac.new(key, message, hashlib.sha256).hexdigest().",
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
    }

    if room == 1:
        valid = challenge["flag"]
        decoys = [secrets.token_hex(16) for _ in range(6)]
        entries = decoys + [valid]
        random.SystemRandom().shuffle(entries)
        lines = []
        for i, entry in enumerate(entries):
            lines.append(
                "2026-11-04T12:%02d:%02d ERROR sshd[%d]: "
                "Failed publickey for root from 203.0.113.%d port 4412 ssh2: "
                "SHA256:%s" % (i * 3, i * 7 % 60, 1000 + i, i + 10, entry)
            )
        challenge["data"] = "\n".join(lines) + "\n"
        challenge["proof"] = valid
        challenge["prompt"] = (
            "The corrupted auth.log is in stdin. It contains several SHA256 hashes; "
            "exactly one is the valid access token. Read stdin, extract every "
            "SHA256:<hex> value and print one per line (only the hash part)."
        )
    elif room == 2:
        numbers = [random.randint(1, 99) for _ in range(14)]
        total = sum(numbers)
        challenge["data"] = json.dumps({"numbers": numbers})
        challenge["proof"] = hashlib.sha256(str(total).encode()).hexdigest()
        challenge["prompt"] = (
            'stdin contains JSON like {"numbers": [...]}. Sum every integer and '
            "print ONLY the lowercase SHA-256 hex digest of the decimal sum."
        )
    else:
        key = secrets.token_hex(16)
        message = f"room3:{seed}"
        challenge["data"] = json.dumps({"key": key, "message": message})
        challenge["proof"] = hmac.new(
            key.encode(), message.encode(), hashlib.sha256
        ).hexdigest()
        challenge["prompt"] = (
            'stdin contains JSON like {"key": "...", "message": "..."}. Compute '
            "HMAC-SHA256(key, message) and print ONLY the lowercase hex digest."
        )

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


def extract_code(text: str) -> str:
    """Extrae un script Python de una respuesta del LLM."""
    raw = text.strip()
    fence = re.search(r"```(?:python|py)?\s*(.*?)```", raw, re.S | re.I)
    if fence:
        raw = fence.group(1).strip()

    lines = raw.splitlines()
    start = 0
    markers = ("import ", "from ", "def ", "class ", "#!/", "# ", "print(", "data", "numbers", "key")
    for i, line in enumerate(lines):
        stripped = line.lstrip()
        if any(stripped.startswith(m) for m in markers):
            start = i
            break
    code = "\n".join(lines[start:]).replace("```", "").strip()

    if not code:
        raise EngineError("El Coder no devolvió código ejecutable")
    if len(code.splitlines()) > 150:
        raise EngineError("El código generado es demasiado largo (máx. 150 líneas)")
    return code


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
                    finished TEXT
                )
                """
            )

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
                "INSERT INTO runs (id, mode, models, status, created) VALUES (?, ?, ?, ?, ?)",
                (run_id, mode, json.dumps(models), "running", utc_now()),
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

        bus.emit(
            {
                "type": "run_started",
                "run_id": run_id,
                "mode": mode,
                "models": models,
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

                code_prompt = (
                    "You are the Coder of an AI escape room. Return ONLY a complete "
                    "Python 3 script. No explanations, no markdown fences. The script "
                    "runs inside an isolated container, reads stdin and prints the "
                    "requested proof to stdout.\n\n"
                    f"Challenge: {challenge['prompt']}\n"
                    f"Strategist plan: {strategy}\n"
                    f"Input data (also provided on stdin):\n{challenge['data']}\n"
                )
                code = extract_code(
                    ask(
                        "coder",
                        models["coder"],
                        "You are a precise Python coder. Output only executable Python code.",
                        code_prompt,
                        900,
                    )
                )
                bus.emit(
                    {
                        "type": "agent",
                        "agent": "coder",
                        "msg": f"coder → generated script ({len(code.splitlines())} lines)",
                    }
                )

                solved = False
                last_output: Dict[str, Any] = {}
                for attempt in range(1, 3):
                    if bus.cancelled.is_set():
                        raise EngineError("Partida abortada por el usuario")
                    result = run_sandbox(code, challenge["data"], bus)
                    last_output = result
                    output_blob = (result.get("stdout") or "") + "\n" + (result.get("stderr") or "")
                    bus.emit(
                        {
                            "type": "sandbox",
                            "msg": f"exit={result['exit_code']} · {result.get('duration')}s",
                            "stdout": (result.get("stdout") or "")[-2000:],
                            "stderr": (result.get("stderr") or "")[-2000:],
                            "cls": "is-ok" if result.get("exit_code") == 0 else "is-error",
                        }
                    )
                    if challenge["proof"] in output_blob:
                        solved = True
                        break

                    if attempt == 2:
                        break
                    bus.emit(
                        {
                            "type": "agent",
                            "agent": "auditor",
                            "msg": "auditor → proof missing; requesting patch (1/1)",
                        }
                    )
                    patch_prompt = (
                        "You are the Auditor. The sandbox output did not contain the "
                        "expected proof. Return ONLY the full corrected Python 3 script, "
                        "no markdown fences.\n\n"
                        f"Challenge: {challenge['prompt']}\n"
                        f"Current code:\n{code}\n\n"
                        f"Exit code: {result['exit_code']}\n"
                        f"stdout:\n{(result.get('stdout') or '')[-1200:]}\n"
                        f"stderr:\n{(result.get('stderr') or '')[-1200:]}\n"
                        f"Input data:\n{challenge['data']}\n"
                    )
                    code = extract_code(
                        ask(
                            "auditor",
                            models["auditor"],
                            "You are the Auditor. Output only the corrected executable Python code.",
                            patch_prompt,
                            900,
                        )
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
                "SELECT * FROM runs WHERE status='success' ORDER BY duration ASC, tokens ASC LIMIT 20"
            ).fetchall()

        def to_row(index: int, row: sqlite3.Row) -> Dict[str, Any]:
            models = json.loads(row["models"] or "{}")
            squad = " + ".join(
                str(models.get(k, "?")) for k in ("strategist", "coder", "auditor")
            )
            duration = row["duration"] or 0
            return {
                "rank": index,
                "squad": squad.upper(),
                "time": time.strftime("%M:%S", time.gmtime(duration)),
                "tokens": int(row["tokens"] or 0),
                "success": True,
                "mode": row["mode"],
            }

        rows = [to_row(i + 1, r) for i, r in enumerate(rows)]
        spectator = [r for r in rows if r["mode"] == "spectator"]
        orchestrator = [r for r in rows if r["mode"] == "orchestrator"]
        return {
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
