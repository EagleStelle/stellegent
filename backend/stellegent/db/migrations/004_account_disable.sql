-- Account enable/disable: a disabled account cannot log in but is retained.
ALTER TABLE users ADD COLUMN disabled INTEGER NOT NULL DEFAULT 0;
