"""Full audit orchestrator: runs A-T, persists nothing here (routers persist), never fabricates."""
from __future__ import annotations
from datetime import datetime, timezone
from urllib.parse import urlparse
from ..schemas import AuditResponse, CheckResult
from .http_utils import fetch_with_chain, domain_of
from .checks.onpage_content import onpage_checks, keyword_match_checks, content_stats_checks
from .checks.technical_security import technical_checks
from .checks.structured import structured_checks
from .checks.performance import performance_checks
from .checks.links_arch import link_checks, architecture_checks
from .checks.advanced import (techstack_detect, rendered_checks, aeo_sample, rank_checks, gsc_health, pwa_checks, local_checks)

def _norm(u: str) -> str:
    u = (u or "").strip()
    if not u.startswith(("http://","https://")): u = "https://" + u
    return u

async def run_full_audit(url: str, keyword: str | None = None, topic: str | None = None,
                         is_local: bool = False, deep: bool = True, include_rendered: bool = True) -> AuditResponse:
    url = _norm(url)
    started = datetime.now(timezone.utc).isoformat()
    resp, chain, elapsed, err = await fetch_with_chain(url)
    html = (resp.text or "") if resp else ""
    headers = dict(resp.headers) if resp else {}
    results: list[CheckResult] = []
    results += onpage_checks(url, html, headers)
    results += keyword_match_checks(url, html, keyword)
    results += content_stats_checks(html)
    results += await technical_checks(url, resp, chain, elapsed, err)
    results += structured_checks(html)
    results += await performance_checks(url)
    results += await link_checks(url, html)
    if deep and resp and resp.status_code == 200:
        results += await architecture_checks(url, html)
    results += techstack_detect(html)
    if include_rendered:
        results += await rendered_checks(url)
    results += await aeo_sample(url, topic or keyword)
    results += await rank_checks(url)
    results += await gsc_health()
    base = f"{urlparse(url).scheme}://{urlparse(url).netloc}"
    results += await pwa_checks(base, html)
    results += local_checks(html, is_local)
    # hreflang bidirectional validation (R) — needs ≥2 pages; do a light 2-hop check
    from ..schemas import CheckResult as CR
    import httpx
    try:
        from .http_utils import soup_of
        soup = soup_of(html)
        links = [l.get("href") for l in soup.find_all("link", attrs={"hreflang": True}) if l.get("href")]
        if links:
            ok_pairs = 0; checked = 0
            async with httpx.AsyncClient(timeout=12) as c:
                for href in links[:3]:
                    try:
                        r = await c.get(href)
                        s2 = soup_of(r.text or "")
                        back = [l.get("href","") for l in s2.find_all("link", attrs={"hreflang": True})]
                        checked += 1
                        if any(url.split("?")[0] in b or b.split("?")[0] in url for b in back): ok_pairs += 1
                    except Exception: checked += 1
            results.append(CR(key="r-bidir",label="hreflang bidirectional",category="R-intl",
                status="pass" if checked and ok_pairs==checked else "warning",severity="ok" if ok_pairs==checked else "warning",
                found=f"{ok_pairs}/{checked} return-links verified" if checked else "no return links verifiable",
                source="cross-page hreflang fetch",evidence=links[:3],
                why_matters="One-directional hreflang is ignored.",how_to_fix="" if ok_pairs==checked else "Add reciprocal hreflang on each alternate.",
                checked_at=datetime.now(timezone.utc).isoformat()))
    except Exception:
        pass
    finished = datetime.now(timezone.utc).isoformat()
    summary = {"total": len(results),
        "pass": sum(1 for r in results if r.status in ("pass", "info")),
        "warning": sum(1 for r in results if r.status=="warning"),
        "fail": sum(1 for r in results if r.status=="fail"),
        "unavailable": sum(1 for r in results if r.status=="unavailable"),
        "info": sum(1 for r in results if r.status=="info")}
    return AuditResponse(url=url, started_at=started, finished_at=finished, results=results, summary=summary)
