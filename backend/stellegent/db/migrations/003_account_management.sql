-- Account, course, and lecture ownership model.
--
-- Keep the existing role names for compatibility:
--   admin   = the single superadmin
--   prof    = faculty
--   student = read-only learner

-- If an older dev database somehow has more than one admin, keep the earliest
-- account as the one superadmin and demote the rest before adding the guard.
UPDATE users
SET role = 'prof'
WHERE role = 'admin'
  AND id NOT IN (
    SELECT id FROM users WHERE role = 'admin' ORDER BY id LIMIT 1
  );

CREATE UNIQUE INDEX IF NOT EXISTS idx_users_single_admin
ON users(role)
WHERE role = 'admin';

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

CREATE TABLE IF NOT EXISTS lecture_students (
    lecture_id TEXT NOT NULL REFERENCES lectures(id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at TEXT NOT NULL,
    PRIMARY KEY (lecture_id, user_id)
);
CREATE INDEX IF NOT EXISTS idx_lecture_students_user ON lecture_students(user_id);

ALTER TABLE lectures ADD COLUMN owner_user_id INTEGER REFERENCES users(id) ON DELETE SET NULL;
ALTER TABLE lectures ADD COLUMN visibility TEXT NOT NULL DEFAULT 'public' CHECK(visibility IN ('public', 'private'));
ALTER TABLE lectures ADD COLUMN course_id INTEGER REFERENCES courses(id) ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS idx_lectures_owner ON lectures(owner_user_id);
CREATE INDEX IF NOT EXISTS idx_lectures_visibility ON lectures(visibility);
CREATE INDEX IF NOT EXISTS idx_lectures_course_id ON lectures(course_id);
