-- 0003: 运行时 KV —— 外部网关与网页「自动」账号共用的轮询游标（round-robin）
CREATE TABLE IF NOT EXISTS runtime_kv (k TEXT PRIMARY KEY, v TEXT NOT NULL);
