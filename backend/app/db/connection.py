import os
import sqlite3
from contextlib import contextmanager
from typing import Any, Iterator, Optional
from urllib.parse import parse_qsl, quote, urlencode, urlparse, urlunparse


try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
    from psycopg2.pool import ThreadedConnectionPool
except ImportError:
    psycopg2 = None  # type: ignore[assignment]
    RealDictCursor = None  # type: ignore[assignment]
    ThreadedConnectionPool = None  # type: ignore[assignment]


_POSTGRES_POOL: Optional["ThreadedConnectionPool"] = None


def database_url() -> str:
    return (
        os.getenv("SUPABASE_DATABASE_URL")
        or os.getenv("DATABASE_URL")
        or os.getenv("POSTGRES_URL")
        or ""
    ).strip()


def using_postgres() -> bool:
    url = database_url().lower()
    return url.startswith("postgres://") or url.startswith("postgresql://")


def postgres_dsn() -> str:
    url = database_url()
    if not url:
        raise RuntimeError("SUPABASE_DATABASE_URL or DATABASE_URL is required for Postgres")

    parsed = urlparse(url)
    query = dict(parse_qsl(parsed.query, keep_blank_values=True))
    query.setdefault("sslmode", "require")
    return urlunparse(parsed._replace(query=urlencode(query)))


def postgres_pool_min_conn() -> int:
    return max(1, int(os.getenv("POSTGRES_POOL_MIN_CONN", "1")))


def postgres_pool_max_conn() -> int:
    return max(postgres_pool_min_conn(), int(os.getenv("POSTGRES_POOL_MAX_CONN", "5")))


def sqlite_db_path(db_path: Optional[str] = None) -> str:
    return db_path or os.getenv(
        "RESUME_DB_PATH",
        os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            "data",
            "resume.db",
        ),
    )


def encode_database_password(password: str) -> str:
    return quote(password, safe="")


def get_postgres_pool() -> "ThreadedConnectionPool":
    global _POSTGRES_POOL

    if psycopg2 is None or ThreadedConnectionPool is None:
        raise RuntimeError(
            "Postgres database URL is configured, but psycopg2 is not installed. "
            "Run: pip install -r requirements.txt"
        )

    if _POSTGRES_POOL is None:
        _POSTGRES_POOL = ThreadedConnectionPool(
            minconn=postgres_pool_min_conn(),
            maxconn=postgres_pool_max_conn(),
            dsn=postgres_dsn(),
        )
    return _POSTGRES_POOL


def close_postgres_pool() -> None:
    global _POSTGRES_POOL

    if _POSTGRES_POOL is not None:
        _POSTGRES_POOL.closeall()
        _POSTGRES_POOL = None


@contextmanager
def postgres_connection() -> Iterator[Any]:
    pool = get_postgres_pool()
    conn = pool.getconn()
    try:
        yield conn
    finally:
        pool.putconn(conn)


@contextmanager
def postgres_cursor(conn: Any) -> Iterator[Any]:
    if RealDictCursor is None:
        raise RuntimeError(
            "Postgres database URL is configured, but psycopg2 extras are not available. "
            "Run: pip install -r requirements.txt"
        )

    cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
        yield cur
    finally:
        cur.close()


@contextmanager
def database_connection(db_path: Optional[str] = None) -> Iterator[Any]:
    if using_postgres():
        with postgres_connection() as conn:
            yield conn
        return

    conn = sqlite3.connect(sqlite_db_path(db_path))
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()
