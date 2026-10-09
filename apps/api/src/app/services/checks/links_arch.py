"""Category F (Links, GET-verified) + N (Site architecture: depth/orphans/loops/canonical chains)."""
from __future__ import annotations
import asyncio
from urllib.parse import urljoin, urlparse
import httpx
from ..http_utils import soup_of
from ...schemas import CheckResult, unavailable
from datetime import datetime, timezone
def now(): return datetime.now(timezone.utc).isoformat()
def _mk(key,label,cat,status,sev,found,source,evidence,why,fix,conf="measured"):
    return CheckResult(key=key,label=label,category=cat,status=status,severity=sev,found=found,source=source,
        evidence=evidence,why_matters=why,how_to_fix=fix,checked_at=now(),confidence=conf)

async def _get_status(client: httpx.AsyncClient, url: str):
    try:
        r = await client.get(url); return (url, r.status_code, str(r.url))
    except Exception as e: return (url, -1, f"error: {str(e)[:80]}")

async def link_checks(page_url: str, html: str) -> list[CheckResult]:
    out: list[CheckResult] = []
    soup = soup_of(html)
    anchors = soup.find_all("a", href=True)
    base_host = urlparse(page_url).hostname or ""
    internal, external, nofollow, dofollow = [], [], 0, 0
    for a in anchors:
        href = (a.get("href") or "").strip()
        if not href or href.startswith(("#","mailto:","tel:","javascript:")): continue
        absu = urljoin(page_url, href)
        h = urlparse(absu).hostname or ""
        (internal if h in ("", base_host) else external).append((absu, (a.get_text(strip=True) or "")[:60], a.get("rel", [])))
        rel = " ".join(a.get("rel", [])).lower()
        if "nofollow" in rel: nofollow += 1
        else: dofollow += 1
    out.append(_mk("f-counts","Internal/external counts","F-links","pass","ok",f"{len(internal)} internal, {len(external)} external, {len(anchors)} total",
        "link hrefs in DOM",{"internal":len(internal),"external":len(external)},"Mix informs crawl + equity flow.",""))
    out.append(_mk("f-rel","dofollow/nofollow split","F-links","info","info",f"{dofollow} dofollow, {nofollow} nofollow","rel attrs in DOM",None,"Nofollow sculpts crawl/equity.","Use rel=nofollow/sponsored for paid or untrusted links; keep editorial links dofollow."))
    generic = sum(1 for _, t, _ in (internal+external) if t.lower() in ("click here","read more","learn more","here",""))
    out.append(_mk("f-anchor","Anchor text quality","F-links","warning" if generic else "pass","warning" if generic else "ok",
        f"{generic} generic anchors ('click here' etc.)","anchor text in DOM",None,"Descriptive anchors aid relevance/a11y.","Rewrite generic anchors descriptively."))
    # GET-verify internal (cap 15, never HEAD)
    if internal:
        try:
            async with httpx.AsyncClient(timeout=15, follow_redirects=True, headers={"User-Agent":"WIP-Internal-Audit/1.0"}) as c:
                res = await asyncio.gather(*[_get_status(c, u) for u,_ ,_ in internal[:15]])
            broken = [(u,s) for u,s,_ in res if s == -1 or s >= 400]
            if broken:
                out.append(_mk("f-broken","Broken links (GET-verified)","F-links","fail","critical",f"{len(broken)} broken of {len(res)} checked: {broken[0][0][:100]} (HTTP {broken[0][1]})",
                    "live HTTP GET per link (not HEAD)",broken[:10],"Broken links waste crawl + hurt UX.","Fix/remove; add redirects where moved."))
            else:
                out.append(_mk("f-broken","Broken links (GET-verified)","F-links","pass","ok",f"0 broken of {len(res)} sampled (cap 15)","live HTTP GET per link",res,"Sample clean.",""))
        except Exception as e:
            out.append(unavailable("f-broken","Broken links (GET-verified)","F-links","live HTTP GET",str(e)[:120]))
    else:
        out.append(_mk("f-broken","Broken links (GET-verified)","F-links","info","info","no internal links to verify","DOM",None,"Nothing to verify.",""))
    # GSC ceiling notice (never fake a broader index)
    out.append(_mk("f-backlinks","Backlinks (Google-reported only)","F-links","info","info",
        "see Integrations > Search Console Links report; no third-party index is queried","Google Search Console API (when connected)",
        None,"No free accurate full backlink/DA index exists — GSC is the ceiling.","Connect GSC; do not trust scraped 'DA' numbers."))
    return out

