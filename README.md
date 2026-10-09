# Website Intelligence Platform — INTERNAL USE ONLY

One dashboard. Zero redirects to any origin checking tool's website. Every check runs on our
backend (free APIs + self-built extraction) and renders inside our UI.

## Stack
- `apps/web` — Next.js (App Router) + Tailwind. Nav: Overview / Audit / Monitoring / Integrations / Alerts / Tech Stack. Audit tabs A–T.
- `apps/api` — FastAPI (async). `src/app/services/checks/` mirrors categories; `audit_runner.py` orchestrates A–T.
- `apps/worker` — Celery + Redis + Beat (free scheduled jobs; per-category cron: technical daily, techstack daily, performance weekly; override via `POST /monitoring/schedules`).
- `packages/db/init.sql` — PostgreSQL + TimescaleDB hypertables (`audit_runs`, `alerts`, `techstack_snapshots`).
- Docker: `docker compose up -d` (uses Docker since you have it; to run without Docker see below).

## Non-negotiables (enforced in code)
- Free only: PSI free tier, GSC API, SMTP free tier / Slack-Discord webhooks, Ollama/self-hosted or free LLM tier. No paid keys.
- No fabricated scores: there is no composite SEO score anywhere.
- Failed checks → `status: "unavailable"` (gray) + `last-attempted timestamp`; never omitted/guessed.
- Every result: found → source/evidence → why → fix → checked-at. GSC rows carry ★ highest-trust badge.
- Trends break the line on missing points (see `TrendChart.tsx`) — never interpolated.

## Quick start (Docker — recommended since you have it)
```bash
cp .env.example .env   # add PAGESPEED_API_KEY + GSC OAuth for full coverage
docker compose up -d
# web http://localhost:3001 · api http://localhost:8000/health · docs http://localhost:8000/docs
# (host :3000 is owned by the legacy fully-function-dashboard dev server)
```

## Verified working (scripts/smoke_test.py — 23/23 passing)
Backend contract enforced per result: closed status/severity/category sets, non-empty
found/source/checked_at, **how_to_fix required on every warning/fail/unavailable**,
ISO timestamps, summary totals that add up. Frontend: all 6 routes return 200.
Worker: `wip.sweep` + `wip.audit_one` registered, Beat scheduler running.
State (sites/runs/alerts/schedules/integrations) persists in `./data/wip_state.json`
and survives container restarts — verified by restart test.

## Integrations (all probed live, never assumed)
- `pagespeed` — real PSI quota-spending test call on probe click
- `gsc` — real OAuth token refresh + sites.list (no quota spent), ★ highest trust
- `webhook` — live Slack/Discord test ping or SMTP login test (no email sent)
- `last_sync_at` updates only on successful probe; failures keep `last_error` + `last_attempt_at`

## Without Docker
```bash
# API
cd apps/api && pip install -r requirements.txt && PYTHONPATH=src uvicorn app.main:app --port 8000
# Web
cd apps/web && npm install && npm run dev
# Worker (optional; API works without it — schedules just won't auto-fire)
cd apps/worker && pip install -r requirements.txt && celery -A worker_app worker -B --loglevel=info
```

## Category → code map
| Nav / tab | Backend |
|---|---|
| A On-Page, R Intl, G Content | `services/checks/onpage_content.py` |
| B Technical, O Security | `services/checks/technical_security.py` |
| C Structured (+P Review/Recipe/Event/JobPosting/Video/HowTo) | `services/checks/structured.py` |
| D Perf lab+field, E A11y, S frontend depth | `services/checks/performance.py` (one PSI call, multi-category) |
| F Links (GET-verified), N Architecture | `services/checks/links_arch.py` |
| H x-browser, I console errors, J tags, K AEO, L rank, M GSC★, Q PWA, T local | `services/checks/advanced.py` |

## Disclosed limits (also shown in-platform)
- Backlinks: GSC Links report is the ceiling; no DA shown.
- AEO/GEO: sampled mention only, not a ranking metric (label in UI + API).
- SERP scraper: supplemental, throttled, `position: null` on block — GSC preferred.
- Competitors: no free tier can measure rivals' DA/backlinks exactly, so external
  competitor totals are never shown. `GET /api/v1/sites/compare?ids=1,2` compares
  only your own monitored sites from their latest stored runs (Overview page panel).
- Content stats (reading time, sentence length, paragraphs) are deterministic local
  counts, not AI judgments. Qualitative LLM review lives only in K as a labeled sample.
