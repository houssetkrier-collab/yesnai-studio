-- Single-account YesNAI Studio schema
PRAGMA foreign_keys = ON;

-- 多账号：凭据 AES-GCM 加密落库（密钥由 Worker 的 APP_ACCESS_KEY 派生），
-- 密码托管后 JWT 过期由 Worker 自动重登续期；*_enc 前缀列一律不出现在 API 响应里
CREATE TABLE IF NOT EXISTS accounts (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  label TEXT,
  username TEXT NOT NULL,
  jwt_enc TEXT NOT NULL DEFAULT '',
  password_enc TEXT NOT NULL DEFAULT '',
  api_token_enc TEXT NOT NULL DEFAULT '',
  enabled INTEGER NOT NULL DEFAULT 1 CHECK (enabled IN (0, 1)),
  gems_last INTEGER,
  last_attempt_slot TEXT,
  last_attempt_at TEXT,
  last_success_slot TEXT,
  status TEXT NOT NULL DEFAULT 'pending',
  last_message TEXT,
  retry_count INTEGER NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

-- 全局签到时刻表（时区/工作日/周末时间槽/总开关；lease 防多 cron 并发）
CREATE TABLE IF NOT EXISTS autocheckin_config (
  id INTEGER PRIMARY KEY CHECK (id = 1),
  enabled INTEGER NOT NULL DEFAULT 1 CHECK (enabled IN (0, 1)),
  timezone TEXT NOT NULL DEFAULT 'Asia/Shanghai',
  weekday_times TEXT NOT NULL DEFAULT '["09:05"]',
  weekend_times TEXT NOT NULL DEFAULT '["10:00"]',
  next_run_at TEXT,
  last_attempt_slot TEXT,
  last_attempt_at TEXT,
  last_success_slot TEXT,
  status TEXT NOT NULL DEFAULT 'pending',
  last_message TEXT,
  retry_count INTEGER NOT NULL DEFAULT 0,
  lease_until TEXT,
  updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

INSERT OR IGNORE INTO autocheckin_config (id) VALUES (1);

CREATE TABLE IF NOT EXISTS autocheckin_logs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  account_id INTEGER,
  attempted_at TEXT NOT NULL,
  slot TEXT NOT NULL,
  ok INTEGER NOT NULL CHECK (ok IN (0, 1)),
  status_code INTEGER,
  message TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS autocheckin_logs_time_idx ON autocheckin_logs(attempted_at DESC);

-- 画廊元数据；原图与缩略图二进制存 R2（img/{id} 与 thumb/{id}），D1 不放大对象
CREATE TABLE IF NOT EXISTS gallery (
  id TEXT PRIMARY KEY,
  ts INTEGER NOT NULL,
  fmt TEXT NOT NULL DEFAULT 'png',
  thumb_fmt TEXT NOT NULL DEFAULT 'png',
  prompt TEXT,
  neg TEXT,
  model TEXT,
  seed INTEGER,
  w INTEGER,
  h INTEGER,
  steps INTEGER,
  scale REAL,
  sampler TEXT,
  noise TEXT,
  n INTEGER,
  action TEXT,
  cost INTEGER,
  params_json TEXT,
  bytes INTEGER,
  thumb_bytes INTEGER
);
CREATE INDEX IF NOT EXISTS gallery_ts_idx ON gallery(ts DESC);
