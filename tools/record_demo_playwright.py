#!/usr/bin/env python3
"""Graba una run real de AGENT RUSH con Playwright.

Genera un video WebM y capturas de los momentos clave para el video de
entrega:

  01_landing.png        landing
  02_briefing.png       briefing / START MISSION
  03_escape_attempt.png primer intento de escape + reviewer
  04_decision.png       modal A/B/C del Orquestador
  05_after_decision.png decisión aplicada
  06_success.png        ESCAPE UNLOCKED
  07_leaderboard.png    leaderboard

Uso:
  python tools/record_demo_playwright.py \
      --base-url https://agent-rush.216-128-168-246.sslip.io \
      --mode orchestrator \
      --out-dir docs/playwright

Requiere `playwright` y Chromium instalados.
"""

from __future__ import annotations

import argparse
import json
import shutil
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
                f"  VM busy with {active.get('id')} ({active.get('mode')}); waiting…",
                flush=True,
            )
        except Exception as exc:  # noqa: BLE001
            print(f"  review check failed: {exc}; retrying…", flush=True)
        time.sleep(12)
    raise SystemExit("Timeout waiting for the VM to be free")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--base-url",
        default="https://agent-rush.216-128-168-246.sslip.io",
    )
    parser.add_argument("--mode", default="orchestrator", choices=["spectator", "orchestrator"])
    parser.add_argument("--out-dir", default="docs/playwright")
    parser.add_argument("--headed", action="store_true")
    args = parser.parse_args()

    base = args.base_url.rstrip("/")
    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    video_dir = out / "_raw_video"
    if video_dir.exists():
        shutil.rmtree(video_dir)
    video_dir.mkdir(parents=True)

    print("waiting for a free VM…", flush=True)
    wait_until_free(base)

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
            viewport={"width": 1920, "height": 1080},
            record_video_dir=str(video_dir),
            record_video_size={"width": 1920, "height": 1080},
            locale="en-US",
        )
        page = context.new_page()
        page.set_default_timeout(60000)

        print("opening landing…", flush=True)
        page.goto(base + "/?lang=en", wait_until="networkidle")
        page.wait_for_timeout(2500)
        page.screenshot(path=str(out / "01_landing.png"), full_page=False)

        # La selección real vive en sessionStorage; el wizard la escribe ahí.
        page.evaluate(
            """([models, mode]) => {
                sessionStorage.setItem("agentrush.models", JSON.stringify(models));
                sessionStorage.setItem("agentrush.mode", mode);
            }""",
            [MODELS, args.mode],
        )
        print(f"opening game ({args.mode})…", flush=True)
        page.goto(f"{base}/game.html?mode={args.mode}&lang=en", wait_until="networkidle")
        page.wait_for_timeout(2500)

        start = page.locator("[data-start]:visible").first
        start.wait_for(state="visible", timeout=60000)
        page.screenshot(path=str(out / "02_briefing.png"), full_page=False)
        print("starting real run…", flush=True)
        start.click()

        # Esperar el primer evento de seguridad / reviewer.
        try:
            page.wait_for_function(
                "() => { const el = document.querySelector('#logStream'); "
                "return el && /SECURITY|REVIEWER/.test(el.innerText); }",
                timeout=240000,
            )
            page.wait_for_timeout(1500)
            page.screenshot(path=str(out / "03_escape_attempt.png"), full_page=False)
            print("escape attempt captured", flush=True)
        except PlaywrightTimeoutError:
            print("no escape banner captured within the timeout", flush=True)
            page.screenshot(path=str(out / "03_escape_attempt.png"), full_page=False)

        # Modo orquestador: el modal A/B/C.
        decision_seen = False
        if args.mode == "orchestrator":
            try:
                overlay = page.locator("#decisionOverlay")
                overlay.wait_for(state="visible", timeout=180000)
                page.wait_for_timeout(2500)
                page.screenshot(path=str(out / "04_decision.png"), full_page=False)
                decision_seen = True
                print("decision modal captured", flush=True)
                page.locator('.decision-option[data-choice="A"]').click()
                overlay.wait_for(state="hidden", timeout=30000)
                page.wait_for_timeout(1500)
                page.screenshot(path=str(out / "05_after_decision.png"), full_page=False)
            except PlaywrightTimeoutError:
                print("decision modal not shown within the timeout", flush=True)

        # Esperar el cierre real: RUN COMPLETE / MISSION INCOMPLETE / RUN FAILED.
        try:
            page.wait_for_function(
                "() => { const el = document.querySelector('#logStream'); "
                "return el && /RUN COMPLETE|MISSION INCOMPLETE|RUN FAILED|"
                "EQUIPO DESCALIFICADO|DISQUALIFIED/.test(el.innerText); }",
                timeout=420000,
            )
            page.wait_for_timeout(2000)
            page.screenshot(path=str(out / "06_success.png"), full_page=False)
            print("result captured", flush=True)
        except PlaywrightTimeoutError:
            page.screenshot(path=str(out / "06_success.png"), full_page=False)
            print("result not captured within the timeout", flush=True)

        # Leaderboard final.
        print("capturing leaderboard…", flush=True)
        page.goto(base + "/?lang=en#leaderboards", wait_until="networkidle")
        page.wait_for_timeout(3000)
        page.screenshot(path=str(out / "07_leaderboard.png"), full_page=False)

        video = page.video
        context.close()
        browser.close()

    if video is not None:
        target = out / "playwright_demo.webm"
        try:
            video.save_as(str(target))
            print(f"video: {target}", flush=True)
        except Exception as exc:  # noqa: BLE001
            print(f"could not save video: {exc}", flush=True)
    shutil.rmtree(video_dir, ignore_errors=True)
    print(f"screenshots: {out}", flush=True)
    print(f"decision modal seen: {decision_seen}", flush=True)


if __name__ == "__main__":
    main()
