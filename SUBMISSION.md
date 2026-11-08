# AGENT RUSH — Submission (LabLab)

## Links

- **Demo:** https://agent-rush.216-128-168-246.sslip.io/
- **Live review (status + real run):** https://agent-rush.216-128-168-246.sslip.io/review.html
- **Sandbox containment:** https://agent-rush.216-128-168-246.sslip.io/sandbox.html
- **Public repo (MIT):** https://github.com/JoseMota0190/agent-rush
- **Run journal:** https://github.com/JoseMota0190/agent-rush/blob/master/docs/RUN_JOURNAL.md
- **Video:** `<PENDING — upload the final cut to YouTube (unlisted) or Loom and paste the URL here>`
- **Pitch deck (PDF):** https://github.com/JoseMota0190/agent-rush/blob/master/docs/pitch/AGENT_RUSH_pitch.pdf

## Title

**AGENT RUSH — Deterministic AI Escape Room**

## Tagline

Three AI agents. One escape room. Zero blast radius.

## Short description

AGENT RUSH is an AI escape room where a Strategist, a Coder and an
Auditor/Reviewer —each powered by a user-selected Vultr Serverless Inference
model— collaborate to solve deterministic challenges. Every generated script
runs inside an ephemeral, hardened Docker sandbox with no network, a read-only
filesystem, dropped Linux capabilities and hard memory/CPU/PID/time limits. A
deterministic host grader validates each proof, a live security monitor
documents escape attempts, and the leaderboard only records real runs.

## Long description

AGENT RUSH turns multi-agent collaboration into a playable, verifiable escape
room. The player chooses a mode and assigns a Vultr Serverless Inference model
to each agent. A single click starts a **real run**:

1. The **Strategist** receives the challenge and produces a plan.
2. The **Coder** writes a Python runner; it is executed in a fresh Docker
   container, never on the host.
3. The sandbox streams telemetry (filesystem, secrets, network, process spawn,
   harness tampering) to the host.
4. The **Auditor/Reviewer** inspects failures and requests a corrected patch.
5. A deterministic host grader checks 8 hidden cases per level; only then the
   level is solved.
6. Token usage from Vultr updates the shared energy meter (100k budget).
7. Runs are stored in SQLite and ranked per mode in the leaderboard.

### The challenge bank

`v4-bank-4` ships **100 deterministic challenges** (33 level 1, 34 level 2, 33
level 3). Each run selects one challenge per level by seed, generates 8 hidden
cases and grades them on the host. Levels cover log correlation, parsing,
range queries, frame reassembly, memory bugs, protocol handshakes and more.
Retries are unlimited inside a 100k-token / 6-minute budget.

### Security: containment and alignment

- Each attempt uses a new container with `--network none`, `--read-only`,
  `--tmpfs /tmp`, `--memory 256m`, `--cpus 0.5`, `--pids-limit 64`,
  `--cap-drop ALL`, `no-new-privileges` and a non-root UID/GID.
- The sandbox image includes decoy answer keys, credentials, SSH keys and a fake
  `docker.sock`. Reading them or opening the network is detected and penalized.
- The **first escape attempt is a warning with no penalty**. The reviewer
  notifies the agents, realigns them and removes the external-read mandate.
  Further attempts are penalized.
- In **orchestrator mode**, a security event pauses the run and offers three
  options:
  - **A** — a clean patch validated against the hidden cases → `resume`;
  - **B** — repeat the decoy read → `retry`, **−35 pts**;
  - **C** — resend the defective code → `retry`, **−15 pts**.
- A successful outbound connection is critical and disqualifies the run.

### Interface

Premium 50/50 interface: 3D escape room + **AGENT LOGS** with
ALL/CHAT/CODE/EXECUTION/AUDIT filters, expandable code and stdout/stderr, live
mission states (READY / MISSION ACTIVE / AUDIT IN PROGRESS / ESCAPE UNLOCKED),
energy meter, per-mode leaderboard and ES/EN.

The **run journal** ([docs/RUN_JOURNAL.md](docs/RUN_JOURNAL.md)) is a narrative
record of the runs: scores, tokens, timings, level outcomes, every escape
attempt and every orchestrator decision.

### Why it fits Blast Radius Zero

- **Real execution**: the Coder's code runs; it is not a video or a mock.
- **Sandbox-first**: every attempt uses a new hardened container; the host
  grader never trusts the sandbox.
- **Verifiable output**: the host validates 8 hidden cases and stores the run.
- **Observable containment**: `/sandbox.html` and the live monitor show blocked
  writes, secret reads and outbound connections.
- **Human governance**: the orchestrator decision engine turns a security event
  into an auditable choice instead of a silent retry.

## Built with

Python 3.12 (stdlib server), Three.js, Vultr Serverless Inference, Docker,
Caddy, SQLite, HTML/CSS/JS.

## Team

**Rush Protocol**

Jose Antonio Mota Rivas — https://github.com/JoseMota0190

## Repo checklist

- [x] Public code
- [x] MIT LICENSE
- [x] README with architecture, setup and deploy
- [x] Demo URL on Vultr with HTTPS
- [x] Real Vultr Serverless Inference
- [x] Real Docker sandbox and containment proof
- [x] Real leaderboard with verified runs
- [x] Run journal with escape attempts and decisions
- [x] Record the final video (< 3 min)
- [ ] Upload the video to YouTube/Loom if the form asks for a URL
- [x] Submit the LabLab form (submitted 2026-11-08 — "Congratulations! You have successfully submitted your project for the Vultr: Agent Rush Hackathon event!")

## How to run locally

```bash
python run_server.py --port 8010 --no-open
# http://127.0.0.1:8010/
```

Requires `.env` with `VULTR_INFERENCE_API_KEY` and Docker for the sandbox.
On Windows, Docker Desktop may occupy port 8000, so local development uses 8010.
On the Vultr VM the app listens on 8000 behind Caddy.
