from fastapi import APIRouter
from ..schemas_api import SiteIn, ScheduleIn
from .. import store

router = APIRouter()

@router.get("")
async def list_sites(): return {"sites": list(store.SITES.values())}

@router.post("")
async def create_site(body: SiteIn):
    url = body.url.strip()
    if not url.startswith(("http://","https://")): url = "https://" + url
    existing = next((s for s in store.SITES.values() if s["url"] == url), None)
    if existing:
        return {**existing, "deduped": True, "note": "URL already monitored — returning existing site, no duplicate created."}
    return store.add_site(url, body.label, body.is_local_business)

@router.get("/compare")
async def compare(ids: str):
    """Side-by-side of YOUR OWN monitored sites from their latest stored runs.
    No third-party competitor index exists on any free tier, so external
    competitor DA/backlink numbers are never shown — this compares only data
    you measured yourself. Sites without a run show null (never interpolated)."""
    out = []
    for raw in ids.split(","):
        try: sid = int(raw.strip())
        except ValueError: continue
        site = store.SITES.get(sid)
        if not site:
            out.append({"site_id": raw, "site": None, "summary": None, "last_run_at": None}); continue
        runs = [r for r in store.RUNS if r["site_id"] == sid]
        last = runs[-1] if runs else None
        out.append({"site_id": sid, "site": site,
                    "summary": (last["result"]["summary"] if last else None),
                    "last_run_at": (last["created_at"] if last else None)})
    return {"compare": out,
            "note": "Own-sites comparison only. External competitor authority/backlink totals cannot be measured exactly on free data and are not shown."}
