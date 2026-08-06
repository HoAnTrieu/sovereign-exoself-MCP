"""SQLite migrations and durable memory operations."""

import hashlib
import json
import os
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import aiosqlite

from sovereign_exoself_mcp.domain import MemoryKind, MemoryRecord
from sovereign_exoself_mcp.security import contains_secret, normalize

SCHEMA_VERSION = 1

_MIGRATION = """
CREATE TABLE IF NOT EXISTS schema_version (version INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS sessions (id TEXT PRIMARY KEY, created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS runs (id TEXT PRIMARY KEY, session_id TEXT, status TEXT NOT NULL, answer TEXT NOT NULL, created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS messages (id TEXT PRIMARY KEY, run_id TEXT NOT NULL, role TEXT NOT NULL, content TEXT NOT NULL, created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS memory_items (
 id TEXT PRIMARY KEY, kind TEXT NOT NULL, content TEXT NOT NULL, fingerprint TEXT NOT NULL UNIQUE,
 confidence REAL NOT NULL, importance REAL NOT NULL, source_run_id TEXT, created_at TEXT NOT NULL,
 updated_at TEXT NOT NULL, last_accessed_at TEXT NOT NULL, access_count INTEGER NOT NULL DEFAULT 0, active INTEGER NOT NULL DEFAULT 1
);
CREATE TABLE IF NOT EXISTS memory_sources (memory_id TEXT NOT NULL, run_id TEXT, source_type TEXT NOT NULL, PRIMARY KEY(memory_id, source_type));
CREATE TABLE IF NOT EXISTS provider_calls (id TEXT PRIMARY KEY, run_id TEXT NOT NULL, role TEXT NOT NULL, model TEXT NOT NULL, latency_ms INTEGER NOT NULL, input_tokens INTEGER NOT NULL, output_tokens INTEGER NOT NULL, cost REAL, created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS outbox (id TEXT PRIMARY KEY, kind TEXT NOT NULL, payload TEXT NOT NULL, created_at TEXT NOT NULL, processed_at TEXT);
"""


def _now() -> str:
    return datetime.now(UTC).isoformat()


def fingerprint(content: str) -> str:
    """Return a stable fingerprint for normalized memory content."""
    return hashlib.sha256(normalize(content).encode()).hexdigest()


