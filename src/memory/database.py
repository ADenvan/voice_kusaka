from datetime import UTC, datetime

import aiosqlite

from src.core.config import Config
from src.core.exceptions import MemoryError as VoiceAIMemoryError

_SCHEMA = """
CREATE TABLE IF NOT EXISTS sessions (
    id TEXT PRIMARY KEY,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    FOREIGN KEY (session_id) REFERENCES sessions(id)
);

CREATE INDEX IF NOT EXISTS idx_messages_session ON messages(session_id);
"""


class SQLiteStore:
    def __init__(self, config: Config) -> None:
        self._db_path = config.db_path
        self._db: aiosqlite.Connection | None = None

    async def _ensure_db(self) -> aiosqlite.Connection:
        if self._db is None:
            try:
                self._db = await aiosqlite.connect(self._db_path)
                await self._db.execute("PRAGMA journal_mode=WAL")
                await self._db.executescript(_SCHEMA)
                await self._db.commit()
            except Exception as e:
                raise VoiceAIMemoryError(f"Failed to open database: {e}") from e
        return self._db

    async def create_session(self) -> str:
        db = await self._ensure_db()
        session_id = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
        created_at = datetime.now(UTC).isoformat()
        try:
            await db.execute(
                "INSERT INTO sessions (id, created_at) VALUES (?, ?)",
                (session_id, created_at),
            )
            await db.commit()
            return session_id
        except Exception as e:
            raise VoiceAIMemoryError(f"Failed to create session: {e}") from e

    async def save_message(self, session_id: str, role: str, content: str) -> None:
        db = await self._ensure_db()
        timestamp = datetime.now(UTC).isoformat()
        try:
            await db.execute(
                "INSERT INTO messages (session_id, role, content, timestamp) VALUES (?, ?, ?, ?)",
                (session_id, role, content, timestamp),
            )
            await db.commit()
        except Exception as e:
            raise VoiceAIMemoryError(f"Failed to save message: {e}") from e

    async def get_history(self, session_id: str, limit: int = 50) -> list[dict]:
        db = await self._ensure_db()
        try:
            cursor = await db.execute(
                "SELECT role, content, timestamp FROM messages "
                "WHERE session_id = ? ORDER BY id DESC LIMIT ?",
                (session_id, limit),
            )
            rows = await cursor.fetchall()
            return [
                {"role": row[0], "content": row[1], "timestamp": row[2]}
                for row in reversed(rows)
            ]
        except Exception as e:
            raise VoiceAIMemoryError(f"Failed to get history: {e}") from e

    async def delete_session(self, session_id: str) -> None:
        db = await self._ensure_db()
        try:
            await db.execute("DELETE FROM messages WHERE session_id = ?", (session_id,))
            await db.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
            await db.commit()
        except Exception as e:
            raise VoiceAIMemoryError(f"Failed to delete session: {e}") from e

    async def close(self) -> None:
        if self._db:
            await self._db.close()
            self._db = None
