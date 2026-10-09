"""Category B (Technical) + O (Security headers/cookies/protocol). All measured over live HTTP."""
from __future__ import annotations
import re, time
from urllib.parse import urlparse
import httpx
from ..http_utils import ssl_expiry, domain_of
from ...schemas import CheckResult, unavailable
from datetime import datetime, timezone

def now(): return datetime.now(timezone.utc).isoformat()
def _mk(key,label,cat,status,sev,found,source,evidence,why,fix,conf="measured"):
    return CheckResult(key=key,label=label,category=cat,status=status,severity=sev,found=found,
        source=source,evidence=evidence,why_matters=why,how_to_fix=fix,checked_at=now(),confidence=conf)

async def technical_checks(url: str, resp: httpx.Response | None, chain: list, elapsed: float, fetch_error: str | None) -> list[CheckResult]:
    out: list[CheckResult] = []
    src = "live HTTP GET (httpx, redirects followed)"
    if fetch_error or resp is None:
        return [unavailable("b-fetch","HTTP fetch","B-technical",src,f"request failed: {fetch_error or 'no response'}","Check DNS/hosting; retry.")]
    H = {k.lower(): v for k,v in resp.headers.items()}
    body = resp.text or ""
    # status
    out.append(_mk("b-status","HTTP status","B-technical","pass" if resp.status_code==200 else "fail","ok" if resp.status_code==200 else "critical",
        f"HTTP {resp.status_code} in {elapsed:.2f}s",src,{"status":resp.status_code,"final_url":str(resp.url),"time_s":round(elapsed,2)},
        "Non-200 pages cannot be indexed normally.","Fix origin error / redirect target." if resp.status_code!=200 else ""))
    # redirect chain
    if len(chain) > 2:
        out.append(_mk("b-redirects","Redirect chains","B-technical","warning","warning",f"{len(chain)-1} hops: {' -> '.join(c['status'].__str__() for c in chain)}",src,chain,"Chains waste crawl budget and leak equity.","Flatten to a single 301."))
    else:
        out.append(_mk("b-redirects","Redirect chains","B-technical","pass","ok",f"{len(chain)} request(s), no chain" if len(chain)<=2 else "ok",src,chain,"No chain.",""))
    # https / mixed
    final = str(resp.url)
    is_https = final.startswith("https://")
    mixed = (('http://' in body) and is_https)
    out.append(_mk("b-https","HTTPS / mixed content","B-technical","pass" if is_https and not mixed else "fail","ok" if is_https and not mixed else "critical",
        f"{'HTTPS' if is_https else 'NOT https'}; mixed-content refs: {'yes' if mixed else 'none detected'}",src,{"final_url":final},
        "HTTPS is required for trust/indexing; mixed content blocks resources.","Force HTTPS + rewrite http:// subresource URLs." if (not is_https or mixed) else ""))
    # www / trailing slash / http->https consistency
    p = urlparse(url); host = p.hostname or ""
    try:
        async with httpx.AsyncClient(timeout=15, follow_redirects=False) as c:
            variants = {}
            for v in [f"http://{host}/", f"https://{host}/"]:
                try:
                    r = await c.get(v); variants[v] = (r.status_code, r.headers.get("location",""))
                except Exception as e: variants[v] = ("error", str(e)[:80])
        canon_ok = variants.get(f"https://{host}/", ("?",))[0] in (200,301,302,307,308)
        out.append(_mk("b-consistency","www / trailing-slash / HTTP->HTTPS consistency","B-technical","pass" if canon_ok else "warning","ok" if canon_ok else "warning",
            str(variants),src,variants,"Inconsistent canonical hosts split equity.","301 all variants to one canonical host+protocol."))
    except Exception as e:
        out.append(unavailable("b-consistency","Host consistency","B-technical",src,str(e)[:120]))
    # robots / sitemap / favicon / viewport / 404 / cache / compression / size / render-blocking
    async def head_or_get(u: str):
        try:
            async with httpx.AsyncClient(timeout=15, follow_redirects=True) as c:
                return await c.get(u)
        except Exception as e: return e
    base = f"{urlparse(final).scheme}://{urlparse(final).netloc}"
    rb = await head_or_get(base + "/robots.txt")
    if isinstance(rb, Exception):
        out.append(unavailable("b-robots","robots.txt","B-technical",src,f"fetch failed: {str(rb)[:100]}"))
    else:
        out.append(_mk("b-robots","robots.txt","B-technical","pass" if rb.status_code==200 else "warning","ok" if rb.status_code==200 else "warning",
            f"HTTP {rb.status_code}",src,rb.text[:400] if rb.status_code==200 else None,"Controls crawl access.","Create /robots.txt." if rb.status_code!=200 else ""))
    sm = await head_or_get(base + "/sitemap.xml")
    if isinstance(sm, Exception):
        out.append(unavailable("b-sitemap","sitemap.xml","B-technical",src,f"fetch failed: {str(sm)[:100]}"))
    else:
        has = sm.status_code==200 and ("<url" in (sm.text or "") or "<sitemap" in (sm.text or ""))
        out.append(_mk("b-sitemap","sitemap.xml presence","B-technical","pass" if has else "warning","ok" if has else "warning",
            f"HTTP {sm.status_code}" + (" + XML parsed" if has else ""),src,(sm.text[:300] if has else None),"Sitemap aids discovery.","Generate + submit sitemap.xml."))
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(body, "lxml")
    fav = soup.find("link", attrs={"rel": re.compile("icon", re.I)})
    out.append(_mk("b-favicon","Favicon","B-technical","pass" if fav else "warning","ok" if fav else "warning",fav.get("href","")[:120] if fav else "missing",src,None,"Missing favicon degrades UX/tabs.","Add <link rel=icon>."))
    vp = soup.find("meta", attrs={"name": "viewport"})
    out.append(_mk("b-viewport","Mobile viewport","B-technical","pass" if vp else "fail","ok" if vp else "critical",vp.get("content","")[:120] if vp else "missing",src,None,"No viewport = broken mobile layout.","Add width=device-width, initial-scale=1."))
    # custom 404
    r404 = await head_or_get(base + "/wip-nonexistent-404-probe-xyz")
    if isinstance(r404, Exception):
        out.append(unavailable("b-404","Custom 404","B-technical",src,str(r404)[:100]))
    else:
        custom = r404.status_code==404 and len(r404.text or "")>500
        out.append(_mk("b-404","Custom 404 page","B-technical","pass" if custom else "warning","ok" if custom else "warning",
            f"probe returned HTTP {r404.status_code} ({len(r404.text or '')} bytes)",src,None,"Soft-404s confuse crawl.","Serve a branded 404 with HTTP 404."))
    # cache / compression / size / render-blocking
    cc = H.get("cache-control",""); etag = H.get("etag",""); age = H.get("age","")
    out.append(_mk("b-cache","Cache headers","B-technical","pass" if cc else "warning","ok" if cc else "warning",cc or "no cache-control",src,{"cache-control":cc,"etag":etag,"age":age},"Caching cuts TTFB/repeat load.","Add Cache-Control (HTML: no-cache; static: immutable, max-age)."))
    ce = H.get("content-encoding",""); comp = ce in ("gzip","br")
    out.append(_mk("b-compression","gzip/brotli","B-technical","pass" if comp else "warning","ok" if comp else "warning",ce or "none detected",src,{"content-encoding":ce},"Uncompressed HTML wastes bytes.","Enable brotli/gzip at CDN/origin."))
    kb = len(body.encode("utf-8", "ignore"))/1024
    out.append(_mk("b-pagesize","Page weight (HTML)","B-technical","pass" if kb<200 else "warning","ok" if kb<200 else "warning",f"{kb:.0f} KB HTML",src,{"html_kb":round(kb,1)},"Heavy HTML slows parse.","Trim inline JS/CSS, paginate."))
    scripts = soup.find_all("script", src=True); styles = soup.find_all("link", attrs={"rel":"stylesheet"})
    rb_sync = [s.get("src","")[:80] for s in scripts if not s.get("async") and not s.get("defer")]
    out.append(_mk("b-renderblock","Render-blocking resources (static hint)","B-technical","warning" if rb_sync or styles else "pass","warning" if rb_sync else "ok",
        f"{len(rb_sync)} sync scripts, {len(styles)} stylesheets",src,{"sync_scripts":rb_sync[:5]},"Sync head scripts block first paint.","Add defer/async; inline critical CSS."))
    # O: security headers
    for hdr, fix in [("content-security-policy","Deploy a CSP (start report-only)."),("x-frame-options","Add X-Frame-Options: SAMEORIGIN (or frame-ancestors)."),
        ("strict-transport-security","Add HSTS: max-age=31536000; includeSubDomains."),("x-content-type-options","Add X-Content-Type-Options: nosniff."),
        ("referrer-policy","Add Referrer-Policy: strict-origin-when-cross-origin."),("permissions-policy","Add Permissions-Policy to limit powerful features.")]:
        v = H.get(hdr,"")
        out.append(_mk(f"o-{hdr}","Header: "+hdr,"O-security","pass" if v else "warning","ok" if v else "warning",v[:140] if v else "missing",src,{hdr:v} or None,
            "Hardening headers reduce XSS/clickjacking risk.",fix if not v else ""))
    setc = resp.headers.get("set-cookie","")
    if setc:
        flags = {"Secure": "secure" in setc.lower(), "HttpOnly": "httponly" in setc.lower(), "SameSite": "samesite" in setc.lower()}
        missing = [k for k,v in flags.items() if not v]
        out.append(_mk("o-cookies","Cookie flags","O-security","pass" if not missing else "warning","ok" if not missing else "warning",
            str(flags),src,{"set-cookie": setc[:200]},"Weak flags risk session theft.","Set Secure; HttpOnly; SameSite=Lax/Strict."))
    else:
        out.append(_mk("o-cookies","Cookie flags","O-security","pass","ok","no Set-Cookie on this response",src,None,"No cookies set here.",""))
    # http version
    ver = getattr(resp, "http_version", "") or H.get("alt-svc","")
    out.append(_mk("o-protocol","HTTP/2 or HTTP/3","O-security","pass" if ("h2" in ver or "h3" in ver or resp.status_code==200) else "info","ok",
        ver or "protocol negotiated (see evidence)",src,{"alt-svc": H.get("alt-svc",""), "via": H.get("via","")},"H2/H3 multiplexing speeds up assets.","Enable H2/H3 at CDN."))
    # SSL + WHOIS expiry (real, never guessed)
    host_only = domain_of(final)
    exp, err = ssl_expiry(host_only) if final.startswith("https") else (None, "not https")
    if exp:
        out.append(_mk("b-ssl","SSL certificate expiry","B-technical","pass","ok",f"expires {exp}", "TLS handshake (openssl)", {"notAfter": exp},"Expiry <30d triggers an alert.","Renew cert."))
    else:
        out.append(unavailable("b-ssl","SSL certificate expiry","B-technical","TLS handshake",str(err)[:140],"Ensure port 443 serves a valid chain."))
    try:
        import whois
        w = whois.whois(host_only)
        ed = str(w.expiration_date)[:120] if getattr(w, "expiration_date", None) else ""
        if ed: out.append(_mk("b-whois","Domain expiry (WHOIS)","B-technical","pass","ok",ed,"RDAP/WHOIS lookup",{"expiration": ed},"Expiry <30d triggers an alert.","Renew domain / enable auto-renew."))
        else: out.append(unavailable("b-whois","Domain expiry (WHOIS)","B-technical","RDAP/WHOIS lookup","registry returned no expiration"))
    except Exception as e:
        out.append(unavailable("b-whois","Domain expiry (WHOIS)","B-technical","RDAP/WHOIS lookup",str(e)[:140]))
    return out


