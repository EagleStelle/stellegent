-- Manifest JSON export dropped: SQLite is the source of truth and the file's
-- only unique data (per-line OCR boxes) is no longer used.
ALTER TABLE lectures DROP COLUMN manifest_path;
