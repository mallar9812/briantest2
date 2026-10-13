#!/usr/bin/env python3
"""Render a brand-styled HTML report to PDF with headless Chromium.

    python3 html_to_pdf.py report.html report.pdf [--wait-ms 1500]

Uses Playwright's page.pdf() with preferCSSPageSize, so the stylesheet's
`@page { size: A4; margin: 0 }` is honoured exactly and full-bleed cover pages
reach the paper edge. Chromium's bare `--print-to-pdf` CLI applies its own
default margins and then shrink-to-fits, which silently scales the whole
document down — do not use it, and never substitute wkhtmltopdf (it drops CSS
grid, @page and web fonts).

Charts drawn in-page need a moment to paint. Either raise --wait-ms, or set
`window.__reportReady = true` when drawing finishes and this waits for it.
"""

import argparse
import glob
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

CANDIDATES = [
    "/opt/pw-browsers/chromium/chrome-linux/chrome",
    "/opt/pw-browsers/chromium-*/chrome-linux/chrome",
    "/opt/pw-browsers/chromium_headless_shell-*/chrome-linux/headless_shell",
]


def find_chromium():
    for name in ("chromium", "chromium-browser", "google-chrome", "google-chrome-stable"):
        found = shutil.which(name)
        if found:
            return found
    for pattern in CANDIDATES:
        for hit in sorted(glob.glob(pattern)):
            if os.access(hit, os.X_OK):
                return hit
    return None


def render_playwright(src: Path, out: Path, wait_ms: int) -> bool:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return False

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(args=["--no-sandbox", "--font-render-hinting=none"])
            page = browser.new_page()
            page.goto(src.as_uri(), wait_until="load")
            try:
                page.wait_for_function("window.__reportReady === true", timeout=wait_ms)
            except Exception:
                page.wait_for_timeout(wait_ms)
            page.evaluate("document.fonts && document.fonts.ready")
            page.pdf(
                path=str(out),
                prefer_css_page_size=True,   # obey @page size + margin
                print_background=True,       # brand grounds must print
                margin={"top": "0", "right": "0", "bottom": "0", "left": "0"},
                scale=1.0,
            )
            browser.close()
        return out.exists() and out.stat().st_size > 0
    except Exception as exc:  # noqa: BLE001
        sys.stderr.write(f"Playwright render failed ({exc}); falling back to Chromium CLI.\n")
        return False


def render_cli(src: Path, out: Path, wait_ms: int) -> bool:
    """Fallback only. Applies Chromium's own margins — expect slight downscaling."""
    chrome = find_chromium()
    if not chrome:
        return False
    profile = tempfile.mkdtemp(prefix="ps-report-")
    cmd = [
        chrome, "--headless=new", "--disable-gpu", "--no-sandbox",
        "--disable-dev-shm-usage", "--font-render-hinting=none",
        f"--user-data-dir={profile}", f"--virtual-time-budget={wait_ms}",
        "--no-pdf-header-footer", f"--print-to-pdf={out}", src.as_uri(),
    ]
    subprocess.run(cmd, capture_output=True, text=True, timeout=180)
    if not out.exists() or out.stat().st_size == 0:
        cmd = [c for c in cmd if c != "--no-pdf-header-footer"]
        cmd[1] = "--headless"
        subprocess.run(cmd, capture_output=True, text=True, timeout=180)
    shutil.rmtree(profile, ignore_errors=True)
    return out.exists() and out.stat().st_size > 0


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("html")
    ap.add_argument("pdf")
    ap.add_argument("--wait-ms", type=int, default=1500)
    args = ap.parse_args()

    src = Path(args.html).resolve()
    if not src.exists():
        sys.exit(f"Not found: {src}")
    out = Path(args.pdf).resolve()
    out.parent.mkdir(parents=True, exist_ok=True)

    if not render_playwright(src, out, args.wait_ms) and not render_cli(src, out, args.wait_ms):
        sys.exit("PDF was not produced. Check that Chromium/Playwright is available.")

    print(f"Wrote {out} ({out.stat().st_size / 1024:.0f} KB)")


if __name__ == "__main__":
    main()
