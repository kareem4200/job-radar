import sqlite3
from pathlib import Path

from job_radar.config import DB_PATH
from job_radar.models import RawJob

SCHEMA = """
CREATE TABLE IF NOT EXISTS seen_jobs (
    fingerprint TEXT PRIMARY KEY,
    company TEXT NOT NULL,
    source TEXT NOT NULL,
    title TEXT NOT NULL,
    location TEXT,
    url TEXT,
    first_seen_at TEXT NOT NULL
);
"""


def _connect() -> sqlite3.Connection:
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute(SCHEMA)
    return conn


def has_any_seen() -> bool:
    """True if the store already has history. Used to detect a first/baseline run."""
    conn = _connect()
    try:
        cur = conn.execute("SELECT 1 FROM seen_jobs LIMIT 1")
        return cur.fetchone() is not None
    finally:
        conn.close()
        
def has_any_seen_for_company(company: str) -> bool:
    """True if THIS company has history. Used to baseline newly-enabled
    companies individually, so enabling 20 new companies at once doesn't
    alert on every currently-open role at all of them simultaneously."""
    conn = _connect()
    try:
        cur = conn.execute("SELECT 1 FROM seen_jobs WHERE company = ? LIMIT 1", (company,))
        return cur.fetchone() is not None
    finally:
        conn.close()


def is_new(fingerprint: str) -> bool:
    conn = _connect()
    try:
        cur = conn.execute("SELECT 1 FROM seen_jobs WHERE fingerprint = ?", (fingerprint,))
        return cur.fetchone() is None
    finally:
        conn.close()


def mark_seen(job: RawJob, seen_at: str) -> None:
    conn = _connect()
    try:
        conn.execute(
            "INSERT OR IGNORE INTO seen_jobs "
            "(fingerprint, company, source, title, location, url, first_seen_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                job.fingerprint,
                job.company,
                job.source,
                job.title,
                job.location,
                job.url,
                seen_at,
            ),
        )
        conn.commit()
    finally:
        conn.close()
