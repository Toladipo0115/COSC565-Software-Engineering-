-- EngageTrace database schema
-- Backing store for ingested OULAD activity data, detection runs, and results.

CREATE TABLE IF NOT EXISTS courses (
    course_id           TEXT PRIMARY KEY,       -- e.g. "AAA_2013J" (module_presentation)
    module              TEXT NOT NULL,
    presentation        TEXT NOT NULL,
    length_days          INTEGER
);

CREATE TABLE IF NOT EXISTS students (
    student_id          TEXT NOT NULL,
    course_id            TEXT NOT NULL,
    final_result         TEXT,                  -- Pass / Fail / Withdrawn / Distinction (if available)
    PRIMARY KEY (student_id, course_id),
    FOREIGN KEY (course_id) REFERENCES courses(course_id)
);

CREATE TABLE IF NOT EXISTS weekly_activity (
    student_id           TEXT NOT NULL,
    course_id            TEXT NOT NULL,
    week                  INTEGER NOT NULL,      -- 1-indexed week within the presentation
    clicks                INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (student_id, course_id, week),
    FOREIGN KEY (student_id, course_id) REFERENCES students(student_id, course_id)
);

-- one row per parameter configuration used for a detection pass
CREATE TABLE IF NOT EXISTS detection_runs (
    run_id                INTEGER PRIMARY KEY AUTOINCREMENT,
    course_id             TEXT NOT NULL,
    created_at            TEXT NOT NULL DEFAULT (datetime('now')),
    baseline_window_k     INTEGER NOT NULL,
    tau_individual         REAL NOT NULL,
    tau_context             REAL NOT NULL,
    persistence_p           INTEGER NOT NULL,
    fixed_threshold          REAL NOT NULL,
    notes                     TEXT,
    FOREIGN KEY (course_id) REFERENCES courses(course_id)
);

-- one row per (student, week, method) flag produced by a run
CREATE TABLE IF NOT EXISTS detection_flags (
    run_id                INTEGER NOT NULL,
    student_id             TEXT NOT NULL,
    week                    INTEGER NOT NULL,
    method                  TEXT NOT NULL CHECK (method IN ('fixed','individual','cusum','cap')),
    flagged                 INTEGER NOT NULL CHECK (flagged IN (0,1)),
    delta_individual        REAL,                -- individual relative-drop value, for CAP/individual
    z_context                REAL,                -- course-relative z-score, for CAP
    PRIMARY KEY (run_id, student_id, week, method),
    FOREIGN KEY (run_id) REFERENCES detection_runs(run_id)
);

CREATE INDEX IF NOT EXISTS idx_activity_course_week ON weekly_activity(course_id, week);
CREATE INDEX IF NOT EXISTS idx_flags_run_method ON detection_flags(run_id, method);
