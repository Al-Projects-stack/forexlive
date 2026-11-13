"""Render the promo page frame-by-frame via its #capture seek hook.

usage: python capture_frames.py <promo.html> <out_dir> <fps>
"""
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

src, out_dir, fps = Path(sys.argv[1]).resolve(), Path(sys.argv[2]), float(sys.argv[3])
out_dir.mkdir(parents=True, exist_ok=True)

with sync_playwright() as p:
    browser = p.chromium.launch(channel="chrome")
    # body side padding is 16px each, so a 992px viewport gives a 960x540 frame
    page = browser.new_page(viewport={"width": 992, "height": 640}, device_scale_factor=1)
    page.goto(src.as_uri() + "#capture")
    page.wait_for_function("typeof window.__seek === 'function'")
    page.evaluate("document.fonts.ready")
    page.wait_for_timeout(1200)  # let the ResizeObserver chart rebuild settle
    total = page.evaluate("window.__TOTAL")
    n = int(total * fps)
    frame = page.locator("#frame")
    box = frame.bounding_box()
    print(f"frame {box['width']:.0f}x{box['height']:.0f}, {n} frames over {total:.1f}s", flush=True)
    for i in range(n):
        page.evaluate(f"window.__seek({i / fps})")
        frame.screenshot(path=str(out_dir / f"f{i:04d}.png"), animations="allow", caret="initial")
        if i % 60 == 0:
            print(f"  {i}/{n}", flush=True)
    browser.close()
print("done", flush=True)
