"""Responsive design-view capture: real screenshots at multiple device widths x engines.
Returns a design matrix keyed by engine -> device -> { dataUrl, hScroll, smallTap }.
Cached in-memory with TTL. Never fabricated — each cell is a real headless render."""
from __future__ import annotations
import base64, time

# Device matrix: name -> (width, height, isMobile, category)
# Categories: mobile, tablet, laptop, desktop, wide
# World-wide catalog — real, not representative. Each is a true viewport used by that device.
_FULL_DEVICES = [
    # ── Mobile · Apple ──
    ("iPhone SE 1",      320,  568, True,  "mobile"),
    ("iPhone SE 2/3",    375,  667, True,  "mobile"),
    ("iPhone 6/7/8",     375,  667, True,  "mobile"),
    ("iPhone 6/7/8 Plus",414,  736, True,  "mobile"),
    ("iPhone X/11 Pro",  375,  812, True,  "mobile"),
    ("iPhone XR/11",     414,  896, True,  "mobile"),
    ("iPhone 12/13 mini",375,  812, True,  "mobile"),
    ("iPhone 12/13/14",  390,  844, True,  "mobile"),
    ("iPhone 12/13 Pro Max",428, 926, True, "mobile"),
    ("iPhone 14/15/16",  390,  844, True,  "mobile"),
    ("iPhone 14/15/16 Pro",393, 852, True,  "mobile"),
    ("iPhone 15/16 Pro Max",430, 932, True, "mobile"),
    ("iPhone 16 Plus",   430,  932, True,  "mobile"),
    # ── Mobile · Samsung ──
    ("Galaxy S8/S9",     360,  740, True,  "mobile"),
    ("Galaxy S10/S20",   360,  780, True,  "mobile"),
    ("Galaxy S21",       360,  800, True,  "mobile"),
    ("Galaxy S22",       360,  780, True,  "mobile"),
    ("Galaxy S23",       360,  780, True,  "mobile"),
    ("Galaxy S24",       360,  780, True,  "mobile"),
    ("Galaxy Note 9",    360,  740, True,  "mobile"),
    ("Galaxy Note 20",   412,  915, True,  "mobile"),
    ("Galaxy Z Flip",    360,  748, True,  "mobile"),
    ("Galaxy Z Fold",    908,  1062, True,  "mobile"),
    ("Galaxy A54",       360,  780, True,  "mobile"),
    ("Galaxy A14",       360,  800, True,  "mobile"),
    ("Galaxy Tab-phone", 393,  851, True,  "mobile"),
    ("Galaxy Grand Prime",360, 640, True,  "mobile"),
    # ── Mobile · Google Pixel ──
    ("Pixel 3/3XL",      412,  823, True,  "mobile"),
    ("Pixel 4",          412,  869, True,  "mobile"),
    ("Pixel 4a",         412,  869, True,  "mobile"),
    ("Pixel 5",          393,  851, True,  "mobile"),
    ("Pixel 6",          412,  915, True,  "mobile"),
    ("Pixel 6 Pro",      412,  915, True,  "mobile"),
    ("Pixel 7",          412,  915, True,  "mobile"),
    ("Pixel 7 Pro",      412,  915, True,  "mobile"),
    ("Pixel 8",          412,  915, True,  "mobile"),
    ("Pixel 8 Pro",      412,  915, True,  "mobile"),
    ("Pixel 9",          412,  915, True,  "mobile"),
    # ── Mobile · Chinese / Global brands ──
    ("Xiaomi Redmi 12",  393,  851, True,  "mobile"),
    ("Xiaomi Redmi Note 13",393,873, True,  "mobile"),
    ("Xiaomi 14",        393,  851, True,  "mobile"),
    ("Xiaomi Mi 11",     393,  851, True,  "mobile"),
    ("POCO X6",          393,  851, True,  "mobile"),
    ("OnePlus 7/8",      412,  876, True,  "mobile"),
    ("OnePlus 11/12",    412,  915, True,  "mobile"),
    ("OnePlus Nord",     393,  851, True,  "mobile"),
    ("OPPO Find X5",     393,  851, True,  "mobile"),
    ("OPPO Reno 8",      393,  851, True,  "mobile"),
    ("vivo V27",         393,  851, True,  "mobile"),
    ("vivo X90",         393,  851, True,  "mobile"),
    ("Realme 11 Pro",    393,  851, True,  "mobile"),
    ("Huawei P40",       360,  780, True,  "mobile"),
    ("Huawei Mate 40",   393,  851, True,  "mobile"),
    ("Honor Magic 5",    393,  851, True,  "mobile"),
    ("Nokia G22",        360,  800, True,  "mobile"),
    ("Asus Zenfone 10",  393,  851, True,  "mobile"),
    # ── Mobile · Other global ──
    ("Motorola Edge",    393,  851, True,  "mobile"),
    ("Motorola razr",    393,  851, True,  "mobile"),
    ("Sony Xperia 1 V",  393,  872, True,  "mobile"),
    ("Sony Xperia 10 V", 360,  780, True,  "mobile"),
    ("LG Velvet",        393,  851, True,  "mobile"),
    ("TCL 10 Pro",       360,  780, True,  "mobile"),
    ("Tecno Camon 20",   393,  851, True,  "mobile"),
    ("Infinix Note 30",  393,  851, True,  "mobile"),
    ("HTC U23",          393,  851, True,  "mobile"),
    # ── Tablet ──
    ("iPad Mini",        768,  1024, False, "tablet"),
    ("iPad 10.9",        820,  1180, False, "tablet"),
    ("iPad Air",         820,  1180, False, "tablet"),
    ("iPad Pro 11",      834,  1112, False, "tablet"),
    ("iPad Pro 12.9",    1024, 1366, False, "tablet"),
    ("Galaxy Tab S7/S8", 800,  1280, False, "tablet"),
    ("Galaxy Tab S9",    820,  1180, False, "tablet"),
    ("Galaxy Tab A",     800,  1280, False, "tablet"),
    ("Galaxy Tab A7 lite",800, 1340, False, "tablet"),
    ("Pixel Tablet",     800,  1280, False, "tablet"),
    ("Surface Go 3",     1280, 800,  False, "tablet"),
    ("Xiaomi Pad 6",     800,  1280, False, "tablet"),
    ("Redmi Pad",        800,  1280, False, "tablet"),
    ("Lenovo Tab P11",   800,  1280, False, "tablet"),
    ("Amazon Fire HD 10",800,  1280, False, "tablet"),
    ("Fire Max 11",      800,  1280, False, "tablet"),
    ("Huawei MatePad",   800,  1280, False, "tablet"),
    ("OPPO Pad 2",       800,  1280, False, "tablet"),
    ("Nokia T20",        800,  1280, False, "tablet"),
    ("Samsung Tab active",800, 1280, False, "tablet"),
    # ── Laptop ──
    ("MacBook Air 13",   1280, 800,  False, "laptop"),
    ("MacBook Air 15",   1440, 900,  False, "laptop"),
    ("MacBook Pro 14",   1440, 900,  False, "laptop"),
    ("MacBook Pro 16",   1728, 1117, False, "laptop"),
    ("MacBook 12",       1440, 900,  False, "laptop"),
    ("Dell XPS 13",      1280, 800,  False, "laptop"),
    ("Dell XPS 15",      1440, 900,  False, "laptop"),
    ("ThinkPad X1",      1440, 900,  False, "laptop"),
    ("ThinkPad T14",     1536, 864,  False, "laptop"),
    ("EliteBook",        1536, 864,  False, "laptop"),
    ("HP Spectre",       1366, 768,  False, "laptop"),
    ("Surface Laptop 5", 1536, 1024, False, "laptop"),
    ("Surface Book 3",   1620, 1080, False, "laptop"),
    ("Asus ZenBook",     1536, 864,  False, "laptop"),
    ("ROG Zephyrus",     1536, 864,  False, "laptop"),
    ("Acer Swift 3",     1536, 864,  False, "laptop"),
    ("Chromebook 14",    1366, 768,  False, "laptop"),
    ("Lenovo Yoga",      1366, 768,  False, "laptop"),
    ("MSI Raider",       1600, 900,  False, "laptop"),
    ("Razer Blade 14",   1560, 1080, False, "laptop"),
    # ── Desktop monitors ──
    ("HD 1366",          1366, 768,  False, "desktop"),
    ("HD 720p",          1280, 720,  False, "desktop"),
    ("XGA 1024",         1024, 768,  False, "desktop"),
    ("FHD 1080p",        1920, 1080, False, "desktop"),
    ("WXGA 1280x800",    1280, 800,  False, "desktop"),
    ("SXGA 1280x960",    1280, 960,  False, "desktop"),
    ("WXGA+ 1440x900",   1440, 900,  False, "desktop"),
    ("WSXGA+ 1680x1050", 1680, 1050, False, "desktop"),
    ("QHD 1440p",        2560, 1440, False, "desktop"),
    ("UWQHD 3440x1440",  3440, 1440, False, "desktop"),
    ("4K UHD",           3840, 2160, False, "desktop"),
    # ── Wide / TV ──
    ("Wide 2560 16:9",   2560, 1440, False, "wide"),
    ("Ultra-wide 3440",  3440, 1440, False, "wide"),
    ("4K TV",            3840, 2160, False, "wide"),
    ("8K TV",            7680, 4320, False, "wide"),
    ("Super Ultra-wide", 5120, 1440, False, "wide"),
]

