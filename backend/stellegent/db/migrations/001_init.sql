-- Fresh baseline schema for new Stellegent deployments.
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL,
    email TEXT NOT NULL COLLATE NOCASE,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL CHECK(role IN ('prof', 'student', 'admin')),
    auth_provider TEXT NOT NULL DEFAULT 'local',
    google_sub TEXT,
    email_verified INTEGER NOT NULL DEFAULT 0,
    disabled INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE UNIQUE INDEX IF NOT EXISTS idx_users_google_sub ON users(google_sub) WHERE google_sub IS NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS idx_users_single_admin ON users(role) WHERE role = 'admin';

CREATE TABLE IF NOT EXISTS courses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    faculty_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    description TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(faculty_id, name)
);
CREATE INDEX IF NOT EXISTS idx_courses_faculty ON courses(faculty_id);

CREATE TABLE IF NOT EXISTS course_students (
    course_id INTEGER NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at TEXT NOT NULL,
    PRIMARY KEY (course_id, user_id)
);
CREATE INDEX IF NOT EXISTS idx_course_students_user ON course_students(user_id);

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
    tags TEXT,
    owner_user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    visibility TEXT NOT NULL DEFAULT 'public' CHECK(visibility IN ('public', 'private')),
    course_id INTEGER REFERENCES courses(id) ON DELETE SET NULL
);
CREATE INDEX IF NOT EXISTS idx_lectures_date ON lectures(date);
CREATE INDEX IF NOT EXISTS idx_lectures_course ON lectures(course_name);
CREATE INDEX IF NOT EXISTS idx_lectures_owner ON lectures(owner_user_id);
CREATE INDEX IF NOT EXISTS idx_lectures_visibility ON lectures(visibility);
CREATE INDEX IF NOT EXISTS idx_lectures_course_id ON lectures(course_id);

CREATE TABLE IF NOT EXISTS lecture_students (
    lecture_id TEXT NOT NULL REFERENCES lectures(id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at TEXT NOT NULL,
    PRIMARY KEY (lecture_id, user_id)
);
CREATE INDEX IF NOT EXISTS idx_lecture_students_user ON lecture_students(user_id);

CREATE TABLE IF NOT EXISTS annotations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    lecture_id TEXT REFERENCES lectures(id) ON DELETE CASCADE,
    user_id INTEGER REFERENCES users(id),
    note_text TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_annot_lecture ON annotations(lecture_id);

CREATE TABLE IF NOT EXISTS password_resets (
    token TEXT PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    expires_at TEXT NOT NULL,
    used INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_resets_user ON password_resets(user_id);

CREATE TABLE IF NOT EXISTS audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    action TEXT NOT NULL,
    target_id TEXT,
    ip_address TEXT,
    timestamp TEXT NOT NULL
);
