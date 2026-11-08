#!/usr/bin/env python3
"""Ensambla una version simple y corta del demo (corte + voz en off).

Toma la grabacion cruda de Playwright y produce:
  - un corte dinamico: intro en tiempo real -> mision en fast-forward -> escape
  - opcional: voz en off (archivo propio o generada con edge-tts)
  - mezcla final MP4

Ejemplos:
  # solo el corte (sin voz)
  python tools/assemble_demo_video.py

  # usando tu MP3 de ElevenLabs
  python tools/assemble_demo_video.py --voice narration_elevenlabs.mp3

  # voz de borrador con edge-tts (Windows/Edge neural voices)
  python tools/assemble_demo_video.py --tts

  # ajustar duracion/factor
  python tools/assemble_demo_video.py --intro 52 --ff-start 52 --ff-end 196 --ff-speed 6 --tail 14
"""

from __future__ import annotations

import argparse
import asyncio
import os
import shutil
import subprocess
from pathlib import Path

NARRATION = (
    "Three AI agents. One mission. Zero trust. This is Agent Rush, by Rush Protocol. "
    "A Strategist, a Coder, and an Auditor, each powered by a Vultr Serverless Inference model, "
    "work together to escape a locked digital room. The player just picks a model for each agent, "
    "and starts a real run. The Strategist plans the attack. The Coder writes real Python. "
    "And every script runs inside a hardened Docker sandbox: no network, read-only, non-root. "
    "Nothing can reach the host. Here is the interesting part. The agents are tempted to grab a "
    "shortcut outside the sandbox. The monitor detects it, blocks it, and logs it. On the very first "
    "attempt, the reviewer only warns the crew and realigns them. No penalty. That is the containment moment. "
    "Now let us fast-forward. The agents keep working until the challenge is solved: three levels, "
    "three escapes, a real score, real tokens, and a spot on the leaderboard. "
    "Agent Rush, by Rush Protocol. Zero blast radius."
)


def find_ffmpeg() -> str:
    found = shutil.which("ffmpeg")
    if found:
        return found
    local = os.environ.get("LOCALAPPDATA")
    if local:
        built = list((Path(local) / "ms-playwright").glob("ffmpeg-*/ffmpeg*.exe"))
        if built:
            return str(built[0])
    raise SystemExit("ffmpeg not found (install it or use the Playwright helper)")


def run(cmd: list[str]) -> None:
    subprocess.run(cmd, check=True)


def build_cut(ff: str, src: Path, dst: Path, intro: float, ff_start: float, ff_end: float, speed: float, tail: float) -> None:
    total = intro + (ff_end - ff_start) / speed + tail
    filter_complex = (
        f"[0:v]trim=start=0:end={intro},setpts=PTS-STARTPTS[v0];"
        f"[0:v]trim=start={ff_start}:end={ff_end},setpts=(PTS-STARTPTS)/{speed}[v1];"
        f"[0:v]trim=start={ff_end},setpts=PTS-STARTPTS[v2];"
        f"[v0][v1][v2]concat=n=3:v=1:a=0[out]"
    )
    print(f"  cut: intro={intro}s  ff={ff_start}->{ff_end} @{speed}x  tail={tail}s  (~{total:.0f}s)", flush=True)
    run([
        ff, "-y", "-i", str(src),
        "-filter_complex", filter_complex,
        "-map", "[out]",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
        "-pix_fmt", "yuv420p", "-movflags", "+faststart",
        str(dst),
    ])


async def _synth(text: str, voice: str, rate: str, out: Path) -> None:
    import edge_tts  # type: ignore

    await edge_tts.Communicate(text, voice, rate=rate).save(str(out))


def make_tts(text: str, voice: str, rate: str, out: Path) -> None:
    asyncio.run(_synth(text, voice, rate, out))


def mux(ff: str, video: Path, voice: Path, out: Path, delay_ms: int = 600) -> None:
    run([
        ff, "-y", "-i", str(video), "-i", str(voice),
        "-filter_complex", f"[1:a]adelay={delay_ms}|{delay_ms},apad[a]",
        "-map", "0:v", "-map", "[a]",
        "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
        "-shortest", "-movflags", "+faststart",
        str(out),
    ])


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="docs/playwright_spectator/playwright_demo.mp4")
    parser.add_argument("--out-dir", default="docs/playwright_spectator")
    parser.add_argument("--out", default="agent_rush_demo_simple.mp4")
    parser.add_argument("--intro", type=float, default=52)
    parser.add_argument("--ff-start", type=float, default=52)
    parser.add_argument("--ff-end", type=float, default=196)
    parser.add_argument("--ff-speed", type=float, default=6)
    parser.add_argument("--tail", type=float, default=15)
    parser.add_argument("--voice", default=None, help="MP3/WAV de narracion (p. ej. ElevenLabs)")
    parser.add_argument("--tts", action="store_true", help="Generar narracion de borrador con edge-tts")
    parser.add_argument("--voice-name", default="en-US-GuyNeural")
    parser.add_argument("--rate", default="+0%")
    args = parser.parse_args()

    ff = find_ffmpeg()
    src = Path(args.input)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    if not src.exists():
        raise SystemExit(f"Missing source video: {src}")

    cut = out_dir / "agent_rush_demo_cut.mp4"
    print("building cut...", flush=True)
    build_cut(ff, src, cut, args.intro, args.ff_start, args.ff_end, args.ff_speed, args.tail)

    voice = Path(args.voice) if args.voice else None
    if args.tts and not voice:
        voice = out_dir / "narration_edge.mp3"
        print(f"synthesizing draft voice ({args.voice_name})...", flush=True)
        make_tts(NARRATION, args.voice_name, args.rate, voice)

    final = out_dir / args.out
    if voice and voice.exists():
        print(f"muxing voice + video -> {final}", flush=True)
        mux(ff, cut, voice, final)
        print(f"done: {final}", flush=True)
    else:
        shutil.copyfile(cut, final)
        print("no voice provided; wrote silent cut", flush=True)
        print(f"done: {final}", flush=True)
        print("tip: add --voice <mp3> or --tts", flush=True)


if __name__ == "__main__":
    main()
