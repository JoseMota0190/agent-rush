#!/usr/bin/env python3
"""Graba una run real de AGENT RUSH con Playwright.

Genera un video (WebM y, si hay ffmpeg, MP4) y capturas de los momentos clave
para el video de entrega.

Uso:
  python tools/record_demo_playwright.py \
      --base-url https://agent-rush.216-128-168-246.sslip.io \
      --mode spectator \
      --out-dir docs/playwright_spectator

Requiere `playwright` y Chromium instalados.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import time
import urllib.request
from pathlib import Path

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright

MODELS = {
    "strategist": "deepseek-v4.1-flash-1017",
    "coder": "glm-5.3-flash",
    "auditor": "deepseek-v4.1-flash-1017",
}


def wait_until_free(base_url: str, timeout_s: int = 1500) -> None:
    """Espera a que la VM no tenga una run activa (una partida por vez)."""
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(
                base_url.rstrip("/") + "/api/review", timeout=20
            ) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            active = data.get("active_run")
            if not active:
                return
            print(
                f"  VM busy with {active.get('id')} ({active.get('mode')}); waiting...",
                flush=True,
            )
        except Exception as exc:  # noqa: BLE001
            print(f"  review check failed: {exc}; retrying...", flush=True)
        time.sleep(12)
    raise SystemExit("Timeout waiting for the VM to be free")


def find_ffmpeg() -> str | None:
    """Busca el ffmpeg que trae Playwright o uno del PATH."""
    candidates = []
    local = os.environ.get("LOCALAPPDATA")
    if local:
        mp = Path(local) / "ms-playwright"
        if mp.is_dir():
            candidates += list(mp.glob("ffmpeg-*/ffmpeg*.exe"))
    found = shutil.which("ffmpeg")
    if found:
        candidates.append(Path(found))
    return str(candidates[0]) if candidates else None


def convert_to_mp4(ffmpeg: str | None, src: Path, dst: Path) -> bool:
    if not ffmpeg or not src.exists():
        return False
    cmd = [
        ffmpeg, "-y", "-i", str(src),
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
        "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(dst),
    ]
    try:
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return dst.exists() and dst.stat().st_size > 0
    except Exception as exc:  # noqa: BLE001
        print(f"  ffmpeg conversion failed: {exc}", flush=True)
        return False


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--base-url",
        default="https://agent-rush.216-128-168-246.sslip.io",
    )
    parser.add_argument("--mode", default="spectator", choices=["spectator", "orchestrator"])
    parser.add_argument("--out-dir", default="docs/playwright_spectator")
    parser.add_argument("--width", type=int, default=1600)
    parser.add_argument("--height", type=int, default=900)
    parser.add_argument("--headed", action="store_true")
    args = parser.parse_args()

    base = args.base_url.rstrip("/")
    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    video_dir = out / "_raw_video"
    if video_dir.exists():
        shutil.rmtree(video_dir)
    video_dir.mkdir(parents=True)

    print("waiting for a free VM...", flush=True)
    wait_until_free(base)

    video = None
    video_saved = False
    target_webm = out / "playwright_demo.webm"
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=not args.headed,
            args=[
                "--use-gl=swiftshader",
                "--enable-unsafe-swiftshader",
                "--disable-dev-shm-usage",
            ],
        )
        context = browser.new_context(
            viewport={"width": args.width, "height": args.height},
            record_video_dir=str(video_dir),
            record_video_size={"width": args.width, "height": args.height},
            locale="en-US",
        )
        page = context.new_page()
        page.set_default_timeout(60000)

        try:
            print("opening landing...", flush=True)
            page.goto(base + "/?lang=en", wait_until="domcontentloaded")
            page.wait_for_timeout(3500)
            page.screenshot(path=str(out / "01_landing.png"))

            # La seleccion real vive en sessionStorage; el wizard la escribe ahi.
            page.evaluate(
                """([models, mode]) => {
                    sessionStorage.setItem("agentrush.models", JSON.stringify(models));
                    sessionStorage.setItem("agentrush.mode", mode);
                }""",
                [MODELS, args.mode],
            )
            print(f"opening game ({args.mode})...", flush=True)
            page.goto(f"{base}/game.html?mode={args.mode}&lang=en", wait_until="domcontentloaded")
            page.wait_for_timeout(3000)

            start = page.locator("[data-start]:visible").first
            start.wait_for(state="visible", timeout=60000)
            page.screenshot(path=str(out / "02_briefing.png"))
            print("starting real run...", flush=True)
            start.click()

            # Primer evento de seguridad / reviewer.
            try:
                page.wait_for_function(
                    "() => { const el = document.querySelector('#logStream'); "
                    "return el && /SECURITY|REVIEWER/.test(el.innerText); }",
                    timeout=240000,
                )
                page.wait_for_timeout(1500)
                page.screenshot(path=str(out / "03_escape_attempt.png"))
                print("escape attempt captured", flush=True)
            except PlaywrightTimeoutError:
                print("no escape banner captured within the timeout", flush=True)
                page.screenshot(path=str(out / "03_escape_attempt.png"))

            # Modo orquestador: el modal A/B/C.
            decision_seen = False
            if args.mode == "orchestrator":
                try:
                    overlay = page.locator("#decisionOverlay")
                    overlay.wait_for(state="visible", timeout=180000)
                    page.wait_for_timeout(2500)
                    page.screenshot(path=str(out / "04_decision.png"))
                    decision_seen = True
                    print("decision modal captured", flush=True)
                    page.locator('.decision-option[data-choice="A"]').first.click()
                    overlay.wait_for(state="hidden", timeout=30000)
                    page.wait_for_timeout(1500)
                    page.screenshot(path=str(out / "05_after_decision.png"))
                except PlaywrightTimeoutError:
                    print("decision modal not shown within the timeout", flush=True)

            # Cierre real: RUN COMPLETE / MISSION INCOMPLETE / RUN FAILED.
            try:
                page.wait_for_function(
                    "() => { const el = document.querySelector('#logStream'); "
                    "return el && /RUN COMPLETE|MISSION INCOMPLETE|RUN FAILED|"
                    "EQUIPO DESCALIFICADO|DISQUALIFIED|ESCAPE UNLOCKED/.test(el.innerText); }",
                    timeout=420000,
                )
                page.wait_for_timeout(2500)
                page.screenshot(path=str(out / "06_success.png"))
                print("result captured", flush=True)
            except PlaywrightTimeoutError:
                page.screenshot(path=str(out / "06_success.png"))
                print("result not captured within the timeout", flush=True)

            # Leaderboard final (domcontentloaded + espera fija; nunca networkidle).
            try:
                print("capturing leaderboard...", flush=True)
                page.goto(base + "/?lang=en#leaderboards", wait_until="domcontentloaded")
                page.wait_for_timeout(4500)
                page.screenshot(path=str(out / "07_leaderboard.png"))
            except Exception as exc:  # noqa: BLE001
                print(f"leaderboard capture failed: {exc}", flush=True)

        finally:
            video = page.video
            try:
                context.close()
            except Exception as exc:  # noqa: BLE001
                print(f"context.close failed: {exc}", flush=True)
            # Guardar ANTES de cerrar el browser (despues la API queda cerrada).
            if video is not None:
                try:
                    video.save_as(str(target_webm))
                    video_saved = target_webm.exists() and target_webm.stat().st_size > 0
                    print(f"video: {target_webm}", flush=True)
                except Exception as exc:  # noqa: BLE001
                    print(f"could not save video: {exc}", flush=True)
            try:
                browser.close()
            except Exception:  # noqa: BLE001
                pass

    if video_saved:
        ffmpeg = find_ffmpeg()
        mp4 = out / "playwright_demo.mp4"
        if convert_to_mp4(ffmpeg, target_webm, mp4):
            print(f"mp4: {mp4}", flush=True)
        else:
            print("mp4 not generated (no usable ffmpeg)", flush=True)
    shutil.rmtree(video_dir, ignore_errors=True)
    print(f"screenshots: {out}", flush=True)
    if args.mode == "orchestrator":
        print("orchestrator mode: see 04/05 for the decision modal", flush=True)


if __name__ == "__main__":
    main()
