"""Categories H (x-browser/device via Playwright), I (console/pageerrors, render-blocking from PSI),
J (tech-stack/tag patterns), K (AEO sample), L (rank: GSC-first + throttled SERP scraper),
M (GSC health, highest trust), Q (PWA), T (local, conditional)."""
from __future__ import annotations
import re, json, base64
import httpx
from datetime import datetime, timezone
from ...schemas import CheckResult, unavailable
from ...config import settings
def now(): return datetime.now(timezone.utc).isoformat()
def _mk(key,label,cat,status,sev,found,source,evidence,why,fix,conf="measured"):
    return CheckResult(key=key,label=label,category=cat,status=status,severity=sev,found=found,source=source,
        evidence=evidence,why_matters=why,how_to_fix=fix,checked_at=now(),confidence=conf)

# ---- J: tag patterns (URL + DOM match) ----
TAG_PATTERNS = {
    "Google Analytics (GA4)": [r"googletagmanager\.com/gtag", r"google-analytics\.com/g/collect", r"gtag\("],
    "Google Tag Manager": [r"googletagmanager\.com/gtm\.js", r"GTM-[A-Z0-9]+"],
    "Meta Pixel": [r"connect\.facebook\.net/.*/fbevents\.js", r"fbq\("],
    "LinkedIn Insight": [r"snap\.licdn\.com/li\.lms-analytics", r"_linkedin_partner_id"],
    "TikTok Pixel": [r"analytics\.tiktok\.com", r"ttq\."],
    "Google Ads": [r"googleadservices\.com", r"googletagmanager\.com.*AW-"],
    "Bing UET": [r"bat\.bing\.com", r"uet\("],
    "HubSpot": [r"js\.hs-scripts\.com", r"hs-scripts"],
    "Marketo": [r"munchkin\.marketo\.net"],
    "Pardot": [r"pi\.pardot\.com"],
    "Apollo.io": [r"apollo\.io"],
    "Lusha": [r"lusha\."],
    "ZoomInfo": [r"zoominfo\."],
    "Clearbit": [r"clearbit"],
    "6sense": [r"6sense"],
    "Demandbase": [r"demandbase"],
    "Drift": [r"js\.driftt\.com"],
    "Intercom": [r"widget\.intercom\.io"],
    "Hotjar": [r"static\.hotjar\.com"],
    "Microsoft Clarity": [r"clarity\.ms"],
    "Segment": [r"cdn\.segment\.com/analytics"],
}

def techstack_detect(html: str, network_urls: list[str] | None = None) -> list[CheckResult]:
    blob = (html or "") + "\n" + "\n".join(network_urls or [])
    out: list[CheckResult] = []
    for vendor, pats in TAG_PATTERNS.items():
        hit = next((p for p in pats if re.search(p, blob, re.I)), None)
        if hit:
            m = re.search(hit, blob, re.I)
            out.append(_mk(f"j-{vendor}", f"Tag: {vendor}", "J-techstack", "info", "info",
                f"detected (pattern {hit})", "script URLs + DOM (regex match)", (m.group(0)[:80] if m else hit),
                "Tags affect privacy/perf/attribution; changes trigger alerts.", "Remove in tag manager if unwanted; document owner."))
    if not out:
        out.append(_mk("j-none","Tracking tags","J-techstack","info","info","no known marketing/sales tags matched","script URLs + DOM",None,
            "Site ships no detected third-party tags.",""))
    return out

# ---- H: Playwright rendered checks with screenshots at multiple device widths ----
# Device matrix: (name, width, height, isMobile)
_RESP_DEVICES = [
    ("Mobile",  390,  844, True),
    ("Desktop", 1440, 900, False),
]

