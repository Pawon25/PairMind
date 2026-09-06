import sqlite3
from datetime import datetime, timezone
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent / "demo_requests.db"


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with _connect() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS demo_requests (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                name       TEXT NOT NULL,
                email      TEXT NOT NULL,
                message    TEXT,
                created_at TEXT NOT NULL,
                reviewed   INTEGER NOT NULL DEFAULT 0
            )
        """)


def save_request(name: str, email: str, message: str = ""):
    with _connect() as conn:
        conn.execute(
            "INSERT INTO demo_requests (name, email, message, created_at) VALUES (?, ?, ?, ?)",
            (name, email, message, datetime.now(timezone.utc).isoformat()),
        )


def list_requests(include_reviewed: bool = False) -> list[sqlite3.Row]:
    query = "SELECT * FROM demo_requests"
    if not include_reviewed:
        query += " WHERE reviewed = 0"
    query += " ORDER BY created_at ASC"
    with _connect() as conn:
        return conn.execute(query).fetchall()


def mark_reviewed(request_id: int):
    with _connect() as conn:
        conn.execute("UPDATE demo_requests SET reviewed = 1 WHERE id = ?", (request_id,))
