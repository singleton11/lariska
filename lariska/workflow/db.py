from __future__ import annotations

import sqlite3
from pathlib import Path

_DB_DIR = Path.home() / ".lariska" / "data"
_DB_FILE = _DB_DIR / "tasks.db"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS tasks (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    card_id     TEXT    NOT NULL UNIQUE,
    state       TEXT    NOT NULL DEFAULT 'ready',
    created_at  TEXT    NOT NULL DEFAULT (datetime('now')),
    updated_at  TEXT    NOT NULL DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS list_id_cache (
    board_id        TEXT    NOT NULL PRIMARY KEY,
    list_name_hash  TEXT    NOT NULL,
    list_id         TEXT    NOT NULL
);
"""


def get_db_path() -> Path:
    return _DB_FILE


def init_db(db_path: str | Path | None = None) -> sqlite3.Connection:
    """Open (and initialise if necessary) the SQLite database.

    Returns an open :class:`sqlite3.Connection`.  The caller is responsible for
    closing it.
    """
    path = Path(db_path) if db_path is not None else _DB_FILE
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.executescript(_SCHEMA)
    conn.commit()
    return conn


def create_task(conn: sqlite3.Connection, card_id: str, state: str = "ready") -> int:
    """Insert a new task row and return its auto-generated *id*.

    If a task for *card_id* already exists the existing row is returned
    unchanged (idempotent).
    """
    conn.execute(
        "INSERT OR IGNORE INTO tasks (card_id, state) VALUES (?, ?)",
        (card_id, state),
    )
    conn.commit()
    row = conn.execute("SELECT id FROM tasks WHERE card_id = ?", (card_id,)).fetchone()
    return int(row["id"])


def get_task_by_card_id(conn: sqlite3.Connection, card_id: str) -> sqlite3.Row | None:
    """Return the task row for *card_id*, or ``None`` if not found."""
    return conn.execute(
        "SELECT * FROM tasks WHERE card_id = ?", (card_id,)
    ).fetchone()


def get_cached_list_id(
    conn: sqlite3.Connection, board_id: str, list_name_hash: str
) -> str | None:
    """Return the cached list ID for *board_id* if *list_name_hash* matches.

    Returns ``None`` when there is no cached entry or when the stored hash does
    not match *list_name_hash* (i.e. the configured list name has changed).
    """
    row = conn.execute(
        "SELECT list_id FROM list_id_cache WHERE board_id = ? AND list_name_hash = ?",
        (board_id, list_name_hash),
    ).fetchone()
    return row["list_id"] if row is not None else None


def set_cached_list_id(
    conn: sqlite3.Connection, board_id: str, list_name_hash: str, list_id: str
) -> None:
    """Upsert the list ID cache entry for *board_id*.

    If an entry for *board_id* already exists it is overwritten with the new
    *list_name_hash* and *list_id* values, which effectively invalidates any
    previously cached value for a different list name.
    """
    conn.execute(
        "INSERT INTO list_id_cache (board_id, list_name_hash, list_id) VALUES (?, ?, ?)"
        " ON CONFLICT(board_id) DO UPDATE SET"
        "   list_name_hash = excluded.list_name_hash,"
        "   list_id = excluded.list_id",
        (board_id, list_name_hash, list_id),
    )
    conn.commit()
