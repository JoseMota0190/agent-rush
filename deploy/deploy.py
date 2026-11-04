#!/usr/bin/env python3
"""
Provisiona una VM en Vultr y despliega AGENT RUSH.

Requisitos:
  - VULTR_API_KEY en .env (key general de la cuenta, NO la de Inference).
  - ~/.ssh/agent_rush y ~/.ssh/agent_rush.pub (se generan con ssh-keygen).
  - VULTR_INFERENCE_API_KEY en .env.

Uso:
  python deploy/deploy.py --region sao --plan vc2-1c-2gb

El script:
  1. Crea/reutiliza la SSH key en Vultr.
  2. Crea una instancia Ubuntu 24.04.
  3. Espera a que esté activa y acepte SSH.
  4. Empaqueta el proyecto, lo copia y corre deploy/setup.sh.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
API = "https://api.vultr.com/v2"
SSH_KEY = Path.home() / ".ssh" / "agent_rush"
SSH_PUB = Path.home() / ".ssh" / "agent_rush.pub"


def load_env() -> dict:
    values = {}
    env_path = BASE / ".env"
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def api(method: str, path: str, body: dict | None = None, key: str = "") -> dict:
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(
        API + path,
        data=data,
        headers={
            "Authorization": "Bearer " + key,
            "Content-Type": "application/json",
        },
        method=method,
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            raw = resp.read().decode("utf-8")
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:500]
        raise SystemExit(f"Vultr API {method} {path} -> HTTP {exc.code}: {detail}")


def ensure_ssh_key(key: str) -> str:
    if not SSH_PUB.exists():
        raise SystemExit(f"Falta {SSH_PUB}. Generala con ssh-keygen.")
    public = SSH_PUB.read_text(encoding="utf-8").strip()
    keys = api("GET", "/ssh-keys?per_page=500", key=key).get("ssh_keys", [])
    for item in keys:
        if item.get("name") == "agent-rush":
            return item["id"]
    created = api(
        "POST",
        "/ssh-keys",
        {"name": "agent-rush", "ssh_key": public},
        key=key,
    )
    return created["ssh_key"]["id"]


def choose_os(key: str) -> int:
    items = api("GET", "/os?per_page=500", key=key).get("os", [])
    candidates = [
        item
        for item in items
        if "ubuntu 24.04" in item.get("name", "").lower()
        and item.get("arch") == "x64"
    ]
    if not candidates:
        raise SystemExit("No encontré Ubuntu 24.04 x64 en Vultr.")
    candidates.sort(key=lambda item: item.get("id", 0), reverse=True)
    return int(candidates[0]["id"])


def choose_plan(key: str, wanted: str, region: str) -> str:
    plans = api("GET", "/plans?per_page=500", key=key).get("plans", [])
    for plan in plans:
        if plan.get("id") == wanted and region in (plan.get("locations") or []):
            return wanted
    for plan in plans:
        if plan.get("id", "").startswith("vc2-") and region in (plan.get("locations") or []):
            return plan["id"]
    raise SystemExit(f"No hay plan disponible en la región {region}.")


def wait_instance(key: str, instance_id: str, timeout: int = 600) -> dict:
    started = time.time()
    while time.time() - started < timeout:
        data = api("GET", f"/instances/{instance_id}", key=key).get("instance", {})
        ip = data.get("main_ip", "0.0.0.0")
        status = data.get("status", "?")
        print(f"  instance {status} ip={ip}", flush=True)
        if status == "active" and ip not in ("", "0.0.0.0"):
            return data
        time.sleep(10)
    raise SystemExit("Timeout esperando la instancia.")


def wait_ssh(ip: str, timeout: int = 300) -> None:
    started = time.time()
    while time.time() - started < timeout:
        proc = subprocess.run(
            [
                "ssh", "-i", str(SSH_KEY),
                "-o", "StrictHostKeyChecking=accept-new",
                "-o", "ConnectTimeout=10",
                "-o", "BatchMode=yes",
                f"root@{ip}", "echo ok",
            ],
            capture_output=True,
        )
        if proc.returncode == 0:
            return
        time.sleep(5)
    raise SystemExit("Timeout esperando SSH.")


def make_tar() -> Path:
    tmp = Path(tempfile.gettempdir()) / "agent-rush-deploy.tgz"
    if tmp.exists():
        tmp.unlink()

    def skip(name: str) -> bool:
        parts = set(Path(name).parts)
        if parts & {".git", "__pycache__", ".opencode", "data", "node_modules"}:
            return True
        return name.endswith((".pyc", ".log"))

    with tarfile.open(tmp, "w:gz") as tar:
        tar.add(BASE / "web", arcname="web", filter=lambda ti: None if skip(ti.name) else ti)
        for directory in ("config", "llm", "agents", "tools", "challenges", "core", "deploy"):
            path = BASE / directory
            if path.exists():
                tar.add(path, arcname=directory, filter=lambda ti: None if skip(ti.name) else ti)
        for filename in (
            "run_server.py", "run_engine.py", "main.py", "referee.py",
            "requirements.txt", "README.md", "LICENSE", ".env",
        ):
            path = BASE / filename
            if path.exists():
                tar.add(path, arcname=filename)
    return tmp


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--region", default="sao")
    parser.add_argument("--plan", default="vc2-1c-2gb")
    args = parser.parse_args()

    env = load_env()
    key = env.get("VULTR_API_KEY", "")
    if not key:
        raise SystemExit("Falta VULTR_API_KEY en .env (key general de la cuenta).")
    if not env.get("VULTR_INFERENCE_API_KEY"):
        print("ADVERTENCIA: VULTR_INFERENCE_API_KEY está vacía.", flush=True)

    os_id = choose_os(key)
    plan = choose_plan(key, args.plan, args.region)
    ssh_id = ensure_ssh_key(key)
    print(f"OS={os_id} plan={plan} region={args.region} sshkey={ssh_id}", flush=True)

    created = api(
        "POST",
        "/instances",
        {
            "region": args.region,
            "plan": plan,
            "os_id": os_id,
            "sshkey_ids": [ssh_id],
            "label": "agent-rush",
            "hostname": "agent-rush",
            "enable_ipv6": True,
            "backups": "disabled",
            "ddos_protection": True,
        },
        key=key,
    )
    instance_id = created["instance"]["id"]
    print(f"instance_id={instance_id}", flush=True)
    instance = wait_instance(key, instance_id)
    ip = instance["main_ip"]
    host = f"agent-rush.{ip.replace('.', '-')}.sslip.io"
    print(f"IP={ip} host={host}", flush=True)

    wait_ssh(ip)
    tar_path = make_tar()
    print(f"copying {tar_path} ({tar_path.stat().st_size // 1024} KiB)…", flush=True)
    subprocess.run(
        [
            "scp", "-i", str(SSH_KEY),
            "-o", "StrictHostKeyChecking=accept-new",
            str(tar_path), f"root@{ip}:/tmp/agent-rush.tgz",
        ],
        check=True,
    )
    tar_path.unlink(missing_ok=True)
    remote = (
        "set -e; "
        "mkdir -p /opt/agent-rush; "
        "tar -xzf /tmp/agent-rush.tgz -C /opt/agent-rush; "
        "rm -f /tmp/agent-rush.tgz; "
        f"AGENT_RUSH_HOST={host} bash /opt/agent-rush/deploy/setup.sh"
    )
    subprocess.run(
        [
            "ssh", "-i", str(SSH_KEY),
            "-o", "StrictHostKeyChecking=accept-new",
            f"root@{ip}", remote,
        ],
        check=True,
    )
    print("\nDEPLOY OK")
    print(f"https://{host}/")
    print("Health local:", "http://127.0.0.1:8000/api/health")


if __name__ == "__main__":
    main()
