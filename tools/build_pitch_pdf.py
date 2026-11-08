#!/usr/bin/env python3
"""Exporta el pitch deck HTML (docs/pitch/index.html) a PDF con Chromium.

Uso:
  python tools/build_pitch_pdf.py

Salida:
  docs/pitch/AGENT_RUSH_pitch.pdf
  docs/pitch/preview/*.png   (una captura por slide, util para revisar)
"""

from __future__ import annotations

from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
DECK = ROOT / "docs" / "pitch" / "index.html"
PDF = ROOT / "docs" / "pitch" / "AGENT_RUSH_pitch.pdf"
PREVIEW = ROOT / "docs" / "pitch" / "preview"


def main() -> None:
    if not DECK.exists():
        raise SystemExit(f"Missing deck: {DECK}")
    PREVIEW.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1280, "height": 720})
        page.goto(DECK.as_uri(), wait_until="load")
        # Esperar a que las fuentes locales carguen antes de capturar.
        page.evaluate("() => document.fonts.ready")
        page.wait_for_timeout(1200)

        page.pdf(
            path=str(PDF),
            width="1280px",
            height="720px",
            print_background=True,
            prefer_css_page_size=True,
        )

        slides = page.query_selector_all(".slide")
        for i, slide in enumerate(slides, start=1):
            slide.screenshot(path=str(PREVIEW / f"slide_{i:02d}.png"))

        browser.close()

    print(f"pdf: {PDF} ({PDF.stat().st_size // 1024} KB)")
    print(f"preview: {PREVIEW} ({len(slides)} slides)")


if __name__ == "__main__":
    main()
