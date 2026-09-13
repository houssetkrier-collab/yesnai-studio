-- 0007: gateway policy compatibility, safe defaults, atomic concurrency state, and cost accounting
-- One-time migration for databases that have not applied these schema changes yet.
-- Do not re-run manually on an upgraded database: ALTER TABLE ADD COLUMN is intentionally not idempotent.
ALTER TABLE gateway_keys ADD COLUMN active_concurrency INTEGER NOT NULL DEFAULT 0;
ALTER TABLE request_logs ADD COLUMN cost_gems REAL;

-- Rebuild only when needed by the migration runner; the table shape is retained for fresh installs.
CREATE TABLE IF NOT EXISTS gateway_keys_v7 (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL DEFAULT '', key TEXT NOT NULL UNIQUE, enabled INTEGER NOT NULL DEFAULT 1,
  mode TEXT NOT NULL DEFAULT 'restricted' CHECK (mode IN ('passthrough', 'restricted')),
  policy_json TEXT NOT NULL DEFAULT '{}', use_count INTEGER NOT NULL DEFAULT 0,
  last_used_at TEXT, active_concurrency INTEGER NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL, updated_at TEXT NOT NULL
);
INSERT OR IGNORE INTO gateway_keys_v7(id,name,key,enabled,mode,policy_json,use_count,last_used_at,active_concurrency,created_at,updated_at)
  SELECT id,name,key,enabled,CASE WHEN mode='passthrough' THEN 'passthrough' ELSE 'restricted' END,policy_json,use_count,last_used_at,active_concurrency,created_at,updated_at FROM gateway_keys;
-- Keep the original table and avoid destructive rebuilds on repeated migration execution.
CREATE UNIQUE INDEX IF NOT EXISTS gateway_keys_key_idx ON gateway_keys(key);
CREATE INDEX IF NOT EXISTS request_logs_created_idx ON request_logs(created_at DESC);