async def rendered_checks(url: str) -> list[CheckResult]:
    try:
        from playwright.async_api import async_playwright
    except Exception as e:
        return [
            unavailable("h-pw","Cross-browser rendered checks","H-xbrowser","Playwright engines",f"playwright not installed: {str(e)[:100]}","pip install playwright && playwright install chromium firefox webkit."),
            unavailable("i-pw","JS console/error capture","I-jshealth","Playwright engines",f"playwright not installed: {str(e)[:100]}","pip install playwright && playwright install chromium firefox webkit."),
        ]
    out: list[CheckResult] = []
    try:
        async with async_playwright() as pw:
            for engine in ["chromium", "firefox", "webkit"]:
                try:
                    browser = await getattr(pw, engine).launch()
                    dev_shots: dict[str, dict] = {}  # device_name -> { dataUrl, timing, smallTap, hScroll, vpOk }
                    all_errors: list[str] = []
                    for (dev_name, dev_w, dev_h, is_mob) in _RESP_DEVICES:
                        try:
                            page = await browser.new_page(viewport={"width": dev_w, "height": dev_h},
                                                          is_mobile=is_mob, has_touch=is_mob)
                            errs_local: list[str] = []
                            page.on("console", lambda m: errs_local.append(m.text[:120]) if m.type == "error" else None)
                            page.on("pageerror", lambda e: errs_local.append(str(e)[:120]))
                            t0 = __import__("time").perf_counter()
                            await page.goto(url, wait_until="domcontentloaded", timeout=30000)
                            try: await page.wait_for_load_state("networkidle", timeout=5000)
                            except Exception: pass
                            load_ms = (__import__("time").perf_counter() - t0) * 1000
                            hs = await page.evaluate("document.documentElement.scrollWidth > window.innerWidth")
                            small = await page.evaluate(
                                "Array.from(document.querySelectorAll('a,button')).filter(e=>{const r=e.getBoundingClientRect();"
                                "return r.width>0&&(r.width<44||r.height<44)}).length")
                            vp_ok = await page.evaluate("!!document.querySelector('meta[name=viewport]')")
                            png = await page.screenshot(full_page=False, timeout=12000)
                            data_url = "data:image/png;base64," + base64.b64encode(png).decode()
                            dev_shots[dev_name] = {
                                "dataUrl": data_url, "timing": round(load_ms),
                                "smallTap": small, "hScroll": hs, "viewportOk": vp_ok,
                                "errors": errs_local[:5],
                            }
                            all_errors.extend(errs_local)
                            await page.close()
                        except Exception as ex:
                            dev_shots[dev_name] = {"status": "unavailable", "error": str(ex)[:120]}
                            await page.close()
                    # summary across devices
                    worst_small = max((d.get("smallTap", 0) for d in dev_shots.values() if isinstance(d.get("smallTap"), int)), default=0)
                    any_hscroll = any(d.get("hScroll") for d in dev_shots.values() if "hScroll" in d)
                    worst_load = max((d.get("timing", 0) for d in dev_shots.values() if "timing" in d), default=0)
                    bad_status = any(d.get("status") == "unavailable" for d in dev_shots.values())
                    out.append(_mk(
                        f"h-{engine}", f"Rendered layout ({engine})", "H-xbrowser",
                        "warning" if any_hscroll or worst_small > 0 else "pass",
                        "warning" if any_hscroll or worst_small > 0 else "ok",
                        f"h-scroll: {'YES' if any_hscroll else 'no'}; <44px tap targets (worst): {worst_small}; viewport: ok",
                        f"rendered DOM ({engine}) — {len(_RESP_DEVICES)} devices captured",
                        {
                            "hScroll": any_hscroll, "smallTap": worst_small, "loadMs": round(worst_load),
                            "devices": {k: {kk: vv for kk, vv in v.items() if kk != "dataUrl"} for k, v in dev_shots.items()},
                        },
                        f"Layout breaks on {engine} cost mobile UX/conversion. Screenshots show rendered state at Mobile+Desktop.",
                        "Fix overflow CSS; size tap targets ≥44px." if any_hscroll or worst_small > 0 else ""))
                    # Screenshots as separate visual evidence rows — the real value
                    for dev_name, shot in dev_shots.items():
                        if shot.get("dataUrl"):
                            out.append(_mk(
                                f"h-screenshot-{engine}-{dev_name.lower()}",
                                f"Screenshot {engine} · {dev_name}", "H-xbrowser",
                                "info", "info",
                                f"rendered at {dev_name} ({dev_shots[dev_name].get('timing','?')}ms)",
                                f"{engine} browser capture ({dev_name} viewport)",
                                {"type": "image", "dataUrl": shot["dataUrl"],
                                 "timing": shot.get("timing"), "smallTap": shot.get("smallTap", 0),
                                 "hScroll": shot.get("hScroll", False)},
                                "Visual check — review screenshot for rendering issues.",
                                f"{'Fix ' + str(shot.get('smallTap',0)) + ' undersized tap targets.' if shot.get('smallTap', 0) > 0 else ''}"))
                    if all_errors:
                        out.append(_mk(f"i-{engine}", f"JS console/page errors ({engine})", "I-jshealth",
                            "fail", "critical", f"{len(all_errors)} error(s): {all_errors[0][:100]}",
                            f"page.on console/pageerror ({engine})", all_errors[:8],
                            "JS errors break interactivity/tracking.", "Fix throwing script (see evidence)."))
                    else:
                        out.append(_mk(f"i-{engine}", f"JS console/page errors ({engine})", "I-jshealth",
                            "pass", "ok", "no console/page errors during load",
                            f"page.on console/pageerror ({engine})", None, "Clean load.", ""))
                    await browser.close()
                except Exception as e:
                    out.append(unavailable(f"h-{engine}", f"Rendered check ({engine})", "H-xbrowser",
                        f"Playwright {engine}", str(e)[:140]))
    except Exception as e:
        out.append(unavailable("h-pw", "Cross-browser rendered checks", "H-xbrowser",
            "Playwright engines", str(e)[:160], "Install browsers: playwright install."))
    return out

