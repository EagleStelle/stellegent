-- Store the raw (unprocessed) board image alongside the preprocessed one so the
-- UI can toggle between them. OCR runs on the raw image.
ALTER TABLE lectures ADD COLUMN raw_image_path TEXT;
