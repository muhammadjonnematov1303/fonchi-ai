import os
import sqlite3
from datetime import datetime, timezone

DB_PATH = "/tmp/database.db" if os.environ.get("VERCEL") else "database.db"


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id       INTEGER PRIMARY KEY,
                username      TEXT,
                full_name     TEXT,
                first_free_used INTEGER DEFAULT 0,
                subscription_until TEXT DEFAULT NULL,
                is_blocked    INTEGER DEFAULT 0,
                created_at    TEXT DEFAULT (datetime('now'))
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS payments (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id       INTEGER,
                status        TEXT DEFAULT 'pending',
                receipt_file_id TEXT,
                created_at    TEXT DEFAULT (datetime('now')),
                updated_at    TEXT DEFAULT (datetime('now'))
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS user_states (
                user_id       INTEGER PRIMARY KEY,
                state         TEXT,
                photo_file_id TEXT
            )
        """)


def get_user(user_id: int):
    with get_conn() as conn:
        return conn.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)).fetchone()


def upsert_user(user_id: int, username: str, full_name: str):
    with get_conn() as conn:
        conn.execute("""
            INSERT INTO users (user_id, username, full_name)
            VALUES (?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                username = excluded.username,
                full_name = excluded.full_name
        """, (user_id, username, full_name))


def is_blocked(user_id: int) -> bool:
    user = get_user(user_id)
    return bool(user and user["is_blocked"])


def has_access(user_id: int, username: str = "") -> bool:
    from config import ADMIN_ID, ADMIN_USERNAMES
    # Admin va whitelist userlar — cheksiz, blok ham ta'sir qilmaydi
    if user_id == ADMIN_ID:
        return True
    if username and username.lower() in ADMIN_USERNAMES:
        return True

    user = get_user(user_id)
    if not user:
        return False
    if user["is_blocked"]:
        return False
    if not user["first_free_used"]:
        return True
    if user["subscription_until"]:
        until = datetime.fromisoformat(user["subscription_until"])
        if until.tzinfo is None:
            until = until.replace(tzinfo=timezone.utc)
        return datetime.now(timezone.utc) < until
    return False


def mark_free_used(user_id: int):
    with get_conn() as conn:
        conn.execute("UPDATE users SET first_free_used = 1 WHERE user_id = ?", (user_id,))


def grant_subscription(user_id: int, days: int = 1):
    from datetime import timedelta
    now = datetime.now(timezone.utc)
    user = get_user(user_id)
    if user and user["subscription_until"]:
        current = datetime.fromisoformat(user["subscription_until"])
        if current.tzinfo is None:
            current = current.replace(tzinfo=timezone.utc)
        base = max(now, current)
    else:
        base = now
    until = (base + timedelta(days=days)).isoformat()
    with get_conn() as conn:
        conn.execute(
            "UPDATE users SET subscription_until = ?, first_free_used = 1 WHERE user_id = ?",
            (until, user_id)
        )


def block_user(user_id: int):
    with get_conn() as conn:
        conn.execute("UPDATE users SET is_blocked = 1 WHERE user_id = ?", (user_id,))


def unblock_user(user_id: int):
    with get_conn() as conn:
        conn.execute("UPDATE users SET is_blocked = 0 WHERE user_id = ?", (user_id,))


def create_payment(user_id: int, receipt_file_id: str) -> int:
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO payments (user_id, receipt_file_id) VALUES (?, ?)",
            (user_id, receipt_file_id)
        )
        return cur.lastrowid


def update_payment(payment_id: int, status: str):
    with get_conn() as conn:
        conn.execute(
            "UPDATE payments SET status = ?, updated_at = datetime('now') WHERE id = ?",
            (status, payment_id)
        )


def get_pending_payment(user_id: int):
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM payments WHERE user_id = ? AND status = 'pending' ORDER BY id DESC LIMIT 1",
            (user_id,)
        ).fetchone()


def set_state(user_id: int, state: str, photo_file_id: str = None):
    with get_conn() as conn:
        conn.execute("""
            INSERT INTO user_states (user_id, state, photo_file_id)
            VALUES (?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET state = excluded.state, photo_file_id = excluded.photo_file_id
        """, (user_id, state, photo_file_id))


def get_state(user_id: int):
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM user_states WHERE user_id = ?", (user_id,)).fetchone()
        if row:
            return row["state"], row["photo_file_id"]
        return None, None


def clear_state(user_id: int):
    with get_conn() as conn:
        conn.execute("DELETE FROM user_states WHERE user_id = ?", (user_id,))


def get_stats():
    with get_conn() as conn:
        total = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        active = conn.execute(
            "SELECT COUNT(*) FROM users WHERE subscription_until > datetime('now')"
        ).fetchone()[0]
        today_payments = conn.execute(
            "SELECT COUNT(*) FROM payments WHERE status = 'approved' AND DATE(updated_at) = DATE('now')"
        ).fetchone()[0]
        return total, active, today_payments


def get_all_users():
    with get_conn() as conn:
        return conn.execute("SELECT * FROM users ORDER BY created_at DESC").fetchall()
