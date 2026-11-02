#!/usr/bin/env python3
"""
Lanzador del front-end AGENT RUSH.

Uso:
    python run_web.py            # sirve en http://localhost:8000
    python run_web.py --port 9000
    python run_web.py --no-open  # no abrir el navegador

No requiere dependencias: usa http.server de la librería estándar.
"""

import argparse
import functools
import http.server
import socketserver
import webbrowser
import threading
import pathlib

WEB_DIR = pathlib.Path(__file__).parent / "web"


def main() -> None:
    parser = argparse.ArgumentParser(description="Serve the AGENT RUSH UI")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--no-open", action="store_true")
    args = parser.parse_args()

    if not WEB_DIR.is_dir():
        raise SystemExit(f"No encuentro el directorio web/: {WEB_DIR}")

    handler = functools.partial(
        http.server.SimpleHTTPRequestHandler,
        directory=str(WEB_DIR),
    )

    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("127.0.0.1", args.port), handler) as httpd:
        url = f"http://localhost:{args.port}/"
        print(f"AGENT RUSH UI → {url}")
        print("Ctrl+C para detener.")
        if not args.no_open:
            threading.Timer(0.8, lambda: webbrowser.open(url)).start()
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nServidor detenido.")


if __name__ == "__main__":
    main()
