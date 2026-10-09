from fastapi import APIRouter, Query, HTTPException
from fastapi.responses import Response
from ..schemas_api import AuditRequest
from ..services.audit_runner import run_full_audit
from ..services.screenshot import capture_png, cached_png, cache_png, png_to_dataurl
from ..services.design_view import capture_design, capture_responsive, DEVICES, ALL_DEVICES, ENGINES, CATEGORY_ORDER, CATEGORY_LABELS, CATEGORY_ICONS, design_cached
from .. import store
from ..alerting import evaluate
from ..notify import deliver

router = APIRouter()

@router.get("/devices")
async def devices():
    """World-wide device catalog (single source of truth for the Responsive Testing Tool)."""
    by_cat: dict[str, list[dict]] = {}
    for (name, w, h, ism, cat) in ALL_DEVICES:
        by_cat.setdefault(cat, []).append({
            "name": name, "width": w, "height": h, "isMobile": ism, "category": cat,
            "icon": CATEGORY_ICONS.get(cat, "📱"),
        })
    cats = []
    for c in CATEGORY_ORDER:
        if c in by_cat:
            cats.append({"id": c, "label": CATEGORY_LABELS[c], "icon": CATEGORY_ICONS[c], "devices": by_cat[c]})
    return {"categories": cats, "total": len(ALL_DEVICES)}

@router.get("/screenshot")
async def screenshot(url: str = Query(...), data_url: bool = False):
    hit = cached_png(url)
    if hit is None:
        try:
            hit = await capture_png(url)
            cache_png(url, hit)
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"screenshot failed: {str(e)[:160]}")
    if data_url:
        return {"url": url, "dataUrl": png_to_dataurl(hit)}
    return Response(content=hit, media_type="image/png")

@router.get("/design")
async def design(url: str = Query(...), engine: str = Query("chromium"), device: str = Query(None)):
    """One screenshot cell of the responsive matrix (cached). Returns full matrix shape when device is omitted."""
    if engine not in ENGINES:
        raise HTTPException(status_code=400, detail=f"engine must be one of {ENGINES}")
    named = {n: (w, h, m) for (n, w, h, m) in DEVICES}
    if device:
        if device not in named:
            raise HTTPException(status_code=400, detail=f"device must be one of {list(named)}")
        w, h, m = named[device]
        hit = design_cached(url, engine, w)
        if hit is None:
            matrix = await capture_design(url, engines=[engine], devices=[(device, w, h, m)])
            hit = matrix[engine][device]
        if hit.get("status") != "ok":
            raise HTTPException(status_code=502, detail=hit.get("error", "capture failed"))
        return {"engine": engine, "device": device, **hit}
    matrix = await capture_design(url, engines=[engine])
    return {"url": url, "engine": engine, "devices": matrix[engine]}

@router.get("/responsive")
async def responsive_test(url: str = Query(...), engine: str = Query("chromium"), category: str = Query(None)):
    """Full responsive test: renders all device sizes grouped by category (mobile/tablet/laptop/desktop/wide)."""
    if engine not in ENGINES:
        raise HTTPException(status_code=400, detail=f"engine must be one of {ENGINES}")
    cats = [category] if category and category in CATEGORY_ORDER else None
    matrix = await capture_responsive(url, engines=[engine], categories=cats)
    devices = matrix[engine]
    grouped = {}
    for cat in CATEGORY_ORDER:
        items = {k: v for k, v in devices.items() if v.get("category") == cat}
        if items:
            grouped[cat] = {
                "label": CATEGORY_LABELS[cat],
                "icon": CATEGORY_ICONS[cat],
                "devices": items,
            }
    return {"url": url, "engine": engine, "categories": grouped,
            "allCategories": [{"id": c, "label": CATEGORY_LABELS[c], "icon": CATEGORY_ICONS[c]} for c in CATEGORY_ORDER]}

@router.get("/frameable")
async def frameable(url: str = Query(...)):
    """Check whether a site allows iframe embedding (X-Frame-Options / CSP frame-ancestors).
    Live-preview mode depends on this; if blocked we fall back to screenshots."""
    import httpx
    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=12,
                                     headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"} ) as c:
            r = await c.get(url)
        xfo = (r.headers.get("x-frame-options") or "").lower()
        csp = (r.headers.get("content-security-policy") or "")
        blocked_reason = ""
        if xfo in ("deny", "sameorigin"):
            blocked_reason = f"X-Frame-Options: {r.headers.get('x-frame-options')}"
        elif "frame-ancestors" in csp:
            fa = csp.split("frame-ancestors", 1)[1].split(";")[0].strip()
            if fa and "*" not in fa and "localhost:3001" not in fa:
                blocked_reason = f"CSP frame-ancestors: {fa}"
        return {"url": url, "frameable": not blocked_reason, "reason": blocked_reason or "ok"}
    except Exception as e:
        return {"url": url, "frameable": True, "reason": "probe-failed"}

@router.get("/lighthouse")
async def lighthouse(url: str = Query(...), strategy: str = Query("mobile")):
    """Full Lighthouse-style report: all category scores, metric weights, per-resource
    opportunities (specific CSS/JS URLs → size + savings), diagnostics, screenshots."""
    from ..services.lighthouse import build_lighthouse_report
    rep = await build_lighthouse_report(url, strategy)
    if rep.get("error"):
        raise HTTPException(status_code=502, detail=rep["error"])
    return rep

@router.get("/proxy")
async def proxy(url: str = Query(...)):
    """Server-side HTML proxy for Live Preview. Lets click-through work even on
    X-Frame-Options/CSP-blocked sites by replaying the page from our own origin."""
    from ..services.proxy import build_proxied
    try:
        body: bytes
        ctype: str
        body, ctype = await build_proxied(url)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"proxy failed: {str(e)[:160]}")
    return Response(content=body, media_type=ctype)

@router.post("/run")
async def run_audit(body: AuditRequest):
    audit = await run_full_audit(body.url, body.keyword, body.topic, body.is_local_business, include_rendered=body.include_rendered)
    # ensure site row
    site = next((s for s in store.SITES.values() if s["url"]==audit.url), None) or store.add_site(audit.url, audit.url, body.is_local_business)
    run = store.add_run(site["id"], "full", audit.model_dump())
    alerts = evaluate(site["id"], audit)
    for a in alerts:
        await deliver(f"[{a['severity']}] {a['kind']} @ {site['url']}: {a['message']}")
        a["delivered"] = True
    return {**audit.model_dump(), "site_id": site["id"], "run_id": run["id"], "alerts_triggered": alerts}

@router.get("/history")
async def history(site_id: int, limit: int = 20):
    runs = [r for r in store.RUNS if r["site_id"]==site_id][-limit:]
    # trend: issue count over time with explicit gaps (no interpolation — frontend breaks line on unavailable runs)
    trend = [{"at": r["created_at"], "fail": r["result"]["summary"].get("fail",0), "warning": r["result"]["summary"].get("warning",0),
              "unavailable": r["result"]["summary"].get("unavailable",0), "gap": r["result"]["summary"].get("unavailable",0)>0} for r in runs]
    return {"runs": runs, "trend": trend}
