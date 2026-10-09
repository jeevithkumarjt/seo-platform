"""File-persisted store (DATA_DIR, default ./data). Survives restarts; caps history size.
Every run persisted with timestamp for trends/diffs. No fabricated data — only measured runs."""
from __future__ import annotations
import json, os, threading
from datetime import datetime, timezone
from typing import Any

DATA_DIR = os.getenv("DATA_DIR", os.path.join(os.getcwd(), "data"))
os.makedirs(DATA_DIR, exist_ok=True)
_STATE_FILE = os.path.join(DATA_DIR, "wip_state.json")
_lock = threading.Lock()
_MAX_RUNS_PER_SITE = 50
_MAX_ALERTS = 500

SITES: dict[int, dict] = {}
RUNS: list[dict] = []
ALERTS: list[dict] = []
SCHEDULES: list[dict] = []
STACK_SNAPS: dict[int, list[dict]] = {}
INTEGRATIONS: dict[str, dict] = {
    "gsc": {"kind":"gsc","status":"disconnected","last_sync_at":None,"last_attempt_at":None,"last_error":None,"note":"Connect a verified property (OAuth). Highest-trust tier."},
    "pagespeed": {"kind":"pagespeed","status":"disconnected","last_sync_at":None,"last_attempt_at":None,"last_error":None,"note":"Add free PageSpeed API key."},
    "webhook": {"kind":"webhook","status":"disconnected","last_sync_at":None,"last_attempt_at":None,"last_error":None,"note":"Slack/Discord webhook or free SMTP."},
}
_seq = {"site": 1, "alert": 1}

def utc(): return datetime.now(timezone.utc).isoformat()

def _snapshot() -> dict:
    return {"sites": SITES, "runs": RUNS[-(_MAX_RUNS_PER_SITE*10):], "alerts": ALERTS[-_MAX_ALERTS:],
            "schedules": SCHEDULES, "snaps": STACK_SNAPS, "integrations": INTEGRATIONS, "seq": _seq}

def _persist():
    try:
        with _lock:
            with open(_STATE_FILE + ".tmp", "w", encoding="utf-8") as f:
                json.dump(_snapshot(), f)
            os.replace(_STATE_FILE + ".tmp", _STATE_FILE)
    except Exception:
        pass  # persistence is best-effort; in-memory stays authoritative

def _load():
    global SITES, RUNS, ALERTS, SCHEDULES, STACK_SNAPS, INTEGRATIONS, _seq
    try:
        if not os.path.exists(_STATE_FILE): return
        with open(_STATE_FILE, encoding="utf-8") as f:
            d = json.load(f)
        SITES = {int(k): v for k, v in d.get("sites", {}).items()}
        RUNS = d.get("runs", []); ALERTS = d.get("alerts", [])
        SCHEDULES = d.get("schedules", [])
        STACK_SNAPS = {int(k): v for k, v in d.get("snaps", {}).items()}
        for k, v in d.get("integrations", {}).items():
            if k in INTEGRATIONS: INTEGRATIONS[k].update(v)
        _seq.update(d.get("seq", {}))
    except Exception:
        pass

_load()

def add_site(url: str, label: str, is_local: bool) -> dict:
    sid = _seq["site"]; _seq["site"] += 1
    SITES[sid] = {"id": sid, "url": url, "label": label or url, "is_local_business": is_local, "created_at": utc()}
    _persist(); return SITES[sid]

def add_run(site_id: int, category: str, result: Any) -> dict:
    run = {"id": (RUNS[-1]["id"] + 1 if RUNS else 1), "site_id": site_id, "category": category, "result": result, "created_at": utc()}
    RUNS.append(run)
    # cap per site
    ids = [r["id"] for r in RUNS if r["site_id"] == site_id]
    if len(ids) > _MAX_RUNS_PER_SITE:
        drop = set(ids[:-_MAX_RUNS_PER_SITE])
        RUNS[:] = [r for r in RUNS if r["id"] not in drop]
    _persist(); return run

def add_alert(site_id: int, kind: str, message: str, severity: str) -> dict:
    a = {"id": _seq["alert"], "site_id": site_id, "kind": kind, "message": message, "severity": severity, "created_at": utc(), "delivered": False}
    _seq["alert"] += 1; ALERTS.append(a)
    del ALERTS[:-_MAX_ALERTS]
    _persist(); return a

def touch_integration(kind: str, status: str, error: str | None = None):
    if kind not in INTEGRATIONS: return None
    row = INTEGRATIONS[kind]
    row["last_attempt_at"] = utc()
    if status == "connected":
        row["status"] = "connected"; row["last_sync_at"] = row["last_attempt_at"]; row["last_error"] = None
    else:
        row["status"] = "disconnected"; row["last_error"] = (error or "probe failed")[:300]
    _persist(); return row
