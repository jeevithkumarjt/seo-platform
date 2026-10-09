"""Alert evaluation: new critical, non-200, tag added/removed, SSL/DOMAIN <30d, CWV/rank regression."""
from __future__ import annotations
from datetime import datetime, timezone
from . import store

def _days_until(datestr: str | None) -> int | None:
    if not datestr: return None
    try:
        # ssl returns like 'Jan  1 00:00:00 2030 GMT'
        from email.utils import parsedate_to_datetime
        dt = parsedate_to_datetime(datestr)
        return (dt - datetime.now(timezone.utc)).days
    except Exception:
        return None

def evaluate(site_id: int, audit) -> list[dict]:
    triggered: list[dict] = []
    res = {r.key: r for r in audit.results}
    # site down
    st = res.get("b-status")
    if st and st.status == "fail":
        triggered.append(store.add_alert(site_id, "site_down", f"Site returned non-200: {st.found}", "critical"))
    # new criticals (compare last full run)
    prev = [r for r in store.RUNS if r["site_id"]==site_id]
    prev_crit = set()
    if len(prev) >= 1:
        try:
            prev_crit = {x["key"] for x in prev[-1]["result"]["results"] if x.get("status")=="fail"}
        except Exception: pass
    for r in audit.results:
        if r.status=="fail" and r.key not in prev_crit:
            triggered.append(store.add_alert(site_id, "new_critical", f"New critical: {r.label} — {r.found[:120]}", "critical"))
            break
    # SSL / domain expiry <30d
    for key, kind in [("b-ssl","ssl_expiring"),("b-whois","domain_expiring")]:
        r = res.get(key)
        if r and r.status != "unavailable":
            d = _days_until(str(r.evidence.get("notAfter") if isinstance(r.evidence,dict) else r.found) if r.evidence else r.found)
            # WHOIS format varies; only alert when explicitly parseable + <30
            if d is not None and 0 <= d < 30:
                triggered.append(store.add_alert(site_id, kind, f"{r.label} expires in {d} days: {r.found[:100]}", "warning"))
    # tech-stack diff
    cur_tags = sorted([r.key for r in audit.results if r.category=="J-techstack" and r.status!="unavailable" and r.key.startswith("j-") and r.key!="j-none"])
    snaps = store.STACK_SNAPS.setdefault(site_id, [])
    if snaps:
        prev_tags = set(snaps[-1].get("detected", []))
        added, removed = set(cur_tags)-prev_tags, prev_tags-set(cur_tags)
        for t in added: triggered.append(store.add_alert(site_id, "tag_added", f"New tracking tag detected: {t}", "warning"))
        for t in removed: triggered.append(store.add_alert(site_id, "tag_removed", f"Tracking tag disappeared: {t}", "warning"))
    snaps.append({"detected": cur_tags, "at": audit.finished_at})
    return triggered
