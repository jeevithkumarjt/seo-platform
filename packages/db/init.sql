-- TimescaleDB hypertables for history/trends. Every run persisted with timestamp.
CREATE EXTENSION IF NOT EXISTS timescaledb;
CREATE TABLE IF NOT EXISTS sites (id SERIAL PRIMARY KEY, url TEXT UNIQUE NOT NULL, label TEXT DEFAULT '', is_local_business BOOLEAN DEFAULT FALSE, created_at TIMESTAMPTZ DEFAULT now());
CREATE TABLE IF NOT EXISTS audit_runs (id SERIAL PRIMARY KEY, site_id INT REFERENCES sites(id), category TEXT NOT NULL, status TEXT DEFAULT 'done', result JSONB DEFAULT '{}', created_at TIMESTAMPTZ DEFAULT now());
SELECT create_hypertable('audit_runs', 'created_at', if_not_exists => TRUE);
CREATE TABLE IF NOT EXISTS alerts (id SERIAL PRIMARY KEY, site_id INT REFERENCES sites(id), kind TEXT NOT NULL, message TEXT NOT NULL, severity TEXT DEFAULT 'warning', created_at TIMESTAMPTZ DEFAULT now(), delivered BOOLEAN DEFAULT FALSE);
SELECT create_hypertable('alerts', 'created_at', if_not_exists => TRUE);
CREATE TABLE IF NOT EXISTS techstack_snapshots (id SERIAL PRIMARY KEY, site_id INT REFERENCES sites(id), detected JSONB DEFAULT '{}', created_at TIMESTAMPTZ DEFAULT now());
SELECT create_hypertable('techstack_snapshots', 'created_at', if_not_exists => TRUE);
