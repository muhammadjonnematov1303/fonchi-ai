import os
import sqlite3
from datetime import datetime, timezone

DB_PATH = "database.db"


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id            INTEGER PRIMARY KEY,
                username           TEXT,
                full_name          TEXT,
                phone              TEXT DEFAULT NULL,
                balance            INTEGER DEFAULT 0,
                first_free_used    INTEGER DEFAULT 0,
                is_blocked         INTEGER DEFAULT 0,
                created_at         TEXT DEFAULT (datetime('now'))
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS payments (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id         INTEGER,
                amount          INTEGER DEFAULT 0,
                status          TEXT DEFAULT 'pending',
                receipt_file_id TEXT,
                created_at      TEXT DEFAULT (datetime('now')),
                updated_at      TEXT DEFAULT (datetime('now'))
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS user_states (
                user_id       INTEGER PRIMARY KEY,
                state         TEXT,
                photo_file_id TEXT
            )
        """)
        # Eski DB ga yangi ustunlar qo'shish
        for col, definition in [
            ("phone",           "TEXT DEFAULT NULL"),
            ("balance",         "INTEGER DEFAULT 0"),
            ("first_free_used", "INTEGER DEFAULT 0"),
        ]:
            try:
                conn.execute(f"ALTER TABLE users ADD COLUMN {col} {definition}")
            except Exception:
                pass
        try:
            conn.execute("ALTER TABLE payments ADD COLUMN amount INTEGER DEFAULT 0")
        except Exception:
            pass


def get_user(user_id: int):
    with get_conn() as conn:
        return conn.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)).fetchone()


def upsert_user(user_id: int, username: str, full_name: str):
    with get_conn() as conn:
        conn.execute("""
            INSERT INTO users (user_id, username, full_name)
            VALUES (?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                username  = excluded.username,
                full_name = excluded.full_name
        """, (user_id, username, full_name))


def is_registered(user_id: int) -> bool:
    return get_user(user_id) is not None


def save_phone(user_id: int, phone: str):
    with get_conn() as conn:
        conn.execute("UPDATE users SET phone = ? WHERE user_id = ?", (phone, user_id))


def is_blocked(user_id: int) -> bool:
    user = get_user(user_id)
    return bool(user and user["is_blocked"])


def get_balance(user_id: int) -> int:
    user = get_user(user_id)
    return int(user["balance"]) if user else 0


def add_balance(user_id: int, amount: int):
    with get_conn() as conn:
        conn.execute(
            "UPDATE users SET balance = balance + ? WHERE user_id = ?",
            (amount, user_id)
        )


def deduct_balance(user_id: int, amount: int) -> bool:
    user = get_user(user_id)
    if not user or user["balance"] < amount:
        return False
    with get_conn() as conn:
        conn.execute(
            "UPDATE users SET balance = balance - ? WHERE user_id = ?",
            (amount, user_id)
        )
    return True


def has_access(user_id: int, username: str = "") -> bool:
    from config import ADMIN_ID, ADMIN_USERNAMES, COST_PER_IMAGE
    if user_id == ADMIN_ID:
        return True
    if username and username.lower() in ADMIN_USERNAMES:
        return True
    user = get_user(user_id)
    if not user or user["is_blocked"]:
        return False
    if not user["first_free_used"]:
        return True
    return int(user["balance"]) >= COST_PER_IMAGE


def mark_free_used(user_id: int):
    from config import COST_PER_IMAGE
    from config import ADMIN_ID
    user = get_user(user_id)
    if not user:
        return
    if user["first_free_used"]:
        # Balansdan ayirish
        with get_conn() as conn:
            conn.execute(
                "UPDATE users SET balance = MAX(0, balance - ?) WHERE user_id = ?",
                (COST_PER_IMAGE, user_id)
            )
    else:
        with get_conn() as conn:
            conn.execute(
                "UPDATE users SET first_free_used = 1 WHERE user_id = ?",
                (user_id,)
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


def set_state(user_id: int, state: str, photo_file_id: str = None):
    with get_conn() as conn:
        conn.execute("""
            INSERT INTO user_states (user_id, state, photo_file_id)
            VALUES (?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                state         = excluded.state,
                photo_file_id = excluded.photo_file_id
        """, (user_id, state, photo_file_id))


def get_state(user_id: int):
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM user_states WHERE user_id = ?", (user_id,)
        ).fetchone()
        if row:
            return row["state"], row["photo_file_id"]
        return None, None


def clear_state(user_id: int):
    with get_conn() as conn:
        conn.execute("DELETE FROM user_states WHERE user_id = ?", (user_id,))


def get_stats():
    with get_conn() as conn:
        total = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        with_balance = conn.execute(
            "SELECT COUNT(*) FROM users WHERE balance > 0"
        ).fetchone()[0]
        today_payments = conn.execute(
            "SELECT COUNT(*) FROM payments WHERE status = 'approved' AND DATE(updated_at) = DATE('now')"
        ).fetchone()[0]
        return total, with_balance, today_payments


def get_all_users():
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM users ORDER BY created_at DESC"
        ).fetchall()