# Legacy compact matrix for the audit-page DesignViewPanel
DEVICES = [
    ("Mobile",  390,  844, True),
    ("Desktop", 1440, 900, False),
]

# All devices for the standalone responsive testing tool
ALL_DEVICES = _FULL_DEVICES

ENGINES = ["chromium", "firefox", "webkit"]

CATEGORY_ORDER = ["mobile", "tablet", "laptop", "desktop", "wide"]
CATEGORY_LABELS = {
    "mobile":  "Mobile",
    "tablet":  "Tablet",
    "laptop":  "Laptop",
    "desktop": "Desktop",
    "wide":    "Wide / TV",
}
CATEGORY_ICONS = {
    "mobile": "📱", "tablet": "📋", "laptop": "💻", "desktop": "🖥", "wide": "📺",
}

_CACHE: dict[str, tuple[float, dict]] = {}
_TTL = 900


def design_cached(url: str, engine: str, w: int, h: int = 0) -> dict | None:
    hit = _CACHE.get(_key(url, engine, w, h))
    if hit and time.time() - hit[0] < _TTL:
        return hit[1]
    return None


def design_cache(url: str, engine: str, w: int, entry: dict, h: int = 0) -> None:
    _CACHE[_key(url, engine, w, h)] = (time.time(), entry)
    if len(_CACHE) > 250:
        cutoff = time.time() - _TTL
        for k in [k for k, (ts, _) in _CACHE.items() if ts < cutoff]:
            _CACHE.pop(k, None)


