-- Baseline schema (ported from the original Flask app).
CREATE TABLE IF NOT EXISTS lectures (
    id TEXT PRIMARY KEY,
    date TEXT NOT NULL,
    course_name TEXT,
    captured_at TEXT NOT NULL,
    image_path TEXT,
    docx_path TEXT,
    pdf_path TEXT,
    txt_path TEXT,
    manifest_path TEXT,
    raw_ocr_text TEXT,
    corrected_text TEXT,
    summary TEXT,
    tags TEXT
);
CREATE INDEX IF NOT EXISTS idx_lectures_date ON lectures(date);
CREATE INDEX IF NOT EXISTS idx_lectures_course ON lectures(course_name);

CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL CHECK(role IN ('prof', 'student', 'admin')),
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS annotations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    lecture_id TEXT REFERENCES lectures(id) ON DELETE CASCADE,
    user_id INTEGER REFERENCES users(id),
    note_text TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_annot_lecture ON annotations(lecture_id);

CREATE TABLE IF NOT EXISTS audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    action TEXT NOT NULL,
    target_id TEXT,
    ip_address TEXT,
    timestamp TEXT NOT NULL
);
