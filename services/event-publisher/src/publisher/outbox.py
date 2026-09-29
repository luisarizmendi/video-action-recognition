"""Durable local outbox. This is the "Durable Event Delivery" box of the edge.

Every event is written to SQLite (WAL, synchronous=FULL) before the API returns.
A worker delivers rows to S4 and AMQ Streams. If the link to the datacenter is down,
rows wait here and are retried with exponential backoff.
"""
import sqlite3
import threading
import time
from dataclasses import dataclass
from typing import List, Optional, Tuple

PRIORITY_HIGH = 100
PRIORITY_SUSPICIOUS = 50
PRIORITY_PASSENGER = 10
PRIORITY_HEALTH = 5

_CREATE = """
CREATE TABLE IF NOT EXISTS outbox (
  id TEXT PRIMARY KEY,
  topic TEXT NOT NULL,
  key TEXT NOT NULL,
  payload TEXT NOT NULL,
  clip_path TEXT,
  evidence_bucket TEXT,
  evidence_key TEXT,
  priority INTEGER NOT NULL,
  attempts INTEGER NOT NULL DEFAULT 0,
  next_attempt REAL NOT NULL,
  evidence_done INTEGER NOT NULL DEFAULT 0,
  last_error TEXT,
  created REAL NOT NULL
)
"""
_COLS = ("id,topic,key,payload,clip_path,evidence_bucket,evidence_key,"
         "priority,attempts,next_attempt,evidence_done,created")


@dataclass
class Row:
    id: str
    topic: str
    key: str
    payload: str
    clip_path: Optional[str]
    evidence_bucket: Optional[str]
    evidence_key: Optional[str]
    priority: int
    attempts: int
    next_attempt: float
    evidence_done: bool
    created: float


class Outbox:
    def __init__(self, path: str):
        self._db = sqlite3.connect(path, check_same_thread=False, isolation_level=None)
        self._lock = threading.Lock()
        with self._lock:
            self._db.execute("PRAGMA journal_mode=WAL")
            self._db.execute("PRAGMA synchronous=FULL")
            self._db.execute(_CREATE)

    def enqueue(self, row_id: str, topic: str, key: str, payload: str, priority: int,
                clip_path: Optional[str] = None, evidence_bucket: Optional[str] = None,
                evidence_key: Optional[str] = None, now: Optional[float] = None) -> None:
        now = now if now is not None else time.time()
        with self._lock:
            self._db.execute(
                "INSERT OR IGNORE INTO outbox (id,topic,key,payload,clip_path,evidence_bucket,"
                "evidence_key,priority,next_attempt,created) VALUES (?,?,?,?,?,?,?,?,?,?)",
                (row_id, topic, key, payload, clip_path, evidence_bucket, evidence_key,
                 priority, now, now))

    def due(self, now: float, limit: int = 20) -> List[Row]:
        with self._lock:
            cur = self._db.execute(
                f"SELECT {_COLS} FROM outbox WHERE next_attempt <= ? "
                "ORDER BY priority DESC, created ASC LIMIT ?", (now, limit))
            return [Row(*r[:10], bool(r[10]), r[11]) for r in cur.fetchall()]

    def mark_evidence_done(self, row_id: str) -> None:
        with self._lock:
            self._db.execute("UPDATE outbox SET evidence_done=1 WHERE id=?", (row_id,))

    def mark_delivered(self, row_id: str) -> None:
        with self._lock:
            self._db.execute("DELETE FROM outbox WHERE id=?", (row_id,))

    def mark_failed(self, row_id: str, now: float, error: str) -> None:
        with self._lock:
            cur = self._db.execute("SELECT attempts FROM outbox WHERE id=?", (row_id,))
            found = cur.fetchone()
            if not found:
                return
            attempts = found[0] + 1
            backoff = min(300, 2 ** attempts)
            self._db.execute(
                "UPDATE outbox SET attempts=?, next_attempt=?, last_error=? WHERE id=?",
                (attempts, now + backoff, error[:500], row_id))

    def stats(self, now: Optional[float] = None) -> Tuple[int, float]:
        now = now if now is not None else time.time()
        with self._lock:
            n, oldest = self._db.execute("SELECT COUNT(*), MIN(created) FROM outbox").fetchone()
        return n, (now - oldest) if oldest else 0.0

    def enforce_cap(self, max_rows: int) -> List[str]:
        """Drop the lowest priority, oldest rows when the outbox is too big.
        Returns the clip paths of dropped rows so the caller can delete the files."""
        with self._lock:
            (n,) = self._db.execute("SELECT COUNT(*) FROM outbox").fetchone()
            overflow = n - max_rows
            if overflow <= 0:
                return []
            rows = self._db.execute(
                "SELECT id, clip_path FROM outbox ORDER BY priority ASC, created ASC LIMIT ?",
                (overflow,)).fetchall()
            self._db.executemany("DELETE FROM outbox WHERE id=?", [(r[0],) for r in rows])
            return [r[1] for r in rows if r[1]]
