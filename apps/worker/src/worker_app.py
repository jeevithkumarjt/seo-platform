"""Scheduled jobs: per-site, per-category (technical/performance/techstack). Cheaper than BullMQ license: Celery+Redis+Beat, free."""
from __future__ import annotations
import os
import httpx
from celery import Celery
from celery.schedules import crontab

REDIS = os.getenv("REDIS_URL", "redis://localhost:6379/0")
API = os.getenv("API_BASE", "http://localhost:8000")

app = Celery("wip", broker=REDIS, backend=REDIS)
# Default daily 06:00 sweep; per-category rows in monitor_schedules override via API.
app.conf.beat_schedule = {
    "sweep-technical-daily": {"task": "wip.sweep", "schedule": crontab(hour=6, minute=0), "args": ("technical",)},
    "sweep-techstack-daily": {"task": "wip.sweep", "schedule": crontab(hour=6, minute=30), "args": ("techstack",)},
    "sweep-performance-weekly": {"task": "wip.sweep", "schedule": crontab(hour=7, minute=0, day_of_week=1), "args": ("performance",)},
}

@app.task(name="wip.sweep")
def sweep(category: str):
    """Pull schedules for category and trigger full audits (filtered server-side later). Returns per-site status."""
    try:
        sites = httpx.get(f"{API}/api/v1/sites", timeout=15).json().get("sites", [])
    except Exception as e:
        return {"error": f"cannot list sites: {e}"}
    out = []
    for s in sites:
        try:
            r = httpx.post(f"{API}/api/v1/audit/run", json={"url": s["url"], "is_local_business": s.get("is_local_business", False)}, timeout=180)
            out.append({"site": s["url"], "status": r.status_code})
        except Exception as e:
            out.append({"site": s.get("url"), "status": f"unavailable: {str(e)[:100]}"})
    return {"category": category, "results": out}

@app.task(name="wip.audit_one")
def audit_one(url: str):
    r = httpx.post(f"{API}/api/v1/audit/run", json={"url": url}, timeout=180)
    return {"status": r.status_code, "body": r.text[:500]}
