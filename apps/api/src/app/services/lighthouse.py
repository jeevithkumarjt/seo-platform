"""Full Lighthouse report builder. One PSI call returns every category —
Performance, Accessibility, Best Practices, SEO (+ experimental Agentic Browsing when PSI
includes it) — plus metric weights and per-resource opportunity tables so users can pinpoint
the exact CSS/JS/DOM causing the problem. Cached in memory (TTL). Never fabricated.
"""
from __future__ import annotations
import time, json, hashlib

CATEGORY_TITLES = {
    "performance": "Performance",
    "accessibility": "Accessibility",
    "best-practices": "Best Practices",
    "seo": "SEO",
    "pwa": "PWA",
    "agentic-browsing": "Agentic Browsing",
}

# Auditor refs under the performance category with weight -> these are the "metric weights"
# shown in the PSI UI (FCP +3, LCP +9, TBT +7, CLS +25, SI +5 style).
METRIC_REF_TITLES = {
    "first-contentful-paint": "First Contentful Paint",
    "speed-index": "Speed Index",
    "largest-contentful-paint": "Largest Contentful Paint",
    "total-blocking-time": "Total Blocking Time",
    "cumulative-layout-shift": "Cumulative Layout Shift",
    "interactive": "Time to Interactive",
}

_CACHE: dict[str, tuple[float, dict]] = {}
_TTL = 600


def _key(url: str, strat: str) -> str:
    return hashlib.sha256(f"lh|{url}|{strat}".encode()).hexdigest()


def lh_cached(url: str, strat: str) -> dict | None:
    hit = _CACHE.get(_key(url, strat))
    if hit and time.time() - hit[0] < _TTL:
        return hit[1]
    return None


def lh_cache(url: str, strat: str, report: dict) -> None:
    _CACHE[_key(url, strat)] = (time.time(), report)
    if len(_CACHE) > 30:
        cutoff = time.time() - _TTL
        for k, (ts, _) in list(_CACHE.items()):
            if ts < cutoff:
                _CACHE.pop(k, None)


def _cat_score(cat: dict | None) -> float | None:
    if not cat:
        return None
    s = cat.get("score")
    return round(s * 100) if s is not None else None


def _byte(b: int) -> str:
    if b >= 1024 * 1024:
        return f"{b/1024/1024:.1f} MiB"
    if b >= 1024:
        return f"{b/1024:.1f} KiB"
    return f"{b} B"


def _ms(ms: int | None) -> str:
    if ms is None:
        return "—"
    if ms >= 1000:
        return f"{ms/1000:.2f} s"
    return f"{ms:.0f} ms"


def _items(audit: dict, limit: int = 25) -> list[dict]:
    """Safely extract the item list from an audit's details.
    The PSI payload uses both list items and object-shaped items."""
    try:
        details = audit.get("details") or {}
        items = details.get("items") if isinstance(details, dict) else None
    except Exception:
        items = None
    if isinstance(items, dict):
        items = items.get("items") or [items]
    if not isinstance(items, list):
        return []
    return [i for i in items if isinstance(i, dict)][:limit]


def _summarize_item(item: dict) -> dict:
    d: dict = {}
    if item.get("url"):
        d["url"] = item["url"]
    if "transferSize" in item:
        d["transferSize"] = _byte(item.get("transferSize", 0))
    if "resourceSize" in item:
        d["resourceSize"] = _byte(item.get("resourceSize", 0))
    if "wastedBytes" in item:
        d["wastedBytes"] = _byte(item.get("wastedBytes", 0))
    if "wastedMs" in item:
        d["wastedMs"] = _ms(item.get("wastedMs"))
    if "duration" in item:
        d["duration"] = _ms(item.get("duration"))
    if item.get("node"):
        d["selector"] = item["node"].get("selector", "")
        d["snippet"] = (item["node"].get("snippet") or "")[:220]
    if "totalBytes" in item:
        d["totalBytes"] = _byte(item.get("totalBytes", 0))
    return d or ({"detail": str(item)[:160]} if item else {})


def _build_opportunity(aid: str, audit: dict) -> dict | None:
    """Opportunity/insight audit -> {id, title, description, savings, items:[{url,size,...}]}"""
    details = audit.get("details") or {}
    items = _items(audit)
    overall = details.get("overallSavingsMs") if isinstance(details, dict) else None
    title = audit.get("title", aid.replace("-", " "))
    desc = (audit.get("description", "") or "")[:400]
    savings = None
    if overall is not None:
        savings = f"Est. savings of {_ms(overall)}"
    elif isinstance(details, dict) and "wastedBytes" in details:
        savings = f"Est. savings of {_byte(details.get('wastedBytes', 0))}"
    return {
        "id": aid,
        "title": title,
        "description": desc,
        "savings": savings,
        "score": audit.get("score"),
        "displayValue": audit.get("displayValue"),
        "items": [_summarize_item(i) for i in items[:25]],
        "count": len(items),
    }


