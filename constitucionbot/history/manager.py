from __future__ import annotations

import os
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "historial" / "chat.db"
MAX_DB_SIZE_BYTES = 1 * 1024 * 1024 * 1024
MAX_HISTORY_CHARS = 6000
MAX_HISTORY_MESSAGES = 2


def _ensure_db() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    if not DB_PATH.exists():
        conn = sqlite3.connect(DB_PATH)
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS chat_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL
            )
            """
        )
        conn.commit()
        conn.close()

    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS chat_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL
        )
        """
    )
    conn.commit()
    return conn


def reset_history() -> None:
    conn = _ensure_db()
    conn.execute("DELETE FROM chat_history")
    conn.commit()
    conn.close()


def load_history(user_id: Optional[str] = None) -> List[Dict[str, Any]]:
    conn = _ensure_db()
    try:
        if user_id is None:
            rows = conn.execute(
                "SELECT role, content FROM chat_history ORDER BY id ASC"
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT role, content FROM chat_history WHERE user_id = ? ORDER BY id ASC",
                (user_id,),
            ).fetchall()

        history = [{"role": role, "content": content} for role, content in rows]
        return _trim_history_to_limit(history)
    finally:
        conn.close()


def save_history(history: List[Dict[str, Any]], user_id: Optional[str] = None) -> None:
    conn = _ensure_db()
    try:
        conn.execute("DELETE FROM chat_history")
        if user_id is not None:
            for entry in history:
                conn.execute(
                    "INSERT INTO chat_history (user_id, role, content) VALUES (?, ?, ?)",
                    (user_id, entry["role"], entry["content"]),
                )
        else:
            for entry in history:
                conn.execute(
                    "INSERT INTO chat_history (user_id, role, content) VALUES (?, ?, ?)",
                    ("", entry["role"], entry["content"]),
                )
        conn.commit()
    finally:
        conn.close()


def append_interaction(question: str, answer: str, user_id: Optional[str] = None) -> None:
    if user_id is None:
        user_id = os.getenv("DEFAULT_USER_ID", "default")

    conn = _ensure_db()
    try:
        conn.execute(
            "INSERT INTO chat_history (user_id, role, content) VALUES (?, ?, ?)",
            (user_id, "user", question),
        )
        conn.execute(
            "INSERT INTO chat_history (user_id, role, content) VALUES (?, ?, ?)",
            (user_id, "assistant", answer),
        )
        conn.commit()
        _clear_history_if_database_is_oversized(conn)
    finally:
        conn.close()


def _clear_history_if_database_is_oversized(conn: sqlite3.Connection) -> None:
    if not DB_PATH.exists() or DB_PATH.stat().st_size <= MAX_DB_SIZE_BYTES:
        return

    conn.execute("DELETE FROM chat_history")
    conn.commit()
    conn.execute("VACUUM")


def _trim_history_to_limit(history: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    if not history:
        return []

    if len(history) <= MAX_HISTORY_MESSAGES:
        text = "\n".join(f"{entry['role']}: {entry['content']}" for entry in history)
        if len(text) <= MAX_HISTORY_CHARS:
            return history

    trimmed = history[-MAX_HISTORY_MESSAGES:]
    text = "\n".join(f"{entry['role']}: {entry['content']}" for entry in trimmed)

    if len(text) <= MAX_HISTORY_CHARS:
        return trimmed

    final_trimmed: List[Dict[str, Any]] = []
    current_chars = 0
    for entry in reversed(trimmed):
        candidate = f"{entry['role']}: {entry['content']}"
        if current_chars + len(candidate) + 1 > MAX_HISTORY_CHARS:
            continue
        final_trimmed.append(entry)
        current_chars += len(candidate) + 1

    final_trimmed.reverse()
    return final_trimmed