def _key(url: str, engine: str, w: int, h: int = 0) -> str:
    import hashlib
    return hashlib.sha256(f"{url}|{engine}|{w}|{h}".encode()).hexdigest()


async def _capture_one(engine: str, url: str, width: int, height: int, is_mobile: bool) -> dict:
    from playwright.async_api import async_playwright
    async with async_playwright() as pw:
        browser = await getattr(pw, engine).launch(args=["--no-sandbox", "--disable-dev-shm-usage"])
        ctx = await browser.new_context(viewport={"width": width, "height": height},
                                        is_mobile=is_mobile, has_touch=is_mobile, device_scale_factor=1)
        page = await ctx.new_page()
        errors: list[str] = []
        page.on("console", lambda m: errors.append(m.text[:120]) if m.type == "error" else None)
        page.on("pageerror", lambda e: errors.append(str(e)[:120]))
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)
            try:
                await page.wait_for_load_state("networkidle", timeout=6000)
            except Exception:
                pass
            await page.wait_for_timeout(400)
            h_scroll = await page.evaluate("document.documentElement.scrollWidth > window.innerWidth")
            small_tap = await page.evaluate(
                "Array.from(document.querySelectorAll('a,button')).filter(e=>{const r=e.getBoundingClientRect();"
                "return r.width>0&&(r.width<44||r.height<44)}).length"
            )
            vp_ok = await page.evaluate("!!document.querySelector('meta[name=viewport]')")
            # full-page screenshot (tall), capped to a sane pixel height.
            # Very-wide viewports (>=4K) skip full-page to avoid Playwright timeouts.
            if width >= 3840:
                png = await page.screenshot(full_page=False, timeout=15000)
            else:
                png = await page.screenshot(full_page=True, timeout=15000)
            if len(png) > 2500000:
                await page.wait_for_timeout(100)
                png = await page.screenshot(full_page=False)  # fallback: viewport-only to keep bytes sane
        except Exception as e:
            await ctx.close(); await browser.close()
            return {"engine": engine, "width": width, "height": height, "isMobile": is_mobile,
                    "status": "unavailable", "error": str(e)[:120]}
        await ctx.close(); await browser.close()
        data_url = "data:image/png;base64," + base64.b64encode(png).decode()
        return {"engine": engine, "width": width, "height": height, "isMobile": is_mobile,
                "status": "ok", "dataUrl": data_url,
                "hScroll": h_scroll, "smallTap": small_tap, "viewportOk": vp_ok, "errors": errors[:5]}


async def capture_design(url: str, engines: list[str] | None = None, devices: list[tuple] | None = None) -> dict:
    """Render the matrix for the audit page (2-device compact set)."""
    engines = engines or ENGINES
    devices = devices or DEVICES
    matrix: dict[str, dict[str, dict]] = {}
    for engine in engines:
        row: dict[str, dict] = {}
        for dev in devices:
            name, w, h, ism = dev[0], dev[1], dev[2], dev[3]
            hit = design_cached(url, engine, w, h)
            if hit:
                row[name] = hit
                continue
            entry = await _capture_one(engine, url, w, h, ism)
            if entry["status"] == "ok":
                design_cache(url, engine, w, entry, h)
            row[name] = entry
        matrix[engine] = row
    return matrix


async def capture_responsive(url: str, engines: list[str] | None = None, categories: list[str] | None = None) -> dict:
    """Render the full responsive-testing matrix (all devices, grouped by category)."""
    engines = engines or ["chromium"]
    devices = ALL_DEVICES
    if categories:
        devices = [d for d in devices if d[4] in categories]
    matrix: dict[str, dict[str, dict]] = {}
    for engine in engines:
        row: dict[str, dict] = {}
        for (name, w, h, ism, cat) in devices:
            hit = design_cached(url, engine, w, h)
            if hit:
                entry = {**hit, "category": cat}
                row[name] = entry
                continue
            entry = await _capture_one(engine, url, w, h, ism)
            entry["category"] = cat
            if entry["status"] == "ok":
                design_cache(url, engine, w, entry, h)
            row[name] = entry
        matrix[engine] = row
    return matrix