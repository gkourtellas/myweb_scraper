import os
import sqlite3
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_FILE = os.path.join(BASE_DIR, "app.db")


def get_conn():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_conn()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            created_at TEXT NOT NULL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS favorites (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            tip_key TEXT NOT NULL,
            tip_text TEXT,
            site TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id),
            UNIQUE(user_id, tip_key)
        )
    """)
    conn.commit()
    conn.close()


def get_or_create_user(name):
    conn = get_conn()
    row = conn.execute("SELECT * FROM users WHERE name = ?", (name,)).fetchone()
    if row:
        conn.close()
        return dict(row)
    now = datetime.utcnow().isoformat()
    cur = conn.execute("INSERT INTO users (name, created_at) VALUES (?, ?)", (name, now))
    conn.commit()
    user_id = cur.lastrowid
    conn.close()
    return {"id": user_id, "name": name, "created_at": now}


def list_favorites(user_id):
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM favorites WHERE user_id = ? ORDER BY created_at DESC", (user_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def add_favorite(user_id, tip_key, tip_text=None, site=None):
    conn = get_conn()
    now = datetime.utcnow().isoformat()
    try:
        conn.execute(
            "INSERT OR IGNORE INTO favorites (user_id, tip_key, tip_text, site, created_at) VALUES (?, ?, ?, ?, ?)",
            (user_id, tip_key, tip_text, site, now),
        )
        conn.commit()
    finally:
        conn.close()
    return True


def remove_favorite(user_id, tip_key):
    conn = get_conn()
    conn.execute("DELETE FROM favorites WHERE user_id = ? AND tip_key = ?", (user_id, tip_key))
    conn.commit()
    conn.close()
    return True


init_db()
