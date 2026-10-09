"""Shared fetch helpers: single httpx client, redirect-chain capture, real timings."""
from __future__ import annotations
import time, ssl, socket
from urllib.parse import urlparse
import httpx
from bs4 import BeautifulSoup

DEFAULT_UA = "WIP-Internal-Audit/1.0 (+internal use only)"

async def fetch_with_chain(url: str, timeout: float = 25.0):
    """GET with redirect history preserved. Returns (final_response, chain, elapsed_s, error)."""
    chain: list[dict] = []
    start = time.perf_counter()
    try:
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True, headers={"User-Agent": DEFAULT_UA}) as c:
            resp = await c.get(url)
            for h in (resp.history or []):
                chain.append({"status": h.status_code, "url": str(h.url), "location": h.headers.get("location", "")})
            chain.append({"status": resp.status_code, "url": str(resp.url), "location": ""})
            return resp, chain, time.perf_counter() - start, None
    except Exception as e:
        return None, chain, time.perf_counter() - start, str(e)

def soup_of(html: str) -> BeautifulSoup:
    return BeautifulSoup(html or "", "lxml")

def ssl_expiry(host: str, port: int = 443, timeout: float = 10.0):
    """Real cert expiry via TLS handshake. Returns (iso_expiry | None, error | None)."""
    try:
        ctx = ssl.create_default_context()
        with socket.create_connection((host, port), timeout=timeout) as sock:
            with ctx.wrap_socket(sock, server_hostname=host) as ssock:
                cert = ssock.getpeercert()
                return cert.get("notAfter"), None
    except Exception as e:
        return None, str(e)

def domain_of(url: str) -> str:
    return urlparse(url).hostname or ""
