"""Central config. Free-tier only. Missing keys => checks report unavailable, never fake."""
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite+aiosqlite:///./wip.db"
    REDIS_URL: str = "redis://localhost:6379/0"
    ALLOWED_ORIGINS: list[str] = ["http://localhost:3000"]
    PAGESPEED_API_KEY: str = ""
    GSC_CLIENT_ID: str = ""
    GSC_CLIENT_SECRET: str = ""
    GSC_REFRESH_TOKEN: str = ""
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASS: str = ""
    ALERT_FROM: str = ""
    SLACK_WEBHOOK_URL: str = ""
    DISCORD_WEBHOOK_URL: str = ""
    OPENAI_API_KEY: str = ""
    OLLAMA_BASE_URL: str = ""
    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()
