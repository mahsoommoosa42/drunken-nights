"""SQLite content store with WAL mode for safe concurrent access."""

from __future__ import annotations

import json
import sqlite3
import threading
from pathlib import Path
from typing import Any

DB_PATH = Path(__file__).parent.parent / "data" / "content.db"

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
    """Create the content table if it doesn't exist."""
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


def is_seeded() -> bool:
    """Check if the DB has any content."""
    conn = _get_conn()
    row = conn.execute("SELECT COUNT(*) as cnt FROM game_content").fetchone()
    return row["cnt"] > 0


def seed_from_game_data() -> None:
    """Populate DB from the game_data module (only if empty)."""
    if is_seeded():
        return

    from app.game_data import (
        TRUTHS, DARES, NEVER_HAVE_I_EVER, WOULD_YOU_RATHER,
        MOST_LIKELY_TO, CATEGORIES, TRIVIA, HOT_TAKES,
        TABOO_WORDS, TWO_TRUTHS_PROMPTS, RHYME_STARTERS,
        WORD_ASSOCIATION_STARTERS,
        TRUTHS_SPICY, DARES_SPICY, NEVER_HAVE_I_EVER_SPICY,
        WOULD_YOU_RATHER_SPICY, MOST_LIKELY_TO_SPICY, CATEGORIES_SPICY,
        HOT_TAKES_SPICY, TABOO_WORDS_SPICY, TWO_TRUTHS_PROMPTS_SPICY,
        RHYME_STARTERS_SPICY, WORD_ASSOCIATION_STARTERS_SPICY,
    )

    # Normal pools
    content_map = {
        "truths": TRUTHS,
        "dares": DARES,
        "never_have_i_ever": NEVER_HAVE_I_EVER,
        "would_you_rather": [list(pair) for pair in WOULD_YOU_RATHER],
        "most_likely_to": MOST_LIKELY_TO,
        "categories": CATEGORIES,
        "trivia": TRIVIA,
        "hot_takes": HOT_TAKES,
        "taboo": TABOO_WORDS,
        "two_truths": TWO_TRUTHS_PROMPTS,
        "rhyme_starters": RHYME_STARTERS,
        "word_association": WORD_ASSOCIATION_STARTERS,
    }

    # Spicy pools
    spicy_map = {
        "truths": TRUTHS_SPICY,
        "dares": DARES_SPICY,
        "never_have_i_ever": NEVER_HAVE_I_EVER_SPICY,
        "would_you_rather": [list(pair) for pair in WOULD_YOU_RATHER_SPICY],
        "most_likely_to": MOST_LIKELY_TO_SPICY,
        "categories": CATEGORIES_SPICY,
        "hot_takes": HOT_TAKES_SPICY,
        "taboo": TABOO_WORDS_SPICY,
        "two_truths": TWO_TRUTHS_PROMPTS_SPICY,
        "rhyme_starters": RHYME_STARTERS_SPICY,
        "word_association": WORD_ASSOCIATION_STARTERS_SPICY,
    }

    for game, items in content_map.items():
        add_content(game, "normal", items)

    for game, items in spicy_map.items():
        add_content(game, "spicy", items)
