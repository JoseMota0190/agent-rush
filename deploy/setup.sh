#!/usr/bin/env bash
# Deploy AGENT RUSH en una VM Ubuntu 24.04 de Vultr.
# Uso (como root, con el repo ya copiado en /opt/agent-rush):
#   AGENT_RUSH_HOST=agent-rush.1-2-3-4.sslip.io bash deploy/setup.sh
set -euo pipefail

APP_DIR="/opt/agent-rush"
HOST="${AGENT_RUSH_HOST:-}"

if [[ $EUID -ne 0 ]]; then
  echo "Ejecutá como root (sudo)." >&2
  exit 1
fi

if [[ -z "$HOST" ]]; then
  echo "Falta AGENT_RUSH_HOST (ej: agent-rush.1-2-3-4.sslip.io)" >&2
  exit 1
fi

if [[ ! -f "$APP_DIR/run_server.py" ]]; then
  echo "Faltan los archivos en $APP_DIR (copiá el repo primero)." >&2
  exit 1
fi

if [[ ! -f "$APP_DIR/.env" ]]; then
  echo "Falta $APP_DIR/.env (VULTR_INFERENCE_API_KEY)." >&2
  exit 1
fi

echo "== Paquetes base =="
export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y docker.io python3 curl ufw

echo "== Docker =="
systemctl enable --now docker
docker pull python:3.12-slim
docker pull caddy:2

echo "== Sandbox con senuelos de seguridad =="
docker build -t agent-rush-sandbox:latest \
  -f "$APP_DIR/deploy/sandbox/Dockerfile" "$APP_DIR/deploy/sandbox"
for kv in \
  "AGENT_RUSH_SANDBOX_IMAGE=agent-rush-sandbox:latest" \
  "AGENT_RUSH_MAX_ATTEMPTS=0" \
  "AGENT_RUSH_RUN_TIME_LIMIT_S=360" \
  "AGENT_RUSH_MIN_PRESENTATION_S=180" \
  "VULTR_REASONING_EFFORT=medium"; do
  key="${kv%%=*}"
  grep -q "^${key}=" "$APP_DIR/.env" || echo "$kv" >> "$APP_DIR/.env"
done

echo "== App =="
mkdir -p "$APP_DIR/data"
install -m 0644 "$APP_DIR/deploy/agent-rush.service" /etc/systemd/system/agent-rush.service

echo "== Caddy (contenedor, red host) =="
docker rm -f agent-rush-caddy >/dev/null 2>&1 || true
docker run -d \
  --name agent-rush-caddy \
  --restart unless-stopped \
  --network host \
  -e "AGENT_RUSH_HOST=$HOST" \
  -v "$APP_DIR/deploy/Caddyfile:/etc/caddy/Caddyfile:ro" \
  -v agent_rush_caddy_data:/data \
  -v agent_rush_caddy_config:/config \
  caddy:2

echo "== Firewall =="
ufw allow 22/tcp
ufw allow 80/tcp
ufw allow 443/tcp
ufw --force enable

echo "== Servicios =="
systemctl daemon-reload
systemctl enable --now agent-rush.service
systemctl restart agent-rush.service

echo "== Estado =="
sleep 2
systemctl --no-pager --full status agent-rush.service | head -20 || true
curl -fsS "http://127.0.0.1:8000/api/health" && echo
echo "Deploy listo: https://$HOST/"
echo "Esperá 10-30 s a que Caddy emita el certificado HTTPS."