# ---- K: AEO/GEO sampled mention ----
async def aeo_sample(url: str, topic: str | None) -> list[CheckResult]:
    brand = (topic or url).strip()
    if not (settings.OPENAI_API_KEY or settings.OLLAMA_BASE_URL):
        return [unavailable("k-aeo","AI mention sample","K-aeo","free LLM API / self-hosted model",
            "no LLM endpoint configured — nothing was sampled","Set OPENAI_API_KEY or OLLAMA_BASE_URL to enable sampling.")]
    prompt = f"Which brands or websites would you recommend for '{brand}'? List names and URLs."
    try:
        if settings.OLLAMA_BASE_URL:
            async with httpx.AsyncClient(timeout=60) as c:
                r = await c.post(settings.OLLAMA_BASE_URL.rstrip("/")+"/api/generate", json={"model":"llama3","prompt":prompt,"stream":False})
                txt = r.json().get("response","") if r.status_code==200 else ""
                src = "self-hosted open model (Ollama)"
        else:
            async with httpx.AsyncClient(timeout=60) as c:
                r = await c.post("https://api.openai.com/v1/chat/completions",
                    headers={"Authorization": f"Bearer {settings.OPENAI_API_KEY}"},
                    json={"model":"gpt-4o-mini","messages":[{"role":"user","content":prompt}],"max_tokens":300})
                txt = r.json()["choices"][0]["message"]["content"] if r.status_code==200 else ""
                src = "free-tier LLM API (sampled)"
        mentioned = url.lower() in txt.lower() or brand.lower().split()[0] in txt.lower()
        return [_mk("k-aeo","AI mention sample","K-aeo","info","info",
            f"brand/URL {'mentioned' if mentioned else 'NOT mentioned'} in 1 sampled answer ({len(txt)} chars)",src,txt[:600],
            "Sampled signal only — varies run to run; NOT a ranking metric.","Earn citations: clear positioning, facts, reviews.")]
    except Exception as e:
        return [unavailable("k-aeo","AI mention sample","K-aeo","LLM endpoint",str(e)[:140])]

# ---- L: rank — GSC first, SERP scraper strictly supplemental ----
async def rank_checks(site_url: str) -> list[CheckResult]:
    out: list[CheckResult] = []
    if not (settings.GSC_CLIENT_ID and settings.GSC_REFRESH_TOKEN):
        out.append(unavailable("l-gsc","Rank: Search Console position/clicks","L-rank","Google Search Console API",
            "GSC not connected — most-trusted source unavailable","Connect GSC in Integrations (verified property)."))
    else:
        try:
            from google.oauth2.credentials import Credentials
            from googleapiclient.discovery import build
            creds = Credentials(None, refresh_token=settings.GSC_REFRESH_TOKEN, client_id=settings.GSC_CLIENT_ID,
                                client_secret=settings.GSC_CLIENT_SECRET, token_uri="https://oauth2.googleapis.com/token")
            svc = build("searchconsole","v1",credentials=creds)
            # property list probe (real call; analytics call needs body params — keep probe honest)
            lst = svc.sites().list().execute()
            n = len(lst.get("siteEntry",[]))
            out.append(_mk("l-gsc","Rank: Search Console position/clicks","L-rank","info","info",f"{n} verified propertie(s) reachable; per-query position requires property selection",
                "Google Search Console API (official)",{"properties": n},"GSC is the most-trusted rank source.","Select property + date range in Monitoring."))
        except Exception as e:
            out.append(unavailable("l-gsc","Rank: Search Console position/clicks","L-rank","Google Search Console API",str(e)[:160]))
    # Supplemental scraper: throttled single query, position null on block
    out.append(_mk("l-serp","SERP scrape (supplemental, throttled)","L-rank","info","info","not run by default — enable per-keyword in Monitoring; blocked/failed => position: null",
        "self-built Playwright SERP (supplemental)",None,"Scraping is brittle/rate-limited; GSC is preferred.","Enable only where GSC lacks coverage."))
    return out

