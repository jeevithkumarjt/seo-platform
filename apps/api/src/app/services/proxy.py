"""Server-side HTML proxy so live previews work even on sites that set X-Frame-Options / CSP.
We fetch the page like a normal browser, inject a <base> so all assets resolve from the
real origin, rewrite links so click-through navigation stays inside the proxy, strip
framing/CSP headers, and replay it from our own origin. Never fabricated.
"""
from __future__ import annotations
import re, urllib.parse, httpx

_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0 Safari/537.36"
_BLOCKED = {"x-frame-options", "content-security-policy", "strict-transport-security"}


def _to_abs(base: str, href: str) -> str:
    return urllib.parse.urljoin(base, href)


def _rewrite_anchors(html: str, proxy_path: str, base: str) -> str:
    def _a(m: re.Match) -> str:
        tag = m.group(0)
        href = m.group("href")
        if not href or href.startswith(("#", "javascript:", "mailto:", "tel:", "whatsapp:",
                                          "data:", "blob:")):
            return tag
        abs_url = _to_abs(base, href)
        # absolute out-of-host links open directly
        try:
            u = urllib.parse.urlsplit(abs_url)
            b = urllib.parse.urlsplit(base)
            out = u.scheme and u.netloc and u.netloc != b.netloc
        except Exception:
            out = False
        if out:
            return f'<a href="{abs_url}" target="_blank" rel="noopener">'
        proxied = f"{proxy_path}?url={urllib.parse.quote(abs_url, safe='')}"
        return f'<a href="{proxied}">'

    return re.sub(r'<a\b[^>]*?\bhref=(["\'])(?P<href>.*?)\1[^>]*?>', _a, html, flags=re.I | re.S)


async def fetch_proxied(url: str, base_url: str | None = None) -> httpx.Response:
    target = _to_abs(base_url or url, url)
    async with httpx.AsyncClient(follow_redirects=True, timeout=25,
                                 headers={"User-Agent": _UA,
                                          "Accept": "text/html,application/xhtml+xml,*/*;q=0.8"}) as c:
        r = await c.get(target)
    return r


async def build_proxied(url: str) -> tuple[bytes, str]:
    """Return (body_bytes, content_type) with anchor rewriting + <base> injected for HTML."""
    base = url
    r = await fetch_proxied(url)
    ctype = r.headers.get("content-type", "").lower()
    if not ctype.startswith("text/html") and not (b"<!doctype html" in r.content[:512] or b"<html" in r.content[:1024]):
        return r.content, ctype or "application/octet-stream"
    html = r.content.decode("utf-8", errors="replace")
    # inject base so CSS/JS/images resolve from the real origin
    parsed = urllib.parse.urlsplit(str(r.url) or url)
    origin = f"{parsed.scheme}://{parsed.netloc}"
    if "<head" in html:
        html = html.replace("<head", f'<head><base href="{origin}/">', 1)
    else:
        html = "<base href=\"{0}/\">".format(origin) + html
    # rewrite anchors so internal links stay in the proxy (click-through works)
    html = _rewrite_anchors(html, "/api/v1/audit/proxy", origin)
    return html.encode("utf-8"), "text/html; charset=utf-8"