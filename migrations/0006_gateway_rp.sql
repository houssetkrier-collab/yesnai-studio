-- 0006: RP gateway keys and request accounting
CREATE TABLE IF NOT EXISTS gateway_keys (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL DEFAULT '',
  key TEXT NOT NULL UNIQUE,
  enabled INTEGER NOT NULL DEFAULT 1,
  mode TEXT NOT NULL DEFAULT 'restricted' CHECK (mode IN ('passthrough', 'restricted')),
  policy_json TEXT NOT NULL DEFAULT '{}',
  use_count INTEGER NOT NULL DEFAULT 0,
  last_used_at TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS daily_usage (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  gateway_key_id INTEGER NOT NULL,
  usage_date TEXT NOT NULL,
  request_count INTEGER NOT NULL DEFAULT 0,
  gem_count REAL NOT NULL DEFAULT 0,
  updated_at TEXT NOT NULL,
  UNIQUE(gateway_key_id, usage_date)
);
CREATE INDEX IF NOT EXISTS daily_usage_key_date_idx ON daily_usage(gateway_key_id, usage_date);

CREATE TABLE IF NOT EXISTS concurrency_leases (
  lease_id TEXT PRIMARY KEY,
  gateway_key_id INTEGER NOT NULL,
  account_id INTEGER,
  expires_at TEXT NOT NULL,
  created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS concurrency_leases_expiry_idx ON concurrency_leases(expires_at);

CREATE TABLE IF NOT EXISTS request_logs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  request_id TEXT NOT NULL,
  gateway_key_id INTEGER,
  account_id INTEGER,
  path TEXT NOT NULL,
  mode TEXT NOT NULL,
  status_code INTEGER,
  ok INTEGER NOT NULL DEFAULT 0,
  duration_ms INTEGER,
  bytes_in INTEGER,
  bytes_out INTEGER,
  created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS request_logs_created_idx ON request_logs(created_at DESC);

CREATE TABLE IF NOT EXISTS request_attempts (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  request_id TEXT NOT NULL,
  gateway_key_id INTEGER,
  account_id INTEGER,
  attempt_no INTEGER NOT NULL,
  status_code INTEGER,
  error TEXT,
  created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS request_attempts_request_idx ON request_attempts(request_id);

CREATE TABLE IF NOT EXISTS account_rate_state (
  account_id INTEGER PRIMARY KEY,
  failure_count INTEGER NOT NULL DEFAULT 0,
  cooldown_until TEXT,
  last_status INTEGER,
  updated_at TEXT NOT NULL
);
