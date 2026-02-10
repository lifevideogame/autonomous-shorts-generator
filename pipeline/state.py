import sqlite3
from contextlib import contextmanager
from pipeline.config import DB_PATH

SCHEMA = """
CREATE TABLE IF NOT EXISTS videos (
    video_id TEXT PRIMARY KEY,
    creator_name TEXT NOT NULL,
    url TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'downloaded',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    error TEXT
);

CREATE TABLE IF NOT EXISTS moments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    video_id TEXT NOT NULL REFERENCES videos(video_id),
    moment_index INTEGER NOT NULL,
    start_sec REAL NOT NULL,
    end_sec REAL NOT NULL,
    title TEXT,
    reason TEXT,
    approved BOOLEAN DEFAULT NULL,
    refined_start REAL,
    refined_end REAL,
    s3_url TEXT
);
"""


def init_db():
    with get_db() as db:
        db.executescript(SCHEMA)


@contextmanager
def get_db():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def upsert_video(video_id: str, creator_name: str, url: str, status: str = "downloaded"):
    with get_db() as db:
        db.execute(
            """INSERT INTO videos (video_id, creator_name, url, status)
               VALUES (?, ?, ?, ?)
               ON CONFLICT(video_id) DO UPDATE SET status=excluded.status""",
            (video_id, creator_name, url, status),
        )


def update_video_status(video_id: str, status: str, error: str | None = None):
    with get_db() as db:
        db.execute(
            "UPDATE videos SET status=?, error=? WHERE video_id=?",
            (status, error, video_id),
        )


def get_video(video_id: str) -> dict | None:
    with get_db() as db:
        row = db.execute("SELECT * FROM videos WHERE video_id=?", (video_id,)).fetchone()
        return dict(row) if row else None


def get_videos_by_status(status: str) -> list[dict]:
    with get_db() as db:
        rows = db.execute("SELECT * FROM videos WHERE status=?", (status,)).fetchall()
        return [dict(r) for r in rows]


def get_all_videos() -> list[dict]:
    with get_db() as db:
        rows = db.execute("SELECT * FROM videos ORDER BY created_at DESC").fetchall()
        return [dict(r) for r in rows]


def insert_moments(video_id: str, moments: list[dict]):
    with get_db() as db:
        for i, m in enumerate(moments):
            db.execute(
                """INSERT INTO moments (video_id, moment_index, start_sec, end_sec, title, reason)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (video_id, i, m["start"], m["end"], m.get("title", ""), m.get("reason", "")),
            )


def get_moments(video_id: str) -> list[dict]:
    with get_db() as db:
        rows = db.execute(
            "SELECT * FROM moments WHERE video_id=? ORDER BY moment_index",
            (video_id,),
        ).fetchall()
        return [dict(r) for r in rows]


def update_moment_approval(moment_id: int, approved: bool, refined_start: float | None = None, refined_end: float | None = None):
    with get_db() as db:
        db.execute(
            "UPDATE moments SET approved=?, refined_start=?, refined_end=? WHERE id=?",
            (approved, refined_start, refined_end, moment_id),
        )


def update_moment_s3_url(moment_id: int, s3_url: str):
    with get_db() as db:
        db.execute("UPDATE moments SET s3_url=? WHERE id=?", (s3_url, moment_id))


def get_approved_moments(video_id: str) -> list[dict]:
    with get_db() as db:
        rows = db.execute(
            "SELECT * FROM moments WHERE video_id=? AND approved=1 ORDER BY moment_index",
            (video_id,),
        ).fetchall()
        return [dict(r) for r in rows]


def is_video_processed(video_id: str) -> bool:
    v = get_video(video_id)
    return v is not None and v["status"] in ("uploaded", "cleaned")
