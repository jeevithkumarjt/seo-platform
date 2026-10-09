from pydantic import BaseModel

class AuditRequest(BaseModel):
    url: str
    keyword: str | None = None
    topic: str | None = None
    is_local_business: bool = False
    include_rendered: bool = True

class SiteIn(BaseModel):
    url: str
    label: str = ""
    is_local_business: bool = False

class ScheduleIn(BaseModel):
    site_id: int
    category: str  # technical|performance|techstack
    cron: str = "0 6 * * *"
    enabled: bool = True
