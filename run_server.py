#!/usr/bin/env python3
"""
Servidor web + API para AGENT RUSH (sin dependencias externas).

Sirve la carpeta web/ y expone:
    GET  /api/models   -> modelos de chat disponibles en Vultr
    GET  /api/presets  -> presets de modelos (balanced/fast/quality)
    GET  /api/agents   -> selección actual de modelos por agente
    POST /api/agents   -> guarda la selección de modelos por agente

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
import webbrowser
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config.models import discover_models, PRESETS
from config.model_profiles import ModelProfile, load_selection, save_selection

WEB_DIR = pathlib.Path(__file__).parent / "web"

# Leaderboard: todavía no hay runs reales verificadas por el árbitro.
# Sin datos simulados. Se llenará desde SQLite cuando exista el backend de runs.
LEADERBOARD = {
    "spectator": {"mode": "spectator", "rows": [], "has_runs": False},
    "orchestrator": {"mode": "orchestrator", "rows": [], "has_runs": False},
}


def _profiles_to_json(profiles) -> dict:
    return {agent: profile.to_dict() for agent, profile in profiles.items()}


class AgentRushHandler(SimpleHTTPRequestHandler):
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

    def do_OPTIONS(self) -> None:
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    # ---- routes ----
    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path == "/api/models":
            models = discover_models(api_key=os.getenv("VULTR_INFERENCE_API_KEY"))
            return self._send_json({"models": models})
        if path == "/api/presets":
            return self._send_json({"presets": PRESETS})
        if path == "/api/agents":
            return self._send_json({"agents": _profiles_to_json(load_selection())})
        if path == "/api/leaderboard":
            query = urlparse(self.path).query
            params = {}
            if query:
                for pair in query.split("&"):
                    if "=" in pair:
                        key, value = pair.split("=", 1)
                        params[key] = value
            mode = params.get("mode", "").lower()
            if mode in ("spectator", "orchestrator"):
                return self._send_json(LEADERBOARD[mode])
            # Si mode está ausente o es inválido, devolver ambos modos
            return self._send_json(
                {
                    "spectator": LEADERBOARD["spectator"],
                    "orchestrator": LEADERBOARD["orchestrator"],
                }
            )
        return super().do_GET()

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        if path != "/api/agents":
            return self._send_json({"error": "not found"}, 404)

        try:
            length = int(self.headers.get("Content-Length", 0))
            raw = self.rfile.read(length).decode("utf-8") if length else "{}"
            payload = json.loads(raw)
        except (ValueError, json.JSONDecodeError):
            return self._send_json({"error": "JSON inválido"}, 400)

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
    httpd = ThreadingHTTPServer(("127.0.0.1", args.port), AgentRushHandler)

    home_url = f"http://localhost:{args.port}/"
    game_url = f"http://localhost:{args.port}/game.html"
    config_url = f"http://localhost:{args.port}/config.html"
    
    print(f"AGENT RUSH server -> {home_url}")
    print(f"JUEGO             -> {game_url}")
    print(f"CONFIG MODEL CONFIG -> {config_url}")
    print("Ctrl+C para detener.")

    if not args.no_open:
        threading.Timer(0.8, lambda: webbrowser.open(home_url)).start()

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nServidor detenido.")


if __name__ == "__main__":
    main()
