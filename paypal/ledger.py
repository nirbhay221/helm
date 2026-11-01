"""A tiny SQLite ledger: idempotency keys, webhook-event dedupe, and a
double-booking guard on money movements.

Three guarantees it enforces so a retry or a duplicate never moves money twice:
  - idempotency(key): a self-generated request key -> the stored response,
  - events(event_id): each PayPal webhook event id applied at most once,
  - movements UNIQUE(kind, ref_type, ref_id): a given payout batch or order
    capture can be booked only once.

Uses the standard-library sqlite3, so no dependency. ":memory:" for tests.
"""
from __future__ import annotations

import json
import sqlite3
import time


class Ledger:
    def __init__(self, path: str = ":memory:") -> None:
        self.conn = sqlite3.connect(path)
        self.conn.row_factory = sqlite3.Row
        self._init()

    def _init(self) -> None:
        c = self.conn
        c.execute(
            "CREATE TABLE IF NOT EXISTS idempotency("
            "key TEXT PRIMARY KEY, response TEXT NOT NULL, created_at REAL NOT NULL)"
        )
        c.execute(
            "CREATE TABLE IF NOT EXISTS events("
            "event_id TEXT PRIMARY KEY, kind TEXT, payload TEXT, created_at REAL NOT NULL)"
        )
        c.execute(
            "CREATE TABLE IF NOT EXISTS movements("
            "id INTEGER PRIMARY KEY AUTOINCREMENT, kind TEXT NOT NULL, "
            "ref_type TEXT NOT NULL, ref_id TEXT NOT NULL, amount REAL, status TEXT, "
            "created_at REAL NOT NULL, UNIQUE(kind, ref_type, ref_id))"
        )
        c.commit()

    # --- idempotency --------------------------------------------------------
    def remember(self, key: str, response: dict) -> tuple[bool, dict]:
        """Return (is_new, response). If the key was seen, returns the stored
        response and is_new=False (mirrors PayPal-Request-Id behavior)."""
        row = self.conn.execute(
            "SELECT response FROM idempotency WHERE key = ?", (key,)
        ).fetchone()
        if row is not None:
            return False, json.loads(row["response"])
        self.conn.execute(
            "INSERT INTO idempotency(key, response, created_at) VALUES (?, ?, ?)",
            (key, json.dumps(response), time.time()),
        )
        self.conn.commit()
        return True, response

    def get(self, key: str) -> dict | None:
        row = self.conn.execute(
            "SELECT response FROM idempotency WHERE key = ?", (key,)
        ).fetchone()
        return json.loads(row["response"]) if row else None

    # --- webhook dedupe -----------------------------------------------------
    def record_event(self, event_id: str, kind: str = "", payload: dict | None = None) -> bool:
        """Return True if this event id is new (and record it), False if already
        seen (duplicate webhook delivery)."""
        cur = self.conn.execute(
            "INSERT OR IGNORE INTO events(event_id, kind, payload, created_at) "
            "VALUES (?, ?, ?, ?)",
            (event_id, kind, json.dumps(payload or {}), time.time()),
        )
        self.conn.commit()
        return cur.rowcount == 1

    # --- money movements ----------------------------------------------------
    def record_movement(
        self, kind: str, ref_type: str, ref_id: str, amount: float, status: str
    ) -> bool:
        """Return True if newly booked, False if this (kind, ref_type, ref_id)
        was already booked (double-booking prevented)."""
        cur = self.conn.execute(
            "INSERT OR IGNORE INTO movements(kind, ref_type, ref_id, amount, status, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (kind, ref_type, ref_id, amount, status, time.time()),
        )
        self.conn.commit()
        return cur.rowcount == 1

    def movements(self) -> list[dict]:
        rows = self.conn.execute(
            "SELECT kind, ref_type, ref_id, amount, status FROM movements ORDER BY id"
        ).fetchall()
        return [dict(r) for r in rows]
