from fastapi import APIRouter
from .. import store

router = APIRouter()

@router.get("/diff")
async def diff(site_id: int):
    snaps = store.STACK_SNAPS.get(site_id, [])
    if len(snaps) < 2:
        return {"diff": [], "note": "Need ≥2 scans for a diff.", "snapshots": len(snaps)}
    prev, cur = set(snaps[-2]["detected"]), set(snaps[-1]["detected"])
    return {"added": sorted(cur-prev), "removed": sorted(prev-cur),
            "first_seen": snaps[0]["at"], "last_seen": snaps[-1]["at"], "snapshots": len(snaps)}