class MemoryRepository:
    """Single-process SQLite repository with explicit transactional writes."""

    def __init__(self, path: Path, *, fts_enabled: bool = True) -> None:
        self.path = path
        self.fts_enabled = fts_enabled
        self.connection: aiosqlite.Connection | None = None

    async def open(self) -> None:
        """Open and migrate the durable database."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if self.path.exists() and self.path.stat().st_mode & 0o077:
            raise PermissionError(f"database permissions are too broad: {self.path}")
        self.connection = await aiosqlite.connect(self.path)
        await self.connection.execute("PRAGMA foreign_keys = ON")
        await self.connection.execute("PRAGMA journal_mode = WAL")
        await self.connection.execute("PRAGMA busy_timeout = 5000")
        await self.connection.executescript(_MIGRATION)
        cursor = await self.connection.execute("SELECT COUNT(*) FROM schema_version")
        row = await cursor.fetchone()
        if row is None:
            raise RuntimeError("schema version query returned no row")
        count = row[0]
        if count == 0:
            await self.connection.execute(
                "INSERT INTO schema_version(version) VALUES (?)", (SCHEMA_VERSION,)
            )
        if self.fts_enabled:
            try:
                await self.connection.execute(
                    "CREATE VIRTUAL TABLE IF NOT EXISTS memory_fts USING fts5(content, memory_id UNINDEXED)"
                )
            except aiosqlite.OperationalError:
                self.fts_enabled = False
        await self.connection.commit()
        os.chmod(self.path, 0o600)
        await self.process_outbox()

    async def close(self) -> None:
        """Close the database connection."""
        if self.connection is not None:
            await self.connection.close()
            self.connection = None

    def _db(self) -> aiosqlite.Connection:
        if self.connection is None:
            raise RuntimeError("memory repository is not open")
        return self.connection

    async def store(
        self,
        content: str,
        kind: MemoryKind,
        *,
        source_run_id: str | None = None,
        confidence: float = 0.8,
        importance: float = 0.5,
    ) -> tuple[str, bool]:
        """Insert or refresh safe memory atomically."""
        if contains_secret(content):
            raise ValueError("memory content appears to contain a secret")
        db = self._db()
        item_id = str(uuid4())
        stamp = _now()
        digest = fingerprint(content)
        try:
            await db.execute("BEGIN IMMEDIATE")
            cursor = await db.execute(
                "SELECT id FROM memory_items WHERE fingerprint = ?", (digest,)
            )
            existing = await cursor.fetchone()
            if existing is not None:
                await db.execute(
                    "UPDATE memory_items SET active = 1, updated_at = ?, last_accessed_at = ? WHERE id = ?",
                    (stamp, stamp, existing[0]),
                )
                await db.commit()
                return str(existing[0]), False
            await db.execute(
                "INSERT INTO memory_items VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, 1)",
                (
                    item_id,
                    kind.value,
                    content,
                    digest,
                    confidence,
                    importance,
                    source_run_id,
                    stamp,
                    stamp,
                    stamp,
                ),
            )
            if self.fts_enabled:
                await db.execute(
                    "INSERT INTO memory_fts(content, memory_id) VALUES (?, ?)", (content, item_id)
                )
            await db.execute(
                "INSERT INTO memory_sources(memory_id, run_id, source_type) VALUES (?, ?, ?)",
                (item_id, source_run_id, "direct"),
            )
            await db.commit()
            return item_id, True
        except aiosqlite.Error:
            await db.rollback()
            raise

    async def search(self, query: str, limit: int) -> list[MemoryRecord]:
        """Return relevant active records using FTS5 or a tested fallback."""
        db = self._db()
        if self.fts_enabled:
            try:
                cursor = await db.execute(
                    "SELECT m.id,m.kind,m.content,m.confidence,m.importance,m.active FROM memory_fts f JOIN memory_items m ON m.id=f.memory_id WHERE memory_fts MATCH ? AND m.active=1 ORDER BY bm25(memory_fts), m.importance DESC LIMIT ?",
                    (query, limit),
                )
            except aiosqlite.OperationalError:
                self.fts_enabled = False
                return await self.search(query, limit)
        else:
            tokens = normalize(query).split()
            clause = " OR ".join("content LIKE ?" for _ in tokens) or "content LIKE ?"
            values = tuple(f"%{token}%" for token in tokens) or ("%",)
            cursor = await db.execute(
                f"SELECT id,kind,content,confidence,importance,active FROM memory_items WHERE active=1 AND ({clause}) ORDER BY importance DESC, updated_at DESC LIMIT ?",  # noqa: S608
                (*values, limit),
            )
        rows = await cursor.fetchall()
        ids = [str(row[0]) for row in rows]
        if ids:
            placeholders = ",".join("?" for _ in ids)
            await db.execute(
                f"UPDATE memory_items SET access_count=access_count+1,last_accessed_at=? WHERE id IN ({placeholders})",  # noqa: S608
                (_now(), *ids),
            )
            await db.commit()
        return [
            MemoryRecord(
                id=str(row[0]),
                kind=MemoryKind(row[1]),
                content=str(row[2]),
                confidence=float(row[3]),
                importance=float(row[4]),
                active=bool(row[5]),
            )
            for row in rows
        ]

    async def list(self, limit: int) -> list[MemoryRecord]:
        """List active records by recency."""
        cursor = await self._db().execute(
            "SELECT id,kind,content,confidence,importance,active FROM memory_items WHERE active=1 ORDER BY updated_at DESC LIMIT ?",
            (limit,),
        )
        return [
            MemoryRecord(
                id=str(row[0]),
                kind=MemoryKind(row[1]),
                content=str(row[2]),
                confidence=float(row[3]),
                importance=float(row[4]),
                active=bool(row[5]),
            )
            for row in await cursor.fetchall()
        ]

    async def delete(self, memory_id: str) -> bool:
        """Soft-delete a memory and persist the state."""
        cursor = await self._db().execute(
            "UPDATE memory_items SET active=0,updated_at=? WHERE id=? AND active=1",
            (_now(), memory_id),
        )
        await self._db().commit()
        return cursor.rowcount == 1

    async def export(self) -> str:
        """Create portable secret-screened JSON."""
        records = await self.list(10000)
        return json.dumps(
            [record.model_dump(mode="json") for record in records], ensure_ascii=False
        )

    async def last_successful_run(self) -> str | None:
        """Return the latest successful or degraded-run timestamp."""
        cursor = await self._db().execute(
            "SELECT created_at FROM runs WHERE status IN ('ok','partial') ORDER BY created_at DESC LIMIT 1"
        )
        row = await cursor.fetchone()
        return None if row is None else str(row[0])

    async def commit_run(
        self, run_id: str, session_id: str | None, status: str, answer: str
    ) -> None:
        """Commit final run output in one transaction."""
        db = self._db()
        await db.execute("BEGIN IMMEDIATE")
        try:
            if session_id is not None:
                await db.execute(
                    "INSERT OR IGNORE INTO sessions VALUES (?, ?)", (session_id, _now())
                )
            await db.execute(
                "INSERT INTO runs VALUES (?, ?, ?, ?, ?)",
                (run_id, session_id, status, answer, _now()),
            )
            await db.commit()
        except aiosqlite.Error:
            await db.rollback()
            raise

    async def enqueue(self, kind: str, payload: str) -> str:
        """Persist deferred work for recovery on restart."""
        outbox_id = str(uuid4())
        await self._db().execute(
            "INSERT INTO outbox VALUES (?, ?, ?, ?, NULL)", (outbox_id, kind, payload, _now())
        )
        await self._db().commit()
        return outbox_id

    async def process_outbox(self) -> int:
        """Process unhandled memory-store records idempotently."""
        db = self._db()
        cursor = await db.execute("SELECT id,kind,payload FROM outbox WHERE processed_at IS NULL")
        rows = await cursor.fetchall()
        completed = 0
        for row in rows:
            if row[1] == "memory_store":
                payload = json.loads(str(row[2]))
                await self.store(str(payload["content"]), MemoryKind(str(payload["kind"])))
            await db.execute(
                "UPDATE outbox SET processed_at=? WHERE id=? AND processed_at IS NULL",
                (_now(), row[0]),
            )
            await db.commit()
            completed += 1
        return completed
