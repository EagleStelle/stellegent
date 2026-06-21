-- Durable queue for image-processing work created by uploads and captures.
CREATE TABLE IF NOT EXISTS processing_tasks (
    id TEXT PRIMARY KEY,
    kind TEXT NOT NULL CHECK(kind IN ('upload', 'capture')),
    status TEXT NOT NULL CHECK(status IN ('queued', 'running', 'succeeded', 'failed')),
    created_by_user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    course_name TEXT,
    course_id INTEGER REFERENCES courses(id) ON DELETE SET NULL,
    filename TEXT,
    payload TEXT NOT NULL,
    lecture_id TEXT REFERENCES lectures(id) ON DELETE SET NULL,
    error TEXT,
    attempts INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    started_at TEXT,
    completed_at TEXT,
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_processing_tasks_status_created
    ON processing_tasks(status, created_at);
CREATE INDEX IF NOT EXISTS idx_processing_tasks_user
    ON processing_tasks(created_by_user_id);
