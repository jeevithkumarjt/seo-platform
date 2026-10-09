"""Site screenshot capture via Playwright (chromium only — fastest, most compatible).
Returns PNG bytes; wrapped by the audit router with a small TTL cache. Never invented."""
from __future__ import annotations
import asyncio, hashlib, time, base64
from typing import Optional

_IMG_CACHE: dict[str, tuple[float, bytes]] = {}
_CACHE_TTL = 300  # seconds

def _key(url: str) -> str:
    return hashlib.sha256(url.encode()).hexdigest()

def cached_png(url: str) -> Optional[bytes]:
    k = _key(url)
    hit = _IMG_CACHE.get(k)
    if hit and time.time() - hit[0] < _CACHE_TTL:
        return hit[1]
    return None

def cache_png(url: str, data: bytes) -> None:
    _IMG_CACHE[_key(url)] = (time.time(), data)
    if len(_IMG_CACHE) > 64:
        cutoff = time.time() - _CACHE_TTL
        for k in [k for k, (ts, _) in _IMG_CACHE.items() if ts < cutoff]:
            _IMG_CACHE.pop(k, None)

async def capture_png(url: str, width: int = 1440, height: int = 960) -> bytes:
    """Full-viewport-if-cheap, else loading-state screenshot. Chromium only."""
    from playwright.async_api import async_playwright
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(args=["--no-sandbox", "--disable-dev-shm-usage"])
        ctx = await browser.new_context(viewport={"width": width, "height": height}, device_scale_factor=1)
        page = await ctx.new_page()
        await page.route("**/*", lambda route: route.continue_())
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=25000)
            # wait up to 6s for networkidle, tolerate partial
            try:
                await page.wait_for_load_state("networkidle", timeout=6000)
            except Exception:
                pass
            # lazy images: scroll to trigger loads bottom-up, then back to top
            for _ in range(3):
                await page.mouse.wheel(0, 800)
                await page.wait_for_timeout(150)
            await page.mouse.wheel(0, -8000)
            await page.wait_for_timeout(120)
        except Exception:
            pass  # render whatever loaded
        png = await page.screenshot()
        await ctx.close()
        await browser.close()
        return png

def png_to_dataurl(data: bytes) -> str:
    return "data:image/png;base64," + base64.b64encode(data).decode()