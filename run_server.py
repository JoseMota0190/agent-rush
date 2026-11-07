#!/usr/bin/env python3
"""
Servidor web + API para AGENT RUSH (solo stdlib).

Sirve web/ y expone:
    GET  /api/models
    GET  /api/presets
    GET  /api/agents
    POST /api/agents
    GET  /api/leaderboard
    GET  /api/health
    GET  /api/review          (snapshot en vivo para revisión)
    POST /api/runs
    GET  /api/runs/<id>/events   (SSE)
    POST /api/runs/<id>/abort

Uso:
    python run_server.py
    python run_server.py --port 9000 --no-open
"""

import argparse
import json
import os
import pathlib
import sys
import threading
import time
import webbrowser
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

BASE_DIR = pathlib.Path(__file__).parent
sys.path.insert(0, str(BASE_DIR))


def _load_env(path: str = ".env") -> None:
    """Carga .env sin dependencias externas (no pisa variables ya definidas)."""
    env_path = BASE_DIR / path
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and value and key not in os.environ:
            os.environ[key] = value


_load_env()

import challenges
import scoring
from config.models import discover_models, PRESETS
from config.model_profiles import ModelProfile, load_selection, save_selection
from run_engine import (
    MANAGER,
    EngineError,
    SandboxError,
    sandbox_probe,
    CHALLENGE_VERSION,
    CONTAINER_TIMEOUT_S,
    SANDBOX_FLAGS,
    SANDBOX_IMAGE,
    MAX_ROOM_ATTEMPTS,
)

WEB_DIR = BASE_DIR / "web"

_MODELS_CACHE = {"ts": 0.0, "data": None}
_MODELS_LOCK = threading.Lock()


def get_models() -> list:
    with _MODELS_LOCK:
        now = time.time()
        if _MODELS_CACHE["data"] is not None and now - _MODELS_CACHE["ts"] < 300:
            return _MODELS_CACHE["data"]
        data = discover_models(api_key=os.getenv("VULTR_INFERENCE_API_KEY"))
        _MODELS_CACHE["data"] = data
        _MODELS_CACHE["ts"] = now
        return data


def _profiles_to_json(profiles) -> dict:
    return {agent: profile.to_dict() for agent, profile in profiles.items()}


