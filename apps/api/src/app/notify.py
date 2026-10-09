"""Free delivery: SMTP (Gmail free tier) and/or Slack/Discord webhook. Alerts feed is primary."""
from __future__ import annotations
import smtplib, json
from email.mime.text import MIMEText
import httpx
from .config import settings

async def deliver(message: str) -> dict:
    out: dict = {}
    if settings.SMTP_HOST and settings.SMTP_USER:
        try:
            msg = MIMEText(message)
            msg["Subject"] = "[WIP] Website alert"; msg["From"] = settings.ALERT_FROM or settings.SMTP_USER; msg["To"] = settings.SMTP_USER
            with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=10) as s:
                s.starttls(); s.login(settings.SMTP_USER, settings.SMTP_PASS); s.send_message(msg)
            out["smtp"] = "sent"
        except Exception as e: out["smtp"] = f"failed: {str(e)[:100]}"
    for name, url in [("slack", settings.SLACK_WEBHOOK_URL), ("discord", settings.DISCORD_WEBHOOK_URL)]:
        if url:
            try:
                async with httpx.AsyncClient(timeout=10) as c:
                    r = await c.post(url, json={"text": message} if name=="slack" else {"content": message})
                out[name] = f"HTTP {r.status_code}"
            except Exception as e: out[name] = f"failed: {str(e)[:100]}"
    return out
