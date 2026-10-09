"""Async SQLAlchemy models. Timescale hypertables created in packages/db/init.sql."""
from datetime import datetime, timezone
from sqlalchemy import String, Text, DateTime, ForeignKey, JSON, Integer
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

def utcnow(): return datetime.now(timezone.utc)

class Base(DeclarativeBase): pass

class Site(Base):
    __tablename__ = "sites"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    url: Mapped[str] = mapped_column(String(2048), unique=True, index=True)
    label: Mapped[str] = mapped_column(String(256), default="")
    is_local_business: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

class AuditRun(Base):
    __tablename__ = "audit_runs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    site_id: Mapped[int] = mapped_column(ForeignKey("sites.id"), index=True)
    category: Mapped[str] = mapped_column(String(64), index=True)  # technical|performance|techstack|full
    status: Mapped[str] = mapped_column(String(32), default="done")
    result: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)

class MonitorSchedule(Base):
    __tablename__ = "monitor_schedules"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    site_id: Mapped[int] = mapped_column(ForeignKey("sites.id"), index=True)
    category: Mapped[str] = mapped_column(String(64))  # technical|performance|techstack
    cron: Mapped[str] = mapped_column(String(64), default="0 6 * * *")
    enabled: Mapped[bool] = mapped_column(default=True)

class Alert(Base):
    __tablename__ = "alerts"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    site_id: Mapped[int] = mapped_column(ForeignKey("sites.id"), index=True)
    kind: Mapped[str] = mapped_column(String(64), index=True)
    message: Mapped[str] = mapped_column(Text)
    severity: Mapped[str] = mapped_column(String(16), default="warning")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    delivered: Mapped[bool] = mapped_column(default=False)

class TechStackSnapshot(Base):
    __tablename__ = "techstack_snapshots"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    site_id: Mapped[int] = mapped_column(ForeignKey("sites.id"), index=True)
    detected: Mapped[dict] = mapped_column(JSON, default=dict)  # {vendor: {first_seen, last_seen, evidence}}
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)

class Integration(Base):
    __tablename__ = "integrations"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    kind: Mapped[str] = mapped_column(String(64), unique=True)  # gsc|pagespeed|webhook
    status: Mapped[str] = mapped_column(String(32), default="disconnected")
    last_sync_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    config: Mapped[dict] = mapped_column(JSON, default=dict)
