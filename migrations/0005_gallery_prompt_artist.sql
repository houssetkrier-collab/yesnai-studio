-- Preserve the separated prompt and artist metadata for gallery replay.
ALTER TABLE gallery ADD COLUMN prompt_base TEXT;
ALTER TABLE gallery ADD COLUMN artist TEXT;
ALTER TABLE gallery ADD COLUMN artist_id TEXT;
ALTER TABLE gallery ADD COLUMN artist_name TEXT;
ALTER TABLE gallery ADD COLUMN final_prompt TEXT;
