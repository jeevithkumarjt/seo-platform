from fastapi import APIRouter
from .. import store

router = APIRouter()

@router.get("")
async def feed(severity: str | None = None, limit: int = 100):
    a = store.ALERTS[::-1]
    if severity: a = [x for x in a if x["severity"]==severity]
    return {"alerts": a[:limit], "note": "In-platform feed is primary; webhooks/SMTP are secondary."}