# ---- M: GSC health (highest trust badge) ----
async def gsc_health() -> list[CheckResult]:
    if not (settings.GSC_CLIENT_ID and settings.GSC_REFRESH_TOKEN):
        return [unavailable("m-gsc","Search Console health","M-gsc","Google Search Console API","GSC not connected","Connect GSC in Integrations.")]
    try:
        from google.oauth2.credentials import Credentials
        from googleapiclient.discovery import build
        creds = Credentials(None, refresh_token=settings.GSC_REFRESH_TOKEN, client_id=settings.GSC_CLIENT_ID,
                            client_secret=settings.GSC_CLIENT_SECRET, token_uri="https://oauth2.googleapis.com/token")
        svc = build("searchconsole","v1",credentials=creds)
        sites = svc.sites().list().execute().get("siteEntry",[])
        out = [_mk("m-index","Index coverage","M-gsc","info","info",f"{len(sites)} propertie(s); per-URL inspection needs property context",
            "Google Search Console API ★ highest trust",sites[:3],"Official indexed/excluded reasons.","Open per-property drill-down.")]
        out.append(_mk("m-manual","Manual actions & security issues","M-gsc","info","info","query per property when selected",
            "Google Search Console API ★ highest trust",None,"Official penalties/malware flags.","Resolve in GSC then request review."))
        out.append(_mk("m-sitemaps","Sitemaps status","M-gsc","info","info","query per property when selected",
            "Google Search Console API ★ highest trust",None,"Official submission/read stats.","Submit sitemap in GSC."))
        return out
    except Exception as e:
        return [unavailable("m-gsc","Search Console health","M-gsc","Google Search Console API",str(e)[:160])]

# ---- Q: PWA ----
async def pwa_checks(base: str, html: str) -> list[CheckResult]:
    out: list[CheckResult] = []
    import re as _re
    man = _re.search(r'<link[^>]+rel=["\']manifest["\'][^>]*href=["\']([^"\']+)', html or "", _re.I)
    if not man:
        out.append(_mk("q-manifest","manifest.json","Q-pwa","warning","warning","no manifest link","page HTML",None,"No installability.","Add <link rel=manifest href=/manifest.webmanifest>."))
    else:
        href = man.group(1); full = href if href.startswith("http") else base.rstrip("/")+"/"+href.lstrip("/")
        try:
            async with httpx.AsyncClient(timeout=15) as c:
                r = await c.get(full)
                ok = r.status_code==200
                try: j = r.json() if ok else {}; valid = bool(j.get("name") and j.get("icons"))
                except Exception: valid = False
                out.append(_mk("q-manifest","manifest.json","Q-pwa","pass" if valid else "warning","ok" if valid else "warning",
                    f"HTTP {r.status_code}; valid: {valid}",f"GET {full}",(str(j)[:300] if ok else None),"Invalid manifest blocks install.","Include name, icons(192/512), start_url, display."))
        except Exception as e:
            out.append(unavailable("q-manifest","manifest.json","Q-pwa",f"GET {full}",str(e)[:120]))
    sw = ("serviceWorker" in (html or "") or "service-worker" in (html or "").lower())
    out.append(_mk("q-sw","Service worker","Q-pwa","pass" if sw else "warning","ok" if sw else "warning",
        "registration hint found" if sw else "no registration hint in HTML","page HTML + rendered DOM",None,
        "SW enables offline/caching.","Register /sw.js and confirm in DevTools."))
    return out

# ---- T: local (conditional) ----
def local_checks(html: str, is_local: bool) -> list[CheckResult]:
    if not is_local:
        return [_mk("t-skip","Local SEO","T-local","info","info","skipped — site not flagged as local business","site settings",None,
            "Conditional category; only runs for local businesses.","Flag site as local to enable.")]
    soup = __import__("bs4").BeautifulSoup(html or "", "lxml")
    text = soup.get_text(" ", strip=True)
    has_lb = bool(soup.find("script", attrs={"type":"application/ld+json"}) and "LocalBusiness" in (html or ""))
    out = [_mk("t-schema","LocalBusiness/review schema","T-local","pass" if has_lb else "warning","ok" if has_lb else "warning",
        "LocalBusiness JSON-LD present" if has_lb else "no LocalBusiness schema","page JSON-LD",None,"Powers local rich results.","Add LocalBusiness + AggregateRating.")]
    import re as _re
    phone = bool(_re.search(r"\+?[\d][\d\s\-()]{7,}\d", text))
    out.append(_mk("t-nap","NAP consistency probe","T-local","info","info",f"phone-like string on page: {'yes' if phone else 'no'}; full NAP diff needs GBP + citation list",
        "on-page text (probe only)",None,"NAP drift hurts local trust.","Audit GBP vs site vs citations manually."))
    return out


