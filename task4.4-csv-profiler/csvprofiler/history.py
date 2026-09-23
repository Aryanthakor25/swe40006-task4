"""Run history in SQLite. In Docker the DB sits on a named volume so it survives
containers being removed."""
import hashlib
import socket
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS runs (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    run_at      TEXT NOT NULL,
    container   TEXT NOT NULL,
    file        TEXT NOT NULL,
    sha256      TEXT NOT NULL,
    rows        INTEGER,
    columns     INTEGER,
    duration_ms INTEGER,
    status      TEXT NOT NULL
)
"""


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


class History:
    def __init__(self, db_path: Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.db_path)
        self.conn.execute(SCHEMA)
        self.conn.commit()

    def record(self, file: str, sha256: str, rows, columns, duration_ms: int, status: str) -> None:
        self.conn.execute(
            "INSERT INTO runs (run_at, container, file, sha256, rows, columns, duration_ms, status) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (datetime.now(timezone.utc).isoformat(timespec="seconds"), socket.gethostname(),
             file, sha256, rows, columns, duration_ms, status),
        )
        self.conn.commit()

    def already_processed(self, sha256: str) -> bool:
        cur = self.conn.execute("SELECT 1 FROM runs WHERE sha256 = ? AND status = 'ok' LIMIT 1", (sha256,))
        return cur.fetchone() is not None

    def recent(self, limit: int = 20) -> list[tuple]:
        cur = self.conn.execute(
            "SELECT id, run_at, container, file, rows, columns, duration_ms, status "
            "FROM runs ORDER BY id DESC LIMIT ?", (limit,))
        return cur.fetchall()

    def close(self) -> None:
        self.conn.close()
