-- 0004: 分发密钥（yst- 前缀子密钥）——外部工具/朋友用 OpenAI 兼容端点接入，
-- 不暴露 APP_ACCESS_KEY 主密钥；简单版：启停/删除 + 使用计数，不做额度限制
CREATE TABLE IF NOT EXISTS api_tokens (
  id INTEGER PRIMARY KEY,
  name TEXT NOT NULL DEFAULT '',
  key TEXT NOT NULL UNIQUE,
  enabled INTEGER NOT NULL DEFAULT 1,
  use_count INTEGER NOT NULL DEFAULT 0,
  last_used_at TEXT,
  created_at TEXT NOT NULL
);
