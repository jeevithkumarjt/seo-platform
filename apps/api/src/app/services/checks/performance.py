"""Categories D (Performance lab+field + screenshots), E (Accessibility), S (Front-end depth).
Single PageSpeed Insights call with multiple categories — lab and CrUX shown separately.
Screenshots captured from PSI final-screenshot + screenshot-thumbnails audits."""
from __future__ import annotations
import httpx
from ...schemas import CheckResult, unavailable
from ...config import settings
from datetime import datetime, timezone
def now(): return datetime.now(timezone.utc).isoformat()
SRC = "PageSpeed Insights API (free tier)"

def _mk(key,label,cat,status,sev,found,evidence,why,fix,conf="measured"):
    return CheckResult(key=key,label=label,category=cat,status=status,severity=sev,found=found,source=SRC,
        evidence=evidence,why_matters=why,how_to_fix=fix,checked_at=now(),confidence=conf)

def _num(audits: dict, key: str):
    try:
        a = audits.get(key, {})
        v = a.get("numericValue", a.get("displayValue"))
        return v
    except Exception: return None

def _score(audits: dict, key: str) -> float:
    try: return float(audits.get(key, {}).get("score", 1))
    except Exception: return 1.0

async def performance_checks(url: str) -> list[CheckResult]:
    out: list[CheckResult] = []
    if not settings.PAGESPEED_API_KEY:
        return [
            unavailable("d-psi","PageSpeed Insights (lab+field)","D-performance",SRC,
                "PAGESPEED_API_KEY not configured — no lab or field data fetched",
                "Add a free PageSpeed API key in Integrations, then re-run."),
            unavailable("e-psi","Accessibility (via PSI)","E-a11y",SRC,
                "same PSI call as Performance — blocked by missing PAGESPEED_API_KEY",
                "Add a free PageSpeed API key in Integrations, then re-run."),
            unavailable("s-psi","Front-end depth (via PSI)","S-frontend",SRC,
                "same PSI payload as Performance — blocked by missing PAGESPEED_API_KEY",
                "Add a free PageSpeed API key in Integrations, then re-run."),
        ]
    try:
        async with httpx.AsyncClient(timeout=120) as c:
            r = await c.get("https://www.googleapis.com/pagespeedonline/v5/runPagespeed",
                params={"url": url, "key": settings.PAGESPEED_API_KEY, "strategy": "mobile",
                        "category": ["performance","accessibility","best-practices","seo"]})
            if r.status_code != 200:
                return [
                    unavailable("d-psi","PageSpeed Insights (lab+field)","D-performance",SRC,
                        f"PSI HTTP {r.status_code}: {r.text[:160]}","Retry; check quota."),
                    unavailable("e-psi","Accessibility (via PSI)","E-a11y",SRC,
                        f"same PSI call failed (HTTP {r.status_code})","Retry; check quota."),
                    unavailable("s-psi","Front-end depth (via PSI)","S-frontend",SRC,
                        f"same PSI payload failed (HTTP {r.status_code})","Retry; check quota."),
                ]
            data = r.json()
    except Exception as e:
        return [
            unavailable("d-psi","PageSpeed Insights (lab+field)","D-performance",SRC,f"request failed: {str(e)[:140]}","Retry."),
            unavailable("e-psi","Accessibility (via PSI)","E-a11y",SRC,f"same PSI call failed: {str(e)[:140]}","Retry."),
            unavailable("s-psi","Front-end depth (via PSI)","S-frontend",SRC,f"same PSI payload failed: {str(e)[:140]}","Retry."),
        ]
    lr = data.get("lighthouseResult", {})
    audits = lr.get("audits", {}); cats = lr.get("categories", {})
    perf_score = cats.get("performance", {}).get("score")
    if perf_score is not None:
        out.append(_mk("d-score","Performance score (Lighthouse)","D-performance",
            "pass" if perf_score>=0.9 else ("warning" if perf_score>=0.5 else "fail"),
            "ok" if perf_score>=0.9 else ("warning" if perf_score>=0.5 else "critical"),
            f"{round(perf_score*100)}/100",{"score":perf_score},
            "Composite lab performance score (0-100).","Focus on failing metrics below." if perf_score<0.9 else ""))
    # ---- LAB METRICS with detailed thresholds ----
    lab_metrics = [
        ("largest-contentful-paint","LCP (lab)","2500ms = good; 4000ms = poor","Compress hero image, preload LCP element, cut render-blocking JS, use CDN."),
        ("first-contentful-paint","FCP (lab)","1800ms = good; 3000ms = poor","Inline critical CSS, defer non-critical JS, reduce server response time."),
        ("interactive","TTI","3800ms = good; 7300ms = poor","Break up long tasks, defer third-parties, reduce main-thread work."),
        ("cumulative-layout-shift","CLS (lab)","0.1 = good; 0.25 = poor","Size images/embeds, reserve ad slots, avoid dynamic content injection."),
        ("speed-index","Speed Index","3400ms = good; 5800ms = poor","Reduce main-thread work, optimize images, lazy-load below-fold."),
        ("total-blocking-time","TBT (lab)","200ms = good; 600ms = poor","Defer scripts, code-split, break up long tasks."),
        ("server-response-time","TTFB (lab)","800ms = good; 1800ms = poor","Cache HTML at CDN, trim server work, use edge caching."),
    ]
    for key, label, thresholds, fix in lab_metrics:
        v = _num(audits, key)
        dv = audits.get(key, {}).get("displayValue", str(v) if v is not None else "?")
        if v is None:
            out.append(unavailable(f"d-{key}",label,"D-performance",SRC,"metric absent in PSI response","Re-run audit."))
            continue
        score = _score(audits, key)
        status = "pass" if score >= 0.9 else ("warning" if score >= 0.5 else "fail")
        sev = "ok" if status == "pass" else ("warning" if status == "warning" else "critical")
        out.append(_mk(f"d-{key}",label+" — lab","D-performance",status,sev,
            f"{dv} (score {score:.2f}) · thresholds: {thresholds}",
            {"displayValue":dv,"numericValue":v,"score":score,"thresholds":thresholds},
            f"Lab value; field (CrUX) may differ. Thresholds: {thresholds}",
            "" if status == "pass" else fix))
    # ---- FIELD (CrUX) — separate, never blended ----
    crux = data.get("loadingExperience", {}).get("metrics", {})
    if not crux:
        out.append(unavailable("d-crux","CrUX field data","D-performance",SRC+" (origin field)",
            "no CrUX data for this origin/URL (low traffic or new page)",
            "Field data accrues with real Chrome traffic; rely on lab meanwhile."))
    else:
        field_map = [
            ("LARGEST_CONTENTFUL_PAINT_MS","LCP (field CrUX)","2500ms = good; 4000ms = poor"),
            ("FIRST_INPUT_DELAY_MS","FID (field CrUX)","100ms = good; 300ms = poor"),
            ("CUMULATIVE_LAYOUT_SHIFT_SCORE","CLS (field CrUX)","0.1 = good; 0.25 = poor"),
            ("INTERACTION_TO_NEXT_PAINT","INP (field CrUX)","200ms = good; 500ms = poor"),
        ]
        for m, label, thresholds in field_map:
            e = crux.get(m)
            cat_str = e.get("category","") if e else ""
            p75 = e.get("percentile","?") if e else "?"
            is_good = "GOOD" in cat_str.upper() if cat_str else False
            is_poor = "SLOW" in cat_str.upper() or "POOR" in cat_str.upper() if cat_str else False
            out.append(_mk("d-field-"+m,label+" — field (CrUX)","D-performance",
                "pass" if is_good else ("warning" if not is_poor and e else "fail"),
                "ok" if is_good else ("critical" if is_poor else "warning"),
                f"{cat_str} · p75={p75} · thresholds: {thresholds}" if e else f"no data · thresholds: {thresholds}",
                e if e else None,
                f"Real-user field data (CrUX). Thresholds: {thresholds}",
                "" if is_good else "Optimize the corresponding lab bottleneck above."))
    # ---- SCREENSHOTS ----
    final_ss = audits.get("final-screenshot", {})
    if final_ss and final_ss.get("details", {}).get("data"):
        data_url = final_ss["details"]["data"]
        out.append(_mk("d-screenshot-final","Final page screenshot","D-performance","info","info",
            "captured after page fully loaded",
            {"type":"image","dataUrl":data_url,"fullSize":True},
            "Visual snapshot of the fully loaded page. Review for layout, content, and rendering issues.",
            "Check for layout shift, missing content, or rendering bugs."))
    ss_thumbs = audits.get("screenshot-thumbnails", {})
    if ss_thumbs and ss_thumbs.get("details", {}).get("items"):
        items = ss_thumbs["details"]["items"]
        if items and len(items) > 1:
            last = items[-1]
            if last.get("data"):
                out.append(_mk("d-screenshot-loading","Loading progression (final frame)","D-performance","info","info",
                    f"frame at {last.get('timing',0):.0f}ms of {len(items)} captured frames",
                    {"type":"image","dataUrl":last["data"],"timing":last.get("timing",0)},
                    "Shows the page state after all loading completed.",
                    "Review for progressive loading issues."))
    # ---- LCP ELEMENT DETAILS ----
    lcp_el = audits.get("largest-contentful-paint-element", {})
    if lcp_el and lcp_el.get("details", {}).get("items"):
        lcp_items = lcp_el["details"]["items"]
        lcp_node = lcp_items[0].get("node", {}) if lcp_items else {}
        snippet = lcp_node.get("snippet", "")
        selector = lcp_node.get("selector", "")
        out.append(_mk("d-lcp-element","LCP element","D-performance","info","info",
            f"selector: {selector[:120]}",{"snippet":snippet[:300],"selector":selector},
            "The largest contentful paint element. Optimize this element for faster LCP.",
            "Preload this element, compress images, reduce server response time."))
    # ---- RENDER-BLOCKING RESOURCES ----
    rb = audits.get("render-blocking-resources", {})
    if rb and rb.get("details", {}).get("items"):
        rb_items = rb["details"]["items"]
        rb_urls = [i.get("url","")[:100] for i in rb_items[:5]]
        rb_savings = rb.get("displayValue","")
        out.append(_mk("d-renderblock","Render-blocking resources","D-performance",
            "warning" if rb.get("score",1)<0.9 else "pass",
            "warning" if rb.get("score",1)<0.9 else "ok",
            f"{len(rb_items)} blocking resource(s): {rb_savings}",
            {"urls":rb_urls,"savings":rb_savings},
            "Render-blocking resources delay first paint.",
            "Defer/async, inline critical CSS, use preload."))
    else:
        out.append(_mk("d-renderblock","Render-blocking resources","D-performance","pass","ok",
            "no render-blocking resources detected",None,"Clean first paint.",""))
    # ---- UNUSED JAVASCRIPT ----
    uj = audits.get("unused-javascript", {})
    if uj and uj.get("details", {}).get("items"):
        uj_items = uj["details"]["items"]
        total_waste = sum(i.get("wastedBytes", 0) for i in uj_items)
        uj_urls = [i.get("url","")[:80] for i in uj_items[:5]]
        out.append(_mk("d-unused-js","Unused JavaScript","D-performance",
            "warning" if total_waste > 50000 else "pass",
            "warning" if total_waste > 50000 else "ok",
            f"{len(uj_items)} scripts, {total_waste/1024:.0f} KB wasted",
            {"urls":uj_urls,"wastedBytes":total_waste},
            "Dead JS ships bytes for nothing.","Tree-shake, code-split, lazy-load."))
    # ---- UNUSED CSS ----
    uc = audits.get("unused-css-rules", {})
    if uc and uc.get("details", {}).get("items"):
        uc_items = uc["details"]["items"]
        total_waste = sum(i.get("wastedBytes", 0) for i in uc_items)
        out.append(_mk("d-unused-css","Unused CSS","D-performance",
            "warning" if total_waste > 30000 else "pass",
            "warning" if total_waste > 30000 else "ok",
            f"{len(uc_items)} stylesheets, {total_waste/1024:.0f} KB wasted",
            {"wastedBytes":total_waste},
            "Dead CSS blocks render and wastes bytes.","Purge unused rules; use critical CSS."))
    # ---- THIRD-PARTY WEIGHT ----
    tp = audits.get("third-party-summary", {})
    if tp and tp.get("details", {}).get("items"):
        tp_items = tp["details"]["items"]
        tp_count = len(tp_items)
        tp_blocking = sum(1 for i in tp_items if i.get("blockingTime", 0) > 0)
        tp_urls = [i.get("entity", str(i.get("url","")))[:60] for i in tp_items[:5]]
        out.append(_mk("d-3p","Third-party count/weight","D-performance",
            "warning" if tp_blocking>0 else "pass",
            "warning" if tp_blocking>0 else "ok",
            f"{tp_count} third-parties, {tp_blocking} blocking",
            {"count":tp_count,"blocking":tp_blocking,"urls":tp_urls},
            "Third parties dominate load on many sites.","Defer/async tags; self-host where possible."))
    else:
        tp_simple = audits.get("third-party-summary", {})
        out.append(_mk("d-3p","Third-party count/weight","D-performance","info","info",
            str(tp_simple.get("displayValue","not reported")),tp_simple.get("details",{}),
            "Third parties dominate load on many sites.","Defer/async tags; self-host where possible."))
    # ---- FONT DISPLAY ----
    fd = audits.get("font-display", {})
    if fd:
        out.append(_mk("d-fontdisplay","font-display strategy","D-performance",
            "pass" if fd.get("score",1)==1 else "warning",
            "ok" if fd.get("score",1)==1 else "warning",
            str(fd.get("displayValue","pass" if fd.get("score",1)==1 else "review")),
            fd.get("details",{}),
            "Missing font-display causes invisible text (FOIT).","Add font-display: swap."))
    # ---- IMAGE OPTIMIZATION ----
    img_opt = audits.get("uses-optimized-images", {})
    if img_opt and img_opt.get("details", {}).get("items"):
        img_items = img_opt["details"]["items"]
        total_waste = sum(i.get("wastedBytes", 0) for i in img_items)
        out.append(_mk("d-imgopt","Image optimization","D-performance",
            "warning" if total_waste > 50000 else "pass",
            "warning" if total_waste > 50000 else "ok",
            f"{len(img_items)} image(s), {total_waste/1024:.0f} KB optimizable",
            {"wastedBytes":total_waste},
            "Unoptimized images waste bandwidth.","Use WebP/AVIF, compress, lazy-load."))
    # ---- IMAGE SIZING ----
    img_sz = audits.get("uses-responsive-images", {})
    if img_sz and img_sz.get("details", {}).get("items"):
        img_items = img_sz["details"]["items"]
        total_waste = sum(i.get("wastedBytes", 0) for i in img_items)
        out.append(_mk("d-imgsize","Responsive image sizing","D-performance",
            "warning" if total_waste > 50000 else "pass",
            "warning" if total_waste > 50000 else "ok",
            f"{len(img_items)} oversized image(s), {total_waste/1024:.0f} KB waste",
            {"wastedBytes":total_waste},
            "Oversized images waste bandwidth on mobile.","Use srcset/sizes; serve appropriately sized images."))
    else:
        out.append(_mk("d-imgsize","Responsive image sizing","D-performance","pass","ok",
            "no oversized images detected",None,"Images sized correctly.",""))
    # ---- MAIN THREAD WORK ----
    mt = audits.get("mainthread-work-breakdown", {})
    if mt and mt.get("numericValue"):
        mt_val = mt["numericValue"]
        out.append(_mk("d-mainthread","Main-thread work","D-performance",
            "warning" if mt_val > 4000 else "pass",
            "warning" if mt_val > 4000 else "ok",
            f"{mt_val/1000:.1f}s total main-thread work",
            {"numericValue":mt_val,"displayValue":mt.get("displayValue","")},
            "Heavy main-thread work blocks interaction.",
            "Reduce JS execution, break up long tasks." if mt_val > 4000 else ""))
    # ---- LONG TASKS ----
    lt = audits.get("long-tasks", {})
    if lt and lt.get("details", {}).get("items"):
        lt_items = lt["details"]["items"]
        out.append(_mk("d-longtasks","Long tasks","D-performance",
            "warning" if lt_items else "pass",
            "warning" if lt_items else "ok",
            f"{len(lt_items)} long task(s) detected",
            {"count":len(lt_items)},
            "Long tasks (>50ms) block user interaction.",
            "Break up long tasks; use requestIdleCallback." if lt_items else ""))
    # ---- E: ACCESSIBILITY (same PSI call) ----
    acc = cats.get("accessibility", {}).get("score")
    if acc is not None:
        out.append(_mk("e-score","Accessibility score","E-a11y",
            "pass" if acc>=0.9 else "warning",
            "ok" if acc>=0.9 else "warning",
            f"{round(acc*100)}/100",{"score":acc},
            "Overall accessibility score (0-100) from Lighthouse.",
            "Fix the failing a11y audits below." if acc<0.9 else ""))
    for aid in ["color-contrast","aria-allowed-attr","label","form-field-labels","image-alt","link-name","button-name","select-name","aria-valid-attr-value","frame-title","meta-viewport"]:
        a = audits.get(aid)
        if not a: continue
        passed = a.get("score",1) == 1
        out.append(_mk("e-"+aid,"A11y: "+a.get("title",aid),"E-a11y",
            "pass" if passed else ("warning" if a.get("score") is not None else "info"),
            "ok" if passed else "warning",
            a.get("displayValue", "pass" if passed else "needs review"),
            a.get("details",{}),
            "Accessibility barrier for users/assistive tech.",
            ("Fix: "+a.get("description","")[:200]) if not passed else ""))
    # ---- DOM SIZE ----
    dom = audits.get("dom-size", {})
    out.append(_mk("s-dom","DOM node count","S-frontend",
        "warning" if "Excessive" in str(dom.get("displayValue","")) else "pass",
        "warning" if "Excessive" in str(dom.get("displayValue","")) else "ok",
        str(dom.get("displayValue","not reported")),dom.get("numericValue"),
        "Huge DOMs slow rendering/interaction.","Flatten DOM, virtualize lists."))
    # ---- JS BOOT-UP TIME ----
    boot = audits.get("bootup-time", {})
    if boot and boot.get("numericValue"):
        boot_val = boot["numericValue"]
        out.append(_mk("s-bootup","JavaScript boot-up time","S-frontend",
            "warning" if boot_val > 1500 else "pass",
            "warning" if boot_val > 1500 else "ok",
            f"{boot_val/1000:.1f}s JavaScript boot-up",
            {"numericValue":boot_val,"displayValue":boot.get("displayValue","")},
            "Slow JS boot delays interactivity.",
            "Reduce JS bundle size; defer non-critical scripts." if boot_val > 1500 else ""))
    # ---- NETWORK REQUESTS ----
    nr = audits.get("network-requests", {})
    if nr and nr.get("details", {}).get("items"):
        nr_items = nr["details"]["items"]
        nr_count = len(nr_items)
        nr_total_bytes = sum(i.get("transferSize", 0) for i in nr_items)
        out.append(_mk("s-network","Network requests","S-frontend",
            "warning" if nr_count > 80 else "pass",
            "warning" if nr_count > 80 else "ok",
            f"{nr_count} requests, {nr_total_bytes/1024/1024:.1f} MB total",
            {"count":nr_count,"totalBytes":nr_total_bytes},
            "Too many requests slow page load.",
            "Bundle assets; use HTTP/2 multiplexing." if nr_count > 80 else ""))
    # ---- JS/CSS COVERAGE (redundant but explicit for I category) ----
    for aid, label in [("unused-javascript","Unused JS"),("unused-css-rules","Unused CSS")]:
        a = audits.get(aid, {})
        if a.get("details", {}).get("items"):
            items = a["details"]["items"]
            waste = sum(i.get("wastedBytes", 0) for i in items)
            out.append(_mk("s-"+aid,label+" (coverage)","S-frontend","info","info",
                f"{len(items)} resource(s), {waste/1024:.0f} KB wasted",
                {"count":len(items),"wastedBytes":waste},
                "Dead code ships bytes for nothing.","Tree-shake / code-split / purge."))
    return out
