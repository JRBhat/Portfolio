"""SQLite storage layer — schema creation, writes, and read queries."""
from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

from .models import InputBucket

# ── Schema ────────────────────────────────────────────────────────────────────

_SCHEMA = """
PRAGMA journal_mode=WAL;
PRAGMA synchronous=NORMAL;

CREATE TABLE IF NOT EXISTS window_sessions (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    date         TEXT NOT NULL,          -- ISO date "YYYY-MM-DD"
    start_ts     REAL NOT NULL,          -- Unix timestamp (float)
    end_ts       REAL,                   -- NULL while the session is still open
    exe_name     TEXT NOT NULL,
    window_title TEXT NOT NULL,
    category     TEXT NOT NULL           -- work | leisure | system | unknown
);

CREATE TABLE IF NOT EXISTS input_events (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    bucket_ts      REAL NOT NULL,        -- start of the 60-second bucket
    date           TEXT NOT NULL,
    key_count      INTEGER NOT NULL DEFAULT 0,
    mouse_clicks   INTEGER NOT NULL DEFAULT 0,
    mouse_distance REAL    NOT NULL DEFAULT 0.0
);

CREATE TABLE IF NOT EXISTS idle_periods (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    date         TEXT NOT NULL,
    start_ts     REAL NOT NULL,
    end_ts       REAL,                   -- NULL while still idle
    duration_sec REAL                    -- filled when end_ts is set
);

CREATE INDEX IF NOT EXISTS idx_ws_date ON window_sessions(date);
CREATE INDEX IF NOT EXISTS idx_ie_date ON input_events(date);
CREATE INDEX IF NOT EXISTS idx_ip_date ON idle_periods(date);
"""


class Database:
    """
    All SQLite access for the activity tracker.

    Writer interface (open_session, close_session, …) must only be called from
    the DatabaseWriter thread after connect_writer() has been called once.

    Reader interface (query_*) opens a fresh connection each time and is safe
    to call from any thread, including the main/report thread.
    """

    def __init__(self, db_path: Path) -> None:
        self._path = db_path
        self._conn: sqlite3.Connection | None = None   # writer thread only

    # ── Writer interface ──────────────────────────────────────────────────────

    def connect_writer(self) -> None:
        """Open the writer connection and ensure the schema exists."""
        self._conn = sqlite3.connect(str(self._path), check_same_thread=False)
        self._conn.executescript(_SCHEMA)
        self._conn.commit()

    def commit(self) -> None:
        if self._conn:
            self._conn.commit()

    def open_session(
        self, exe: str, title: str, category: str, ts: float, date: str
    ) -> int:
        """Insert a new open session row; returns the new row id."""
        assert self._conn, "connect_writer() must be called first"
        cur = self._conn.execute(
            "INSERT INTO window_sessions (date, start_ts, exe_name, window_title, category)"
            " VALUES (?, ?, ?, ?, ?)",
            (date, ts, exe, title, category),
        )
        return cur.lastrowid  # type: ignore[return-value]

    def close_session(self, session_id: int, end_ts: float) -> None:
        """Set end_ts on an open session row."""
        assert self._conn, "connect_writer() must be called first"
        self._conn.execute(
            "UPDATE window_sessions SET end_ts = ? WHERE id = ?",
            (end_ts, session_id),
        )

    def delete_session(self, session_id: int) -> None:
        """Remove a session that was too short to be meaningful (< min_session_sec)."""
        assert self._conn, "connect_writer() must be called first"
        self._conn.execute(
            "DELETE FROM window_sessions WHERE id = ?", (session_id,)
        )

    def insert_input_bucket(self, bucket: InputBucket) -> None:
        assert self._conn, "connect_writer() must be called first"
        self._conn.execute(
            "INSERT INTO input_events"
            " (bucket_ts, date, key_count, mouse_clicks, mouse_distance)"
            " VALUES (?, ?, ?, ?, ?)",
            (
                bucket.bucket_ts,
                bucket.date,
                bucket.key_count,
                bucket.mouse_clicks,
                bucket.mouse_distance,
            ),
        )

    def open_idle(self, ts: float, date: str) -> None:
        assert self._conn, "connect_writer() must be called first"
        self._conn.execute(
            "INSERT INTO idle_periods (date, start_ts) VALUES (?, ?)",
            (date, ts),
        )

    def close_idle(self, ts: float) -> None:
        """Close the most recently opened idle period."""
        assert self._conn, "connect_writer() must be called first"
        self._conn.execute(
            """UPDATE idle_periods
               SET end_ts = ?, duration_sec = ? - start_ts
               WHERE id = (
                   SELECT id FROM idle_periods
                   WHERE end_ts IS NULL
                   ORDER BY start_ts DESC
                   LIMIT 1
               )""",
            (ts, ts),
        )

    # ── Reader interface (own connection, any thread) ─────────────────────────

    def _reader_conn(self) -> sqlite3.Connection:
        if not self._path.exists():
            raise FileNotFoundError(
                f"Database not found at {self._path}. "
                "Has the tracker been started yet?"
            )
        conn = sqlite3.connect(str(self._path))
        conn.row_factory = sqlite3.Row
        return conn

    def query_window_sessions(self, date: str) -> list[dict[str, Any]]:
        conn = self._reader_conn()
        try:
            rows = conn.execute(
                "SELECT * FROM window_sessions WHERE date = ? ORDER BY start_ts ASC",
                (date,),
            ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    def query_input_totals(self, date: str) -> dict[str, float]:
        conn = self._reader_conn()
        try:
            row = conn.execute(
                """SELECT
                     COALESCE(SUM(key_count), 0)      AS total_keys,
                     COALESCE(SUM(mouse_clicks), 0)   AS total_clicks,
                     COALESCE(SUM(mouse_distance), 0) AS total_distance
                   FROM input_events WHERE date = ?""",
                (date,),
            ).fetchone()
            return dict(row) if row else {
                "total_keys": 0, "total_clicks": 0, "total_distance": 0
            }
        finally:
            conn.close()

    def query_idle_periods(self, date: str) -> list[dict[str, Any]]:
        conn = self._reader_conn()
        try:
            rows = conn.execute(
                "SELECT * FROM idle_periods WHERE date = ? ORDER BY start_ts ASC",
                (date,),
            ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    def query_trail(
        self,
        date: str,
        from_ts: float | None = None,
        to_ts: float | None = None,
    ) -> list[dict[str, Any]]:
        """
        Return a merged, time-ordered list of active sessions and idle periods.

        Optionally filtered to a Unix-timestamp range [from_ts, to_ts].
        Each row has keys: type, start_ts, end_ts, exe_name, window_title, category.
        """
        params_s: list[Any] = [date]
        params_i: list[Any] = [date]
        tf_s = ""
        tf_i = ""

        if from_ts is not None:
            tf_s += " AND start_ts >= ?"
            params_s.append(from_ts)
            tf_i += " AND start_ts >= ?"
            params_i.append(from_ts)
        if to_ts is not None:
            tf_s += " AND start_ts <= ?"
            params_s.append(to_ts)
            tf_i += " AND start_ts <= ?"
            params_i.append(to_ts)

        sql = f"""
            SELECT 'active' AS type,
                   start_ts, end_ts, exe_name, window_title, category
              FROM window_sessions
             WHERE date = ?{tf_s}
            UNION ALL
            SELECT 'idle', start_ts, end_ts, '', '', ''
              FROM idle_periods
             WHERE date = ?{tf_i}
            ORDER BY start_ts ASC
        """
        conn = self._reader_conn()
        try:
            rows = conn.execute(sql, params_s + params_i).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()
