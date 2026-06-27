"""SQLite content store with WAL mode for safe concurrent access."""

from __future__ import annotations

import json
import os
import sqlite3
import threading
import uuid
from pathlib import Path
from typing import Any

_DEFAULT_DB_DIR = Path(__file__).parent.parent / "data"
DB_PATH = Path(os.environ.get("DB_DIR", str(_DEFAULT_DB_DIR))) / "content.db"

_local = threading.local()


def _get_conn() -> sqlite3.Connection:
    """Return a thread-local connection with WAL mode enabled."""
    conn = getattr(_local, "conn", None)
    if conn is None:
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=5000")
        conn.row_factory = sqlite3.Row
        _local.conn = conn
    return conn


def init_db() -> None:
    """Create the content and session_log tables if they don't exist."""
    conn = _get_conn()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS game_content (
            id      INTEGER PRIMARY KEY AUTOINCREMENT,
            game    TEXT NOT NULL,
            pool    TEXT NOT NULL DEFAULT 'normal',
            content TEXT NOT NULL
        )
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_game_pool ON game_content(game, pool)
    """)
    # Migrate: drop old session_log if it has PII columns (player, ip)
    cols = {r[1] for r in conn.execute("PRAGMA table_info(session_log)").fetchall()}
    if "player" in cols or "ip" in cols:
        conn.execute("DROP TABLE session_log")

    conn.execute("""
        CREATE TABLE IF NOT EXISTS session_log (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            anon_id    TEXT NOT NULL,
            room_code  TEXT NOT NULL,
            device     TEXT NOT NULL DEFAULT '',
            joined_at  TEXT NOT NULL DEFAULT (datetime('now')),
            is_host    INTEGER NOT NULL DEFAULT 0
        )
    """)
    conn.commit()


def get_content(game: str, pool: str = "normal") -> list[Any]:
    """Fetch all content items for a game+pool. Returns parsed JSON objects."""
    conn = _get_conn()
    rows = conn.execute(
        "SELECT content FROM game_content WHERE game = ? AND pool = ?",
        (game, pool),
    ).fetchall()
    return [json.loads(r["content"]) for r in rows]


def add_content(game: str, pool: str, items: list[Any]) -> int:
    """Insert content items. Returns count inserted."""
    conn = _get_conn()
    rows = [(game, pool, json.dumps(item)) for item in items]
    conn.executemany(
        "INSERT INTO game_content (game, pool, content) VALUES (?, ?, ?)",
        rows,
    )
    conn.commit()
    return len(rows)


def replace_content(game: str, pool: str, items: list[Any]) -> int:
    """Replace all content for a game+pool. Returns count inserted."""
    conn = _get_conn()
    conn.execute(
        "DELETE FROM game_content WHERE game = ? AND pool = ?",
        (game, pool),
    )
    rows = [(game, pool, json.dumps(item)) for item in items]
    conn.executemany(
        "INSERT INTO game_content (game, pool, content) VALUES (?, ?, ?)",
        rows,
    )
    conn.commit()
    return len(rows)


def delete_content(game: str, pool: str | None = None) -> int:
    """Delete content. If pool is None, delete all pools for the game."""
    conn = _get_conn()
    if pool:
        cur = conn.execute(
            "DELETE FROM game_content WHERE game = ? AND pool = ?",
            (game, pool),
        )
    else:
        cur = conn.execute(
            "DELETE FROM game_content WHERE game = ?",
            (game,),
        )
    conn.commit()
    return cur.rowcount


def count_content(game: str | None = None) -> dict[str, dict[str, int]]:
    """Return content counts grouped by game and pool."""
    conn = _get_conn()
    if game:
        rows = conn.execute(
            "SELECT game, pool, COUNT(*) as cnt FROM game_content WHERE game = ? GROUP BY game, pool",
            (game,),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT game, pool, COUNT(*) as cnt FROM game_content GROUP BY game, pool"
        ).fetchall()
    result: dict[str, dict[str, int]] = {}
    for r in rows:
        result.setdefault(r["game"], {})[r["pool"]] = r["cnt"]
    return result


def _parse_device(ua: str) -> str:
    """Extract a short device description from a User-Agent string (no PII)."""
    if not ua:
        return "unknown"
    ua_lower = ua.lower()
    if "iphone" in ua_lower:
        return "iPhone"
    if "ipad" in ua_lower:
        return "iPad"
    if "android" in ua_lower:
        return "Android"
    if "macintosh" in ua_lower or "mac os" in ua_lower:
        return "Mac"
    if "windows" in ua_lower:
        return "Windows"
    if "linux" in ua_lower:
        return "Linux"
    if "cros" in ua_lower:
        return "ChromeOS"
    return "other"


def log_session(room_code: str, user_agent: str, is_host: bool) -> str:
    """Log a session join. Returns the generated anon_id."""
    anon_id = uuid.uuid4().hex[:12]
    device = _parse_device(user_agent)
    conn = _get_conn()
    conn.execute(
        "INSERT INTO session_log (anon_id, room_code, device, is_host) VALUES (?, ?, ?, ?)",
        (anon_id, room_code, device, 1 if is_host else 0),
    )
    conn.commit()
    return anon_id


def get_sessions(limit: int = 100) -> list[dict]:
    conn = _get_conn()
    rows = conn.execute(
        "SELECT id, anon_id, room_code, device, joined_at, is_host FROM session_log ORDER BY id DESC LIMIT ?",
        (limit,),
    ).fetchall()
    return [dict(r) for r in rows]


def is_seeded() -> bool:
    """Check if the DB has any content."""
    conn = _get_conn()
    row = conn.execute("SELECT COUNT(*) as cnt FROM game_content").fetchone()
    return row["cnt"] > 0


CONTENT_DIR = Path(__file__).parent.parent / "content"


def _load_txt(filepath: Path) -> list[str]:
    """Load a plain-text file as a list of non-empty lines."""
    return [line for line in filepath.read_text().strip().split("\n") if line.strip()]


def _load_txt_pairs(filepath: Path) -> list[list[str]]:
    """Load tab-separated pairs from a text file."""
    pairs = []
    for line in filepath.read_text().strip().split("\n"):
        if "\t" in line:
            pairs.append(line.split("\t", 1))
    return pairs


def _load_jsonl(filepath: Path) -> list[Any]:
    """Load a JSONL file as a list of parsed objects."""
    return [json.loads(line) for line in filepath.read_text().strip().split("\n") if line.strip()]


def seed_from_game_data() -> None:
    """Populate DB from content/ text files (only if empty)."""
    if is_seeded():
        return

    for f in sorted(CONTENT_DIR.iterdir()):
        stem = f.stem  # e.g. "truths_normal", "trivia_spicy"
        parts = stem.rsplit("_", 1)
        if len(parts) != 2:
            continue
        game, pool = parts

        if f.suffix == ".jsonl":
            items = _load_jsonl(f)
        elif game == "would_you_rather":
            items = _load_txt_pairs(f)
        else:
            items = _load_txt(f)

        if items:
            add_content(game, pool, items)
