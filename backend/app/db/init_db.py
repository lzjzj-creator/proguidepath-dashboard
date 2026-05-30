import os
import sqlite3
from typing import Optional

from app.db.connection import database_connection, postgres_cursor, sqlite_db_path, using_postgres


def _db_path() -> str:
    return sqlite_db_path()


def _init_postgres() -> None:
    with database_connection() as conn:
        with postgres_cursor(conn) as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS resume_records (
                    id SERIAL PRIMARY KEY,
                    filename TEXT NOT NULL,
                    user_id TEXT,
                    user_role TEXT NOT NULL DEFAULT 'student',
                    extracted_text TEXT,
                    sections_json TEXT,
                    suggestions_json TEXT,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            cur.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_resume_records_created_at
                ON resume_records(created_at)
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS job_profiles (
                    id SERIAL PRIMARY KEY,
                    title TEXT NOT NULL,
                    responsibilities TEXT NOT NULL,
                    must_haves_json TEXT NOT NULL,
                    nice_to_haves_json TEXT NOT NULL,
                    experience_years TEXT NOT NULL,
                    keywords_json TEXT NOT NULL,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS match_results (
                    id SERIAL PRIMARY KEY,
                    resume_id INTEGER NOT NULL REFERENCES resume_records(id),
                    job_profile_id INTEGER NOT NULL REFERENCES job_profiles(id),
                    status TEXT NOT NULL,
                    match_score INTEGER NOT NULL,
                    result_json TEXT NOT NULL,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS ai_call_logs (
                    id SERIAL PRIMARY KEY,
                    user_id TEXT,
                    user_role TEXT NOT NULL DEFAULT 'student',
                    feature TEXT NOT NULL,
                    endpoint TEXT NOT NULL,
                    status TEXT NOT NULL,
                    duration_ms INTEGER NOT NULL DEFAULT 0,
                    error_message TEXT NOT NULL DEFAULT '',
                    metadata_json TEXT NOT NULL DEFAULT '{}',
                    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            cur.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_match_results_resume_id
                ON match_results(resume_id)
                """
            )
            cur.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_ai_call_logs_created_at
                ON ai_call_logs(created_at)
                """
            )
            cur.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_ai_call_logs_feature
                ON ai_call_logs(feature)
                """
            )
            cur.execute(
                """
                ALTER TABLE resume_records
                ADD COLUMN IF NOT EXISTS user_id TEXT
                """
            )
            cur.execute(
                """
                ALTER TABLE resume_records
                ADD COLUMN IF NOT EXISTS user_role TEXT NOT NULL DEFAULT 'student'
                """
            )
        conn.commit()


def init_db(db_path: Optional[str] = None) -> None:
    if using_postgres():
        _init_postgres()
        return

    path = sqlite_db_path(db_path)
    os.makedirs(os.path.dirname(path), exist_ok=True)

    conn = sqlite3.connect(path)
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS resume_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT NOT NULL,
                user_id TEXT,
                user_role TEXT NOT NULL DEFAULT 'student',
                extracted_text TEXT,
                sections_json TEXT,
                suggestions_json TEXT,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                updated_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_resume_records_created_at
            ON resume_records(created_at)
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS job_profiles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                responsibilities TEXT NOT NULL,
                must_haves_json TEXT NOT NULL,
                nice_to_haves_json TEXT NOT NULL,
                experience_years TEXT NOT NULL,
                keywords_json TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS match_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                resume_id INTEGER NOT NULL,
                job_profile_id INTEGER NOT NULL,
                status TEXT NOT NULL,
                match_score INTEGER NOT NULL,
                result_json TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                FOREIGN KEY(resume_id) REFERENCES resume_records(id),
                FOREIGN KEY(job_profile_id) REFERENCES job_profiles(id)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS ai_call_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT,
                user_role TEXT NOT NULL DEFAULT 'student',
                feature TEXT NOT NULL,
                endpoint TEXT NOT NULL,
                status TEXT NOT NULL,
                duration_ms INTEGER NOT NULL DEFAULT 0,
                error_message TEXT NOT NULL DEFAULT '',
                metadata_json TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_match_results_resume_id
            ON match_results(resume_id)
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_ai_call_logs_created_at
            ON ai_call_logs(created_at)
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_ai_call_logs_feature
            ON ai_call_logs(feature)
            """
        )
        columns = {
            row[1]
            for row in conn.execute("PRAGMA table_info(resume_records)").fetchall()
        }
        if "user_id" not in columns:
            conn.execute("ALTER TABLE resume_records ADD COLUMN user_id TEXT")
        if "user_role" not in columns:
            conn.execute("ALTER TABLE resume_records ADD COLUMN user_role TEXT NOT NULL DEFAULT 'student'")
        conn.commit()
    finally:
        conn.close()