class AgentRushHandler(SimpleHTTPRequestHandler):
    server_version = "AgentRush/1.0"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(WEB_DIR), **kwargs)

    # ---- helpers ----
    def _send_json(self, obj, status: int = 200) -> None:
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        self.wfile.write(body)

    def _read_json(self) -> dict:
        try:
            length = int(self.headers.get("Content-Length", 0))
            raw = self.rfile.read(length).decode("utf-8") if length else "{}"
            payload = json.loads(raw)
            return payload if isinstance(payload, dict) else {}
        except (ValueError, json.JSONDecodeError):
            return {}

    def _sse_event(self, event: dict) -> None:
        data = json.dumps(event, ensure_ascii=False)
        self.wfile.write(f"data: {data}\n\n".encode("utf-8"))
        self.wfile.flush()

    def _stream_run(self, run: dict) -> None:
        bus = run["bus"]
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Cache-Control", "no-cache, no-transform")
        self.send_header("Connection", "close")
        self.send_header("X-Accel-Buffering", "no")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.close_connection = True

        terminal = {"run_completed", "run_failed", "aborted", "disqualified"}
        try:
            self.wfile.write(b"retry: 3000\n\n")
            self.wfile.flush()
            last_seq = 0
            for event in bus.history():
                last_seq = max(last_seq, int(event.get("seq", 0)))
                self._sse_event(event)
                if event.get("type") in terminal:
                    return

            while True:
                event = bus.next_event(timeout=15.0)
                if event is None:
                    if bus.closed:
                        return
                    self.wfile.write(b": ping\n\n")
                    self.wfile.flush()
                    continue
                if int(event.get("seq", 0)) <= last_seq:
                    continue
                last_seq = int(event.get("seq", 0))
                self._sse_event(event)
                if event.get("type") in terminal:
                    return
        except (BrokenPipeError, ConnectionResetError, OSError):
            return

    def do_OPTIONS(self) -> None:
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    # ---- GET ----
    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/api/models":
            return self._send_json({"models": get_models()})
        if path == "/api/presets":
            return self._send_json({"presets": PRESETS})
        if path == "/api/agents":
            return self._send_json({"agents": _profiles_to_json(load_selection())})
        if path == "/api/leaderboard":
            board = MANAGER.leaderboard()
            params = parse_qs(parsed.query)
            mode = params.get("mode", [""])[0].lower()
            if mode in ("spectator", "orchestrator"):
                return self._send_json(board[mode])
            return self._send_json(board)
        if path == "/api/health":
            return self._send_json({"ok": True, "has_key": bool(os.getenv("VULTR_INFERENCE_API_KEY"))})
        if path == "/api/review":
            models = get_models()
            return self._send_json(
                {
                    "project": "AGENT RUSH",
                    "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                    "challenge_version": CHALLENGE_VERSION,
                    "bank": {
                        "challenges": len(challenges.POOL),
                        "levels": {
                            str(level): len(challenges.LEVELS[level])
                            for level in (1, 2, 3)
                        },
                        "cases_per_level": len(challenges.SIZES),
                        "level_budgets": {
                            str(level): budget
                            for level, budget in challenges.LEVEL_BUDGET.items()
                        },
                        "scoring_weights": {
                            str(level): weight
                            for level, weight in scoring.WEIGHTS.items()
                        },
                        "max_attempts": MAX_ROOM_ATTEMPTS,
                    },
                    "models": {
                        "count": len(models),
                        "ids": [m.get("id") for m in models if m.get("id")],
                    },
                    "leaderboard": MANAGER.leaderboard(),
                    "active_run": MANAGER.current(),
                    "stats": MANAGER.stats(),
                    "sandbox": {
                        "image": SANDBOX_IMAGE,
                        "flags": SANDBOX_FLAGS,
                        "timeout_seconds": CONTAINER_TIMEOUT_S,
                        "case_timeout_seconds": challenges.CASE_TIMEOUT_S,
                        "attempts_per_room": MAX_ROOM_ATTEMPTS,
                    },
                    "endpoints": {
                        "runs": "POST /api/runs",
                        "events": "GET /api/runs/<id>/events",
                        "abort": "POST /api/runs/<id>/abort",
                        "sandbox_probe": "POST /api/sandbox/probe",
                    },
                    "links": {
                        "landing": "/",
                        "game": "/game.html",
                        "review": "/review.html",
                        "sandbox": "/sandbox.html",
                        "repo": "https://github.com/JoseMota0190/agent-rush",
                    },
                    "has_inference_key": bool(os.getenv("VULTR_INFERENCE_API_KEY")),
                }
            )

        parts = path.strip("/").split("/")
        if len(parts) == 4 and parts[:2] == ["api", "runs"] and parts[3] == "events":
            run = MANAGER.get_run(parts[2])
            if not run:
                return self._send_json({"error": "run no encontrada"}, 404)
            return self._stream_run(run)

        return super().do_GET()

    # ---- POST ----
    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/api/agents":
            payload = self._read_json()
            incoming = payload.get("agents", payload)
            if not isinstance(incoming, dict):
                return self._send_json({"error": "formato inválido"}, 400)

            profiles = load_selection()
            for agent, value in incoming.items():
                if agent not in profiles:
                    continue
                base = profiles[agent]
                if isinstance(value, str):
                    model_id, extra = value, {}
                elif isinstance(value, dict):
                    model_id = value.get("model_id", base.model_id)
                    extra = value
                else:
                    continue
                profiles[agent] = ModelProfile(
                    agent=agent,
                    model_id=model_id,
                    base_url=extra.get("base_url", base.base_url),
                    api_key_env=extra.get("api_key_env", base.api_key_env),
                    temperature=float(extra.get("temperature", base.temperature)),
                    max_tokens=int(extra.get("max_tokens", base.max_tokens)),
                )
            save_selection(profiles)
            return self._send_json({"ok": True, "agents": _profiles_to_json(profiles)})

        if path == "/api/runs":
            payload = self._read_json()
            mode = payload.get("mode")
            models = payload.get("models")
            seed = payload.get("seed")
            if mode not in ("spectator", "orchestrator"):
                return self._send_json({"error": "modo inválido"}, 400)
            if not isinstance(models, dict) or not all(
                isinstance(models.get(agent), str) and models.get(agent)
                for agent in ("strategist", "coder", "auditor")
            ):
                return self._send_json(
                    {"error": "Elegí un modelo para los tres agentes."}, 400
                )
            if seed is not None and not isinstance(seed, str):
                return self._send_json({"error": "seed inválida"}, 400)

            available = {m.get("id") for m in get_models() if m.get("id")}
            invalid = [models[a] for a in ("strategist", "coder", "auditor") if models[a] not in available]
            if invalid:
                return self._send_json(
                    {"error": "Modelo no disponible: " + ", ".join(invalid)}, 400
                )

            try:
                run = MANAGER.start(
                    mode,
                    {a: models[a] for a in ("strategist", "coder", "auditor")},
                    seed=seed,
                )
            except EngineError as exc:
                return self._send_json({"error": str(exc)}, 429 if "en curso" in str(exc) else 503)
            return self._send_json(
                {
                    "run_id": run["id"],
                    "mode": mode,
                    "models": run["models"],
                    "seed": run.get("seed"),
                    "challenges": run.get("challenges", []),
                    "challenge_version": CHALLENGE_VERSION,
                },
                201,
            )

        if path == "/api/sandbox/probe":
            try:
                return self._send_json({"results": sandbox_probe()})
            except SandboxError as exc:
                return self._send_json({"error": str(exc)}, 503)

        parts = path.strip("/").split("/")
        if len(parts) == 4 and parts[:2] == ["api", "runs"] and parts[3] == "abort":
            ok = MANAGER.abort(parts[2])
            if not ok:
                return self._send_json({"error": "run no encontrada"}, 404)
            return self._send_json({"ok": True})

        return self._send_json({"error": "not found"}, 404)

    def log_message(self, fmt, *args) -> None:
        return


def main() -> None:
    parser = argparse.ArgumentParser(description="AGENT RUSH — servidor web + API")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--no-open", action="store_true")
    args = parser.parse_args()

    if not WEB_DIR.is_dir():
        raise SystemExit(f"No encuentro el directorio web/: {WEB_DIR}")

    ThreadingHTTPServer.allow_reuse_address = True
    ThreadingHTTPServer.daemon_threads = True
    httpd = ThreadingHTTPServer(("127.0.0.1", args.port), AgentRushHandler)

    home_url = f"http://localhost:{args.port}/"
    print(f"AGENT RUSH server -> {home_url}")
    print(f"JUEGO             -> {home_url}game.html")
    print(f"RUNS              -> POST /api/runs · GET /api/runs/<id>/events")
    print("Ctrl+C para detener.")

    if not args.no_open:
        threading.Timer(0.8, lambda: webbrowser.open(home_url)).start()

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nServidor detenido.")


if __name__ == "__main__":
    main()
