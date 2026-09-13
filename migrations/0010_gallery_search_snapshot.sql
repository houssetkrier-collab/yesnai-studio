ALTER TABLE gallery ADD COLUMN prompt_hash TEXT;
ALTER TABLE gallery ADD COLUMN snapshot_id TEXT;
CREATE INDEX IF NOT EXISTS gallery_prompt_hash_idx ON gallery(prompt_hash);
CREATE INDEX IF NOT EXISTS gallery_snapshot_id_idx ON gallery(snapshot_id);
CREATE INDEX IF NOT EXISTS gallery_model_idx ON gallery(model);
CREATE INDEX IF NOT EXISTS gallery_artist_id_idx ON gallery(artist_id);
