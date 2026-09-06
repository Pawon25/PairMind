import secrets
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "tokens.db"


class TokenError(Exception):
    """Raised with a specific reason so callers can return the right 401 message."""


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with _connect() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS tokens (
                token          TEXT PRIMARY KEY,
                note           TEXT,
                created_at     TEXT NOT NULL,
                expires_at     TEXT NOT NULL,
                uses_remaining INTEGER NOT NULL
            )
        """)


def issue_token(note: str, expires_days: int = 7, uses: int = 3) -> str:
    token = secrets.token_urlsafe(24)
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(days=expires_days)
    with _connect() as conn:
        conn.execute(
            "INSERT INTO tokens (token, note, created_at, expires_at, uses_remaining) VALUES (?, ?, ?, ?, ?)",
            (token, note, now.isoformat(), expires_at.isoformat(), uses),
        )
    return token


def list_tokens() -> list[sqlite3.Row]:
    with _connect() as conn:
        return conn.execute("SELECT * FROM tokens ORDER BY created_at DESC").fetchall()


def check_token(token: str) -> sqlite3.Row:
    """Validate a token without consuming a use (existence + expiry only).
    Raises TokenError with a specific reason. Used for the initial gate check
    and for /upload, which shouldn't burn negotiation quota just to stage docs.
    """
    with _connect() as conn:
        row = conn.execute("SELECT * FROM tokens WHERE token = ?", (token,)).fetchone()
    if row is None:
        raise TokenError("Invalid token")
    if datetime.fromisoformat(row["expires_at"]) < datetime.now(timezone.utc):
        raise TokenError("Token expired")
    return row


def consume_negotiation(token: str) -> sqlite3.Row:
    """Validate + decrement uses_remaining by one. Used only by /negotiate,
    the actual Claude-calling endpoint - this is what the usage cap protects.
    """
    row = check_token(token)
    if row["uses_remaining"] <= 0:
        raise TokenError("Token usage limit reached")
    with _connect() as conn:
        conn.execute(
            "UPDATE tokens SET uses_remaining = uses_remaining - 1 WHERE token = ?",
            (token,),
        )
    return row