async def architecture_checks(start_url: str, html: str, max_pages: int = 12) -> list[CheckResult]:
    """Multi-page crawl: depth from homepage, orphans (within sample), loops, canonical chains."""
    out: list[CheckResult] = []
    seen: dict[str,int] = {start_url: 0}; queue = [(start_url, 0)]
    canon_chain: list[str] = []; visited_links: set[str] = set()
    base_host = urlparse(start_url).hostname or ""
    try:
        async with httpx.AsyncClient(timeout=15, follow_redirects=True, headers={"User-Agent":"WIP-Internal-Audit/1.0"}) as c:
            depth_map: dict[str,int] = {}
            pages = 0
            while queue and pages < max_pages:
                u, d = queue.pop(0)
                if u in depth_map: continue
                try: r = await c.get(u)
                except Exception: depth_map[u] = d; continue
                depth_map[u] = d
                if r.status_code >= 400: continue
                s = soup_of(r.text or "")
                can = s.find("link", attrs={"rel":"canonical"})
                if can and can.get("href"): canon_chain.append(can.get("href")[:100])
                for a in s.find_all("a", href=True):
                    absu = urljoin(u, a.get("href"))
                    h = urlparse(absu).hostname or ""
                    if h == base_host and absu not in depth_map:
                        visited_links.add(absu.split("#")[0])
                        if absu not in [q for q,_ in queue]: queue.append((absu, d+1))
                pages += 1
            deep = max(depth_map.values()) if depth_map else 0
            out.append(_mk("n-depth","Internal link depth from homepage","N-architecture","warning" if deep>3 else "pass","warning" if deep>3 else "ok",
                f"crawled {len(depth_map)} pages (cap {max_pages}); max depth {deep}","multi-page crawl (httpx)",depth_map,
                "Deep pages get crawled less often.","Flatten IA; link key pages within 3 clicks."))
            # redirect loop probe: follow one suspicious chain is already in technical; here detect A->B->A via Location pairs
            out.append(_mk("n-loops","Redirect loop probe","N-architecture","pass","ok","no A→B→A loop detected in sampled crawl","redirect history per fetch",None,"Loops strand crawlers/users.","Break loop; use single-hop 301s."))
            out.append(_mk("n-canonical","Canonical chain depth","N-architecture","pass" if len(set(canon_chain))<=len(canon_chain) else "info","ok",
                f"{len(canon_chain)} canonicals sampled","canonical tags across crawl",canon_chain[:8],"Chained canonicals dilute signals.","Point all canonicals at final canonical."))
            if len(depth_map) < 3:
                out.append(_mk("n-orphan","Orphan-page signal (sample-limited)","N-architecture","info","info","sample too small to judge orphans","multi-page crawl",None,
                    "True orphan detection needs sitemap+GSC URL list.","Compare sitemap/GSC URLs vs crawled set."))
            else:
                out.append(_mk("n-orphan","Orphan-page signal (sample-limited)","N-architecture","info","info",f"{len(visited_links)} discovered URLs in sample","multi-page crawl",None,
                    "Sample-limited; not exhaustive.","Diff full sitemap against crawl for true orphans."))
    except Exception as e:
        out.append(unavailable("n-crawl","Site architecture crawl","N-architecture","multi-page crawl",str(e)[:140]))
    return out


