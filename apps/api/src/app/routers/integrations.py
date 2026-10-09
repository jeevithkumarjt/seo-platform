"""Integrations with REAL probes. Status reflects a live validation, never assumed.
last_sync_at = last SUCCESSFUL probe only. Failures record last_error + last_attempt_at."""
from __future__ import annotations
from fastapi import APIRouter
import httpx
from .. import store
from ..config import settings

router = APIRouter()

def _snapshot():
    gsc = bool(settings.GSC_CLIENT_ID and settings.GSC_REFRESH_TOKEN)
    psi = bool(settings.PAGESPEED_API_KEY)
    hook = bool(settings.SLACK_WEBHOOK_URL or settings.DISCORD_WEBHOOK_URL or (settings.SMTP_HOST and settings.SMTP_USER))
    for kind, configured in [("gsc", gsc), ("pagespeed", psi), ("webhook", hook)]:
        row = store.INTEGRATIONS[kind]
        if not configured and row["status"] == "connected":
            store.touch_integration(kind, "failed", "credentials removed from environment")
    return store.INTEGRATIONS

@router.get("")
async def list_all(): return {"integrations": _snapshot()}

async def _probe_pagespeed() -> tuple[bool, str]:
    if not settings.PAGESPEED_API_KEY:
        return False, "PAGESPEED_API_KEY not set — add the free key to .env"
    try:
        async with httpx.AsyncClient(timeout=60) as c:
            r = await c.get("https://www.googleapis.com/pagespeedonline/v5/runPagespeed",
                params={"url": "https://example.com", "key": settings.PAGESPEED_API_KEY,
                        "strategy": "mobile", "category": "performance"})
        if r.status_code == 200:
            return True, "live PSI call succeeded (1 quota unit used)"
        return False, f"PSI HTTP {r.status_code}: {r.text[:160]}"
    except Exception as e:
        return False, f"probe request failed: {str(e)[:160]}"

async def _probe_gsc() -> tuple[bool, str]:
    if not (settings.GSC_CLIENT_ID and settings.GSC_REFRESH_TOKEN):
        return False, "GSC OAuth not configured — set GSC_CLIENT_ID + GSC_REFRESH_TOKEN"
    try:
        from google.oauth2.credentials import Credentials
        from google.auth.transport.requests import Request
        creds = Credentials(None, refresh_token=settings.GSC_REFRESH_TOKEN, client_id=settings.GSC_CLIENT_ID,
                            client_secret=settings.GSC_CLIENT_SECRET, token_uri="https://oauth2.googleapis.com/token")
        creds.refresh(Request())  # real token refresh, no quota spent
        from googleapiclient.discovery import build
        svc = build("searchconsole", "v1", credentials=creds)
        sites = svc.sites().list().execute().get("siteEntry", [])
        return True, f"OAuth refresh + sites.list ok: {len(sites)} verified propertie(s)"
    except Exception as e:
        return False, f"GSC validation failed: {str(e)[:200]}"

async def _probe_webhook() -> tuple[bool, str]:
    notes: list[str] = []
    if settings.SLACK_WEBHOOK_URL:
        try:
            async with httpx.AsyncClient(timeout=15) as c:
                r = await c.post(settings.SLACK_WEBHOOK_URL, json={"text": "WIP connectivity probe — no action needed."})
            notes.append(f"slack HTTP {r.status_code}" if r.status_code == 200 else f"slack HTTP {r.status_code}: {r.text[:100]}")
        except Exception as e: notes.append(f"slack failed: {str(e)[:100]}")
    if settings.DISCORD_WEBHOOK_URL:
        try:
            async with httpx.AsyncClient(timeout=15) as c:
                r = await c.post(settings.DISCORD_WEBHOOK_URL, json={"content": "WIP connectivity probe — no action needed."})
            notes.append(f"discord HTTP {r.status_code}" if r.status_code in (200, 204) else f"discord HTTP {r.status_code}: {r.text[:100]}")
        except Exception as e: notes.append(f"discord failed: {str(e)[:100]}")
    if settings.SMTP_HOST and settings.SMTP_USER:
        import smtplib
        try:
            with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=15) as s:
                s.starttls(); s.login(settings.SMTP_USER, settings.SMTP_PASS or "")
            notes.append("smtp login ok (no email sent)")
        except Exception as e: notes.append(f"smtp failed: {str(e)[:120]}")
    if not notes:
        return False, "no webhook/SMTP target configured"
    ok = any(x.endswith("ok (no email sent)") or "HTTP 200" in x or "HTTP 204" in x for x in notes)
    return ok, "; ".join(notes)[:300]

@router.post("/sync")
async def sync(kind: str):
    if kind == "pagespeed": ok, note = await _probe_pagespeed()
    elif kind == "gsc": ok, note = await _probe_gsc()
    elif kind == "webhook": ok, note = await _probe_webhook()
    else: return {"error": "unknown kind (gsc|pagespeed|webhook)"}
    row = store.touch_integration(kind, "connected" if ok else "failed", None if ok else note)
    return {"integration": row, "sync": "ok" if ok else "failed", "detail": note}