def _build_metric(audit: dict, weight: int) -> dict:
    gadget = (audit.get("details", {}) or {}).get("items") or []
    g = gadget[0] if gadget else {}
    acc = (g.get("items") or [{}])[0] if g else {}
    v = audit.get("numericValue")
    d = audit.get("displayValue")
    score = audit.get("score")
    return {
        "id": audit.get("id"),
        "title": audit.get("title", audit.get("id", "")),
        "metricTitle": METRIC_REF_TITLES.get(audit.get("id", ""), audit.get("title", "")),
        "weight": weight,
        "score": round(score * 100) if score is not None else None,
        "displayValue": d,
        "numericValue": v,
    }


async def build_lighthouse_report(url: str, strategy: str = "mobile") -> dict:
    """Fetch full PSI report and structure it like the PSI/DevTools UI."""
    import httpx
    from ..config import settings
    hit = lh_cached(url, strategy)
    if hit:
        return hit
    if not settings.PAGESPEED_API_KEY:
        return {"error": "PAGESPEED_API_KEY not configured", "url": url}
    async with httpx.AsyncClient(timeout=120) as c:
        r = await c.get("https://www.googleapis.com/pagespeedonline/v5/runPagespeed",
            params={"url": url, "key": settings.PAGESPEED_API_KEY, "strategy": strategy,
                    "category": ["performance", "accessibility", "best-practices", "seo"]})
        if r.status_code != 200:
            return {"error": f"PSI HTTP {r.status_code}: {r.text[:160]}", "url": url}
        data = r.json()
    lr = data.get("lighthouseResult", {}) or {}
    audits: dict = lr.get("audits", {}) or {}
    cats: dict = lr.get("categories", {}) or {}

    # category scores
    categories = []
    for cid, t in CATEGORY_TITLES.items():
        cat = cats.get(cid)
        if cat is None:
            continue
        score = _cat_score(cat)
        refs = cat.get("auditRefs", [])
        categories.append({
            "id": cid,
            "title": t,
            "score": score,
            "scoreNum": (score / 100) if score is not None else None,
            "count": len(refs),
        })

    # Performance: metric weights + weighted score (PSI "calculator")
    perf_refs = cats.get("performance", {}).get("auditRefs", []) or []
    total_weight = sum(r.get("weight", 0) for r in perf_refs)
    metrics = []
    for r in perf_refs:
        aid = r.get("id", "")
        audit = audits.get(aid, {})
        if aid in METRIC_REF_TITLES and audit:
            metrics.append(_build_metric(audit, r.get("weight", 0)))

    # Metric deltas relative to good thresholds (PSI shows 49 FCP +3 LCP +9...)
    THRESH = {"FCP": 1800, "LCP": 2500, "TBT": 200, "CLS": 0.1, "SI": 3400, "TTI": 3800}
    for m in metrics:
        delta = None
        if m["numericValue"] is not None and m["displayValue"]:
            key = " ".join(m["metricTitle"].split()).split()[-1]
            for k, thr in THRESH.items():
                if m["metricTitle"].endswith(k) or k in m["metricTitle"]:
                    if k == "CLS":
                        delta = round((m["numericValue"] / thr - 1) * 100) if thr else None
                    else:
                        delta = round((m["numericValue"] / thr - 1) * 100) if thr else None
                    break
        m["deltaPct"] = delta

    # Opportunities + diagnostics (performance, most-tabular)
    OPP_IDS = [
        "render-blocking-resources", "unused-css-rules", "unused-javascript",
        "uses-text-compression", "uses-optimized-images", "uses-responsive-images",
        "uses-long-cache-ttl", "server-response-time", "redirects", "efficient-animated-content",
        "modern-image-formats", "preload-lcp-image", "preload-fonts", "third-party-facades",
        "legacy-javascript", "duplicated-javascript", "no-unload-listeners", "layout-shift",
        "mainthread-work-breakdown", "total-byte-weight", "dom-size", "long-tasks",
        "bootup-time", "third-party-summary", "unsized-images", "lcp-lazy-loaded",
        "user-timings", "largest-contentful-paint-element", "prioritize-lcp-image",
        "font-display", "errors-in-console", "deprecations",
    ]
    opportunities = []
    diagnostics = []
    for aid in OPP_IDS:
        a = audits.get(aid)
        if not a or a.get("score") is None:
            continue
        o = _build_opportunity(aid, a)
        if not o["items"] and not o["savings"]:
            continue
        # numeric-waste items go to opportunities; pure "score != 1" to diagnostics
        if any(i.get("wastedBytes") or i.get("wastedMs") for i in o["items"]) or o["savings"]:
            opportunities.append(o)
        else:
            diagnostics.append(o)
    # mainthread-work, dom-size etc. always under diagnostics via readable values
    for aid in ["mainthread-work-breakdown", "total-byte-weight", "dom-size", "long-tasks", "bootup-time", "errors-in-console", "deprecations", "font-display", "layout-shift-pre-shift"]:
        a = audits.get(aid)
        if not a:
            continue
        if any(o["id"] == aid for o in opportunities) or any(o["id"] == aid for o in diagnostics):
            continue
        o = _build_opportunity(aid, a)
        diagnostics.append(o)

    # Passed audits (performance)
    passed_perf = []
    for aid, a in audits.items():
        if a.get("score") == 1 and a.get("title"):
            passed_perf.append((a.get("id", aid), a.get("title", aid)))
    passed_perf = sorted(set(passed_perf))[:40]

    # Accessibility failing audits grouped by description
    a11y_fails, a11y_passed = [], []
    for aid, a in audits.items():
        if a.get("score") is None:
            continue
        if "accessibility" not in (_group_of(cats, aid) or ""):
            pass
        entry = {"id": aid, "title": a.get("title", aid),
                 "description": (a.get("description") or "")[:300],
                 "displayValue": a.get("displayValue"),
                 "items": [_summarize_item(i) for i in _items(a)]}
        if a.get("score", 1) == 1:
            a11y_passed.append(entry)
        else:
            a11y_fails.append(entry)
    a11y_fails = sorted(a11y_fails, key=lambda x: 1 if x["items"] else 0, reverse=True)

    # Best practices / SEO failing audits
    def failing(cat_id: str) -> list[dict]:
        refs = cats.get(cat_id, {}).get("auditRefs", [])
        out = []
        for r in refs:
            a = audits.get(r.get("id", ""), {})
            if a and a.get("score") is not None and a.get("score", 1) < 1:
                out.append({"id": r.get("id"), "title": a.get("title", r.get("id")),
                            "description": (a.get("description") or "")[:300],
                            "displayValue": a.get("displayValue"),
                            "items": [_summarize_item(i) for i in _items(a)]})
        return out

    bp_fails = failing("best-practices")
    seo_fails = failing("seo")
    agentic = cats.get("agentic-browsing")

    # Screenshots
    final_ss = audits.get("final-screenshot", {}).get("details", {}).get("data")
    thumbs = audits.get("screenshot-thumbnails", {}).get("details", {}).get("items") or []

    # CrUX field data
    le = data.get("loadingExperience", {}) or {}
    field_metrics = {}
    for m, label in [("LARGEST_CONTENTFUL_PAINT_MS", "LCP"), ("FIRST_INPUT_DELAY_MS", "FID"),
                     ("CUMULATIVE_LAYOUT_SHIFT_SCORE", "CLS"), ("INTERACTION_TO_NEXT_PAINT", "INP"),
                     ("FIRST_CONTENTFUL_PAINT_MS", "FCP")]:
        e = le.get("metrics", {}).get(m)
        if e:
            field_metrics[label] = {"category": e.get("category", ""), "percentile": e.get("percentile")}

    report = {
        "url": url,
        "strategy": strategy,
        "lighthouseVersion": lr.get("lighthouseVersion"),
        "fetchedAt": lr.get("fetchedAt", data.get("lighthouseResult", {}).get("fetchTime")),
        "formFactor": lr.get("configSettings", {}).get("formFactor", strategy),
        "categories": categories,
        "metrics": sorted(metrics, key=lambda m: -(m.get("weight", 0))),
        "metricWeightsNote": [{"id": m["id"], "title": m["metricTitle"], "weight": m["weight"],
                               "deltaPct": m.get("deltaPct"), "displayValue": m["displayValue"],
                               "score": m["score"]} for m in metrics],
        "opportunities": opportunities,
        "diagnostics": diagnostics,
        "passedPerformance": passed_perf,
        "a11y": {"fails": a11y_fails, "passed": a11y_passed},
        "bestPractices": bp_fails,
        "seo": seo_fails,
        "agentic": _cat_score(agentic),
        "finalScreenshot": final_ss,
        "thumbnails": [t.get("data") for t in thumbs if t.get("data")][:: max(1, len(thumbs) // 6)],
        "fieldMetrics": field_metrics,
        "loadingExperience": le.get("metrics", {}),
        "summary": data.get("analysisUTCTimestamp"),
    }
    lh_cache(url, strategy, report)
    return report


def _group_of(cats: dict, aid: str) -> str | None:
    for cat in cats.values():
        for r in cat.get("auditRefs", []):
            if r.get("id") == aid:
                return r.get("group", r.get("g", ""))
    return None