"""Unified result envelope. Every check returns this shape. No scores, no estimates."""
from __future__ import annotations
from datetime import datetime, timezone
from typing import Any, Literal
from pydantic import BaseModel, Field

Status = Literal["pass", "warning", "fail", "unavailable", "info"]
Confidence = Literal["google-official", "measured", "sampled", "unavailable"]

class CheckResult(BaseModel):
    key: str
    label: str
    category: str  # e.g. "A-onpage", "B-technical", ... "T-local"
    status: Status
    severity: Literal["ok", "info", "warning", "critical", "unknown"] = "ok"
    found: str = ""            # what was found (measured value or "unavailable: reason")
    source: str = ""           # e.g. "rendered DOM (Chromium)", "PageSpeed Insights API (lab)", "Google Search Console API"
    evidence: Any = None       # raw measured snippet (headers, tag value, metric)
    why_matters: str = ""      # one-liner
    how_to_fix: str = ""       # actionable fix, empty only when pass
    checked_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    confidence: Confidence = "measured"

def unavailable(key: str, label: str, category: str, source: str, reason: str, how_to_fix: str = "") -> CheckResult:
    return CheckResult(
        key=key, label=label, category=category, status="unavailable", severity="unknown",
        found=f"unavailable: {reason}", source=source, evidence=None,
        why_matters="Check could not run; no value is inferred.",
        how_to_fix=how_to_fix or "Retry the audit. If it persists, configure the required free API key / integration.",
        confidence="unavailable",
    )

class AuditResponse(BaseModel):
    url: str
    started_at: str
    finished_at: str
    results: list[CheckResult]
    summary: dict[str, int]
