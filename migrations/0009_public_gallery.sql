-- 0009: public gallery metadata and visitor likes
-- Existing gallery rows remain private and undisclosed by default.
ALTER TABLE gallery ADD COLUMN title TEXT NOT NULL DEFAULT '';
ALTER TABLE gallery ADD COLUMN tags TEXT NOT NULL DEFAULT '';
ALTER TABLE gallery ADD COLUMN rating TEXT NOT NULL DEFAULT 'general';
ALTER TABLE gallery ADD COLUMN public INTEGER NOT NULL DEFAULT 0;
ALTER TABLE gallery ADD COLUMN published_at TEXT;
ALTER TABLE gallery ADD COLUMN prompt_disclosed INTEGER NOT NULL DEFAULT 0;
ALTER TABLE gallery ADD COLUMN params_disclosed INTEGER NOT NULL DEFAULT 0;
ALTER TABLE gallery ADD COLUMN view_count INTEGER NOT NULL DEFAULT 0;
ALTER TABLE gallery ADD COLUMN like_count INTEGER NOT NULL DEFAULT 0;
CREATE TABLE IF NOT EXISTS gallery_likes (
  visitor_id TEXT NOT NULL,
  gallery_id TEXT NOT NULL,
  created_at TEXT NOT NULL,
  PRIMARY KEY(visitor_id, gallery_id)
);
CREATE INDEX IF NOT EXISTS gallery_public_idx ON gallery(public, published_at DESC);
