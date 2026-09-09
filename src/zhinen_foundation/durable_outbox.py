"""SQLite-backed outbox for committed control-plane events."""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path

from .envelope import MessageEnvelope


class DurableOutbox:
    def __init__(self, database: str | Path) -> None:
        self.connection = sqlite3.connect(database)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA journal_mode=WAL")
        self.connection.execute("""
            CREATE TABLE IF NOT EXISTS outbox (
                message_id TEXT PRIMARY KEY,
                message_json TEXT NOT NULL,
                attempts INTEGER NOT NULL DEFAULT 0,
                published_at TEXT,
                last_error TEXT
            )
        """)
        self.connection.commit()

    def append(self, message: MessageEnvelope) -> None:
        self.connection.execute(
            "INSERT OR IGNORE INTO outbox(message_id, message_json) VALUES (?, ?)",
            (message.messageId, json.dumps(message.as_dict(), ensure_ascii=False, sort_keys=True)),
        )
        self.connection.commit()

    def pending(self) -> list[sqlite3.Row]:
        return list(self.connection.execute("SELECT * FROM outbox WHERE published_at IS NULL ORDER BY rowid"))

    def publish_pending(self, publisher: Callable[[dict], None]) -> int:
        count = 0
        for row in self.pending():
            self.connection.execute("UPDATE outbox SET attempts = attempts + 1 WHERE message_id = ?", (row["message_id"],))
            try:
                publisher(json.loads(row["message_json"]))
            except Exception as exc:  # retain the row for a later retry
                self.connection.execute("UPDATE outbox SET last_error = ? WHERE message_id = ?", (str(exc), row["message_id"]))
                self.connection.commit()
                continue
            self.connection.execute("UPDATE outbox SET published_at = ?, last_error = NULL WHERE message_id = ?", (datetime.now(timezone.utc).isoformat(), row["message_id"]))
            self.connection.commit()
            count += 1
        return count

    def close(self) -> None:
        self.connection.close()
