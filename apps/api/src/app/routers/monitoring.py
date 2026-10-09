from fastapi import APIRouter
from ..schemas_api import ScheduleIn
from .. import store

router = APIRouter()

@router.get("/schedules")
async def schedules(site_id: int | None = None):
    s = store.SCHEDULES
    return {"schedules": [x for x in s if site_id is None or x["site_id"]==site_id]}

@router.post("/schedules")
async def upsert_schedule(body: ScheduleIn):
    row = {"id": len(store.SCHEDULES)+1, **body.model_dump()}
    store.SCHEDULES.append(row)
    return row

@router.get("/runs")
async def runs(site_id: int, category: str | None = None):
    return {"runs": [r for r in store.RUNS if r["site_id"]==site_id and (category is None or r["category"]==category)]}
