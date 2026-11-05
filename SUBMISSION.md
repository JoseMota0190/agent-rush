# AGENT RUSH — Submission (LabLab)

## Links

- **Demo:** https://agent-rush.216-128-168-246.sslip.io/
- **Sandbox containment:** https://agent-rush.216-128-168-246.sslip.io/sandbox.html
- **Repo público (MIT):** https://github.com/JoseMota0190/agent-rush
- **Video:** `docs/agent-rush-demo.mp4` (48 s). Si LabLab pide una URL, subilo a
  YouTube (unlisted) o Loom y pegá el link.

## Title

**AGENT RUSH — Deterministic AI Escape Room**

## Tagline

Three AI agents. One escape room. Zero blast radius.

## Short description

AGENT RUSH is an AI escape room where a Strategist, a Coder and an Auditor —
each powered by a user-selected Vultr Serverless Inference model — collaborate
to break out of three rooms. Every generated script runs inside an ephemeral,
hardened Docker sandbox with no network, a read-only filesystem, dropped Linux
capabilities and hard memory/CPU/PID/time limits. A deterministic referee
validates each proof, the energy meter tracks real tokens, and the leaderboard
only records verified runs.

## Long description

AGENT RUSH turns multi-agent collaboration into a playable, verifiable escape
room. The player chooses the mode and assigns a Vultr Serverless Inference model
to each agent (all available models are shown in the wizard). A single click
starts a **real run**:

1. The **Strategist** receives the room challenge and produces a plan.
2. The **Coder** writes a Python script; it is executed in a fresh Docker
   container, never on the host.
3. The **Auditor** inspects stdout/stderr and requests a corrected script if the
   proof is missing.
4. A deterministic referee checks the proof; only then the room is solved.
5. Token usage from Vultr updates the shared energy meter (100k budget).
6. Successful runs are stored in SQLite and shown in the leaderboard.

The three rooms are deterministic and generated per run: a corrupted auth log
with a hidden SHA-256 token, a checksum recovery challenge, and an HMAC-SHA256
firewall signature.

### Why it fits Blast Radius Zero

- **Real execution**: the Coder's code runs; it is not a video or a mock.
- **Sandbox-first**: every attempt uses a new container with
  `--network none`, `--read-only`, `--tmpfs /tmp`, `--memory 256m`,
  `--cpus 0.5`, `--pids-limit 64`, `--cap-drop ALL`,
  `no-new-privileges` and a 15 s timeout.
- **Verifiable output**: the server validates the proof and records the run.
- **Live containment demo**: `/sandbox.html` runs attempts to write to the host,
  read secrets and open a socket; all are blocked.

## Built with

Python 3.12 (stdlib server), Three.js, Vultr Serverless Inference, Docker,
Caddy, SQLite, HTML/CSS/JS.

## Team

Jose Antonio Mota Rivas — https://github.com/JoseMota0190

## Repo checklist

- [x] Código público
- [x] LICENSE MIT
- [x] README con arquitectura y deploy
- [x] Demo URL en Vultr con HTTPS
- [x] Vultr Serverless Inference real
- [x] Sandbox Docker real y prueba de contención
- [x] Leaderboard con runs reales
- [x] Video < 3 min
- [ ] Upload del video a YouTube/Loom (opcional si el form pide URL)
- [ ] Enviar el formulario en LabLab

## Cómo correr localmente

```bash
python run_server.py --port 8010 --no-open
# http://127.0.0.1:8010/
```

Requiere `.env` con `VULTR_INFERENCE_API_KEY` y Docker para el sandbox.
En Windows, Docker Desktop ocupa el puerto 8000; por eso local se usa 8010.
En la VM de Vultr la app corre en 8000 detrás de Caddy.
