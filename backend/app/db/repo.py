import json
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from app.db.connection import database_connection, postgres_cursor, using_postgres


@dataclass
class ResumeRecord:
    id: int
    filename: str
    user_id: Optional[str]
    user_role: str
    extracted_text: Optional[str]
    sections_json: Optional[str]
    suggestions_json: Optional[str]
    created_at: str
    updated_at: str


class ResumeRepo:
    def __init__(self, db_path: Optional[str] = None) -> None:
        self._use_postgres = using_postgres()
        self._db_path = db_path

    def _connect(self):
        return database_connection(self._db_path)

    def _normalized_sql(self, sql: str) -> str:
        if not self._use_postgres:
            return sql
        return sql.replace("?", "%s").replace("datetime('now')", "CURRENT_TIMESTAMP")

    def _execute_write(self, conn: Any, sql: str, params: tuple[Any, ...] = ()) -> int:
        if self._use_postgres:
            with postgres_cursor(conn) as cur:
                cur.execute(self._normalized_sql(sql), params)
                return cur.rowcount
        cur = conn.execute(sql, params)
        return cur.rowcount

    def _fetchone(self, conn: Any, sql: str, params: tuple[Any, ...] = ()) -> Any:
        if self._use_postgres:
            with postgres_cursor(conn) as cur:
                cur.execute(self._normalized_sql(sql), params)
                return cur.fetchone()
        return conn.execute(sql, params).fetchone()

    def _fetchall(self, conn: Any, sql: str, params: tuple[Any, ...] = ()) -> List[Any]:
        if self._use_postgres:
            with postgres_cursor(conn) as cur:
                cur.execute(self._normalized_sql(sql), params)
                return list(cur.fetchall())
        return list(conn.execute(sql, params).fetchall())

    def _insert_and_get_id(self, conn: Any, sql: str, params: tuple[Any, ...]) -> int:
        if self._use_postgres:
            row = self._fetchone(conn, f"{sql} RETURNING id", params)
            if row is None:
                raise RuntimeError("failed to insert row")
            return int(row["id"])
        cur = conn.execute(sql, params)
        return int(cur.lastrowid)

    def create_record(self, filename: str, user_id: Optional[str] = None, user_role: str = "student") -> int:
        with self._connect() as conn:
            record_id = self._insert_and_get_id(
                conn,
                "INSERT INTO resume_records(filename, user_id, user_role) VALUES (?, ?, ?)",
                (filename, user_id, user_role),
            )
            conn.commit()
            return record_id

    def set_ocr_result(self, resume_id: int, extracted_text: str, sections: Any) -> None:
        sections_json = json.dumps(sections, ensure_ascii=False)
        with self._connect() as conn:
            rowcount = self._execute_write(
                conn,
                """
                UPDATE resume_records
                SET extracted_text = ?, sections_json = ?, updated_at = datetime('now')
                WHERE id = ?
                """,
                (extracted_text, sections_json, resume_id),
            )
            if rowcount == 0:
                raise ValueError(f"resume record not found: {resume_id}")
            conn.commit()

    def set_suggestions(self, resume_id: int, suggestions: Any) -> None:
        suggestions_json = json.dumps(suggestions, ensure_ascii=False)
        with self._connect() as conn:
            rowcount = self._execute_write(
                conn,
                """
                UPDATE resume_records
                SET suggestions_json = ?, updated_at = datetime('now')
                WHERE id = ?
                """,
                (suggestions_json, resume_id),
            )
            if rowcount == 0:
                raise ValueError(f"resume record not found: {resume_id}")
            conn.commit()

    def delete_record(self, resume_id: int) -> None:
        with self._connect() as conn:
            self._execute_write(conn, "DELETE FROM resume_records WHERE id = ?", (resume_id,))
            conn.commit()

    def get_record(self, resume_id: int) -> Optional[ResumeRecord]:
        with self._connect() as conn:
            row = self._fetchone(
                conn,
                """
                SELECT id, filename, user_id, user_role, extracted_text, sections_json, suggestions_json, created_at, updated_at
                FROM resume_records
                WHERE id = ?
                """,
                (resume_id,),
            )

        if row is None:
            return None

        return ResumeRecord(
            id=int(row["id"]),
            filename=str(row["filename"]),
            user_id=row["user_id"],
            user_role=str(row["user_role"] or "student"),
            extracted_text=row["extracted_text"],
            sections_json=row["sections_json"],
            suggestions_json=row["suggestions_json"],
            created_at=str(row["created_at"]),
            updated_at=str(row["updated_at"]),
        )

    def get_sections(self, resume_id: int) -> Optional[Any]:
        record = self.get_record(resume_id)
        if record is None or not record.sections_json:
            return None
        return json.loads(record.sections_json)

    def get_extracted_text(self, resume_id: int) -> Optional[str]:
        record = self.get_record(resume_id)
        return None if record is None else record.extracted_text

    def get_suggestions(self, resume_id: int) -> Optional[Any]:
        record = self.get_record(resume_id)
        if record is None or not record.suggestions_json:
            return None
        return json.loads(record.suggestions_json)

    def create_job_profile(self, job_profile: Dict[str, Any]) -> int:
        with self._connect() as conn:
            job_profile_id = self._insert_and_get_id(
                conn,
                """
                INSERT INTO job_profiles(
                    title,
                    responsibilities,
                    must_haves_json,
                    nice_to_haves_json,
                    experience_years,
                    keywords_json
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    str(job_profile.get("title") or ""),
                    str(job_profile.get("responsibilities") or ""),
                    json.dumps(job_profile.get("must_haves") or [], ensure_ascii=False),
                    json.dumps(job_profile.get("nice_to_haves") or [], ensure_ascii=False),
                    str(job_profile.get("experience_years") or ""),
                    json.dumps(job_profile.get("keywords") or [], ensure_ascii=False),
                ),
            )
            conn.commit()
            return job_profile_id

    def set_match_result(
        self,
        resume_id: int,
        job_profile_id: int,
        status: str,
        match_score: int,
        result: Dict[str, Any],
    ) -> int:
        with self._connect() as conn:
            match_result_id = self._insert_and_get_id(
                conn,
                """
                INSERT INTO match_results(
                    resume_id,
                    job_profile_id,
                    status,
                    match_score,
                    result_json
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    resume_id,
                    job_profile_id,
                    status,
                    match_score,
                    json.dumps(result, ensure_ascii=False),
                ),
            )
            conn.commit()
            return match_result_id

    def count_resumes(self) -> int:
        with self._connect() as conn:
            row = self._fetchone(
                conn,
                """
                SELECT COUNT(*) AS total
                FROM resume_records
                WHERE extracted_text IS NOT NULL
                  AND TRIM(extracted_text) <> ''
                  AND sections_json IS NOT NULL
                  AND TRIM(sections_json) <> ''
                """
            )
        return int(row["total"] or 0)

    def count_users(self) -> int:
        with self._connect() as conn:
            row = self._fetchone(
                conn,
                """
                SELECT COUNT(DISTINCT COALESCE(NULLIF(TRIM(user_id), ''), filename)) AS total
                FROM resume_records
                """
            )
        return int(row["total"] or 0)

    def list_match_results(self) -> List[Dict[str, Any]]:
        with self._connect() as conn:
            rows = self._fetchall(
                conn,
                """
                SELECT
                    mr.id,
                    mr.resume_id,
                    mr.job_profile_id,
                    mr.status,
                    mr.match_score,
                    mr.result_json,
                    mr.created_at,
                    jp.title AS job_title
                FROM match_results mr
                JOIN job_profiles jp ON jp.id = mr.job_profile_id
                ORDER BY mr.created_at DESC
                """
            )

        results: List[Dict[str, Any]] = []
        for row in rows:
            try:
                result = json.loads(row["result_json"])
            except Exception:
                result = {}
            results.append(
                {
                    "id": int(row["id"]),
                    "resume_id": int(row["resume_id"]),
                    "job_profile_id": int(row["job_profile_id"]),
                    "job_title": str(row["job_title"] or "未命名岗位"),
                    "status": str(row["status"]),
                    "match_score": int(row["match_score"]),
                    "result": result,
                    "created_at": str(row["created_at"]),
                }
            )
        return results

    def log_ai_call(
        self,
        *,
        feature: str,
        endpoint: str,
        status: str,
        duration_ms: int = 0,
        error_message: str = "",
        user_id: Optional[str] = None,
        user_role: str = "student",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> int:
        with self._connect() as conn:
            log_id = self._insert_and_get_id(
                conn,
                """
                INSERT INTO ai_call_logs(
                    user_id,
                    user_role,
                    feature,
                    endpoint,
                    status,
                    duration_ms,
                    error_message,
                    metadata_json
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    user_id,
                    user_role,
                    feature,
                    endpoint,
                    status,
                    duration_ms,
                    error_message,
                    json.dumps(metadata or {}, ensure_ascii=False),
                ),
            )
            conn.commit()
            return log_id

    def list_ai_call_logs(self, limit: int = 100) -> List[Dict[str, Any]]:
        with self._connect() as conn:
            rows = self._fetchall(
                conn,
                """
                SELECT
                    id,
                    user_id,
                    user_role,
                    feature,
                    endpoint,
                    status,
                    duration_ms,
                    error_message,
                    metadata_json,
                    created_at
                FROM ai_call_logs
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (limit,),
            )

        logs: List[Dict[str, Any]] = []
        for row in rows:
            try:
                metadata = json.loads(row["metadata_json"] or "{}")
            except Exception:
                metadata = {}
            logs.append(
                {
                    "id": int(row["id"]),
                    "userId": str(row["user_id"] or ""),
                    "userRole": str(row["user_role"] or "student"),
                    "feature": str(row["feature"] or ""),
                    "endpoint": str(row["endpoint"] or ""),
                    "status": str(row["status"] or ""),
                    "durationMs": int(row["duration_ms"] or 0),
                    "errorMessage": str(row["error_message"] or ""),
                    "metadata": metadata,
                    "createdAt": str(row["created_at"] or ""),
                }
            )
        return logs

    def summarize_ai_calls(self) -> Dict[str, Any]:
        with self._connect() as conn:
            total_row = self._fetchone(
                conn,
                """
                SELECT
                    COUNT(*) AS total,
                    SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) AS success_total,
                    SUM(CASE WHEN status <> 'success' THEN 1 ELSE 0 END) AS failed_total
                FROM ai_call_logs
                """
            )
            feature_rows = self._fetchall(
                conn,
                """
                SELECT
                    feature,
                    COUNT(*) AS total,
                    SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) AS success_total,
                    SUM(CASE WHEN status <> 'success' THEN 1 ELSE 0 END) AS failed_total
                FROM ai_call_logs
                GROUP BY feature
                ORDER BY total DESC, feature ASC
                """
            )
            role_rows = self._fetchall(
                conn,
                """
                SELECT
                    user_role,
                    COUNT(*) AS total
                FROM ai_call_logs
                GROUP BY user_role
                ORDER BY total DESC, user_role ASC
                """
            )

        total = int((total_row or {}).get("total", 0) or 0)
        success_total = int((total_row or {}).get("success_total", 0) or 0)
        failed_total = int((total_row or {}).get("failed_total", 0) or 0)
        return {
            "total": total,
            "successTotal": success_total,
            "failedTotal": failed_total,
            "successRate": round(success_total / total * 100, 1) if total else 0,
            "featureBreakdown": [
                {
                    "feature": str(row["feature"] or ""),
                    "total": int(row["total"] or 0),
                    "successTotal": int(row["success_total"] or 0),
                    "failedTotal": int(row["failed_total"] or 0),
                }
                for row in feature_rows
            ],
            "roleBreakdown": [
                {
                    "role": str(row["user_role"] or "student"),
                    "total": int(row["total"] or 0),
                }
                for row in role_rows
            ],
        }
