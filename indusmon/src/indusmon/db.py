from __future__ import annotations

import sqlite3
import threading
from pathlib import Path
from typing import Any, Iterable

SCHEMA = """
PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;

CREATE TABLE IF NOT EXISTS devices (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  host TEXT NOT NULL,
  port INTEGER NOT NULL,
  unit_id INTEGER NOT NULL,
  poll_interval_ms INTEGER NOT NULL DEFAULT 1000,
  enabled INTEGER NOT NULL DEFAULT 1,
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS tags (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  device_id TEXT NOT NULL REFERENCES devices(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  register INTEGER NOT NULL,
  data_type TEXT NOT NULL DEFAULT 'uint16',
  scale REAL NOT NULL DEFAULT 1,
  offset REAL NOT NULL DEFAULT 0,
  unit TEXT NOT NULL DEFAULT '',
  limit_hi REAL,
  limit_hihi REAL,
  limit_lo REAL,
  UNIQUE(device_id, name)
);

CREATE TABLE IF NOT EXISTS readings (
  ts INTEGER NOT NULL,
  device_id TEXT NOT NULL,
  tag TEXT NOT NULL,
  value REAL NOT NULL,
  quality INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_readings_dtt ON readings(device_id, tag, ts);

CREATE TABLE IF NOT EXISTS alerts (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ts INTEGER NOT NULL,
  device_id TEXT NOT NULL,
  tag TEXT NOT NULL,
  level TEXT NOT NULL,
  value REAL NOT NULL,
  "limit" REAL NOT NULL,
  state TEXT NOT NULL DEFAULT 'active',
  cleared_ts INTEGER
);
CREATE INDEX IF NOT EXISTS idx_alerts_state ON alerts(state, device_id);
CREATE INDEX IF NOT EXISTS idx_alerts_dtl ON alerts(device_id, tag, level, state);

CREATE TABLE IF NOT EXISTS spikes (
  device_id TEXT NOT NULL,
  tag TEXT NOT NULL,
  value REAL NOT NULL,
  until_ts INTEGER NOT NULL,
  PRIMARY KEY(device_id, tag)
);
"""


def _open(db_path: Path | str) -> sqlite3.Connection:
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def connect(db_path: Path | str) -> sqlite3.Connection:
    """Create schema and return a raw connection (prefer Database for multi-thread)."""
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    return conn


class Database:
    """Thread-local SQLite access against a shared file (WAL)."""

    def __init__(self, db_path: Path | str) -> None:
        self.path = Path(db_path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._local = threading.local()
        # initialize schema once
        conn = _open(self.path)
        conn.executescript(SCHEMA)
        conn.close()

    def conn(self) -> sqlite3.Connection:
        conn = getattr(self._local, "conn", None)
        if conn is None:
            conn = _open(self.path)
            self._local.conn = conn
        return conn

    def execute(self, sql: str, params: Any = ()) -> sqlite3.Cursor:
        return self.conn().execute(sql, params)

    def executemany(self, sql: str, seq: Iterable[Any]) -> sqlite3.Cursor:
        return self.conn().executemany(sql, seq)

    def cursor(self) -> sqlite3.Cursor:
        return self.conn().cursor()

    def commit(self) -> None:
        self.conn().commit()

    def close(self) -> None:
        conn = getattr(self._local, "conn", None)
        if conn is not None:
            conn.close()
            self._local.conn = None


def rows_to_dicts(rows: Iterable[sqlite3.Row]) -> list[dict[str, Any]]:
    return [dict(r) for r in rows]
