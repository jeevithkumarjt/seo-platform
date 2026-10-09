from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .config import settings
from .routers import audit, sites, monitoring, alerts, integrations, techstack

app = FastAPI(title="Website Intelligence Platform API", version="1.0.0",
    description="INTERNAL USE ONLY. Every value measured; failures are 'unavailable', never guessed.")

app.add_middleware(CORSMiddleware, allow_origins=settings.ALLOWED_ORIGINS + ["*"],
    allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

for r, prefix, tag in [(audit.router,"/api/v1/audit","audit"),(sites.router,"/api/v1/sites","sites"),
    (monitoring.router,"/api/v1/monitoring","monitoring"),(alerts.router,"/api/v1/alerts","alerts"),
    (integrations.router,"/api/v1/integrations","integrations"),(techstack.router,"/api/v1/techstack","techstack")]:
    app.include_router(r, prefix=prefix, tags=[tag])

@app.get("/health")
async def health(): return {"status": "ok", "internal_only": True}
