"""
Kuma Claw - 记忆系统
==================
SQLite 持久化，线程安全（已移除 JSON 冗余）
"""

import json
import sqlite3
import threading
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass
class MemoryEntry:
    """记忆条目"""

    id: str
    content: str
    source: str
    metadata: dict[str, Any]
    created_at: str
    updated_at: str
    embedding: list[float] | None = None


@dataclass
class MemorySearchResult:
    """搜索结果"""

    entry: MemoryEntry
    score: float


@dataclass
class MemoryStats:
    """记忆统计"""

    total_entries: int
    by_source: dict[str, int]
    last_sync: str | None


class MemoryStore:
    """记忆存储（线程安全 SQLite）"""

    def __init__(self, db_path: str | None = None):
        self.db_path = db_path or str(Path.home() / ".kuma-claw" / "memory.db")
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)

        # 线程本地存储
        self._local = threading.local()
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        """获取线程本地连接"""
        if not hasattr(self._local, "conn") or self._local.conn is None:
            self._local.conn = sqlite3.connect(self.db_path, check_same_thread=False)
            self._local.conn.row_factory = sqlite3.Row
            # 启用 WAL 模式提升并发
            self._local.conn.execute("PRAGMA journal_mode=WAL")
        return self._local.conn

    def _init_db(self):
        """初始化数据库"""
        conn = self._get_conn()
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS memories (
                id TEXT PRIMARY KEY,
                content TEXT NOT NULL,
                source TEXT NOT NULL,
                metadata TEXT DEFAULT '{}',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                embedding BLOB
            );

            CREATE VIRTUAL TABLE IF NOT EXISTS memories_fts
            USING fts5(content, content='memories', content_rowid='rowid');

            CREATE TRIGGER IF NOT EXISTS memories_ai
            AFTER INSERT ON memories BEGIN
                INSERT INTO memories_fts(rowid, content) VALUES (new.rowid, new.content);
            END;

            CREATE TRIGGER IF NOT EXISTS memories_ad
            AFTER DELETE ON memories BEGIN
                INSERT INTO memories_fts(memories_fts, rowid, content)
                VALUES('delete', old.rowid, old.content);
            END;

            CREATE TRIGGER IF NOT EXISTS memories_au_before
            BEFORE UPDATE ON memories BEGIN
                INSERT INTO memories_fts(memories_fts, rowid, content)
                VALUES('delete', old.rowid, old.content);
            END;

            CREATE TRIGGER IF NOT EXISTS memories_au_after
            AFTER UPDATE ON memories BEGIN
                INSERT INTO memories_fts(rowid, content) VALUES (new.rowid, new.content);
            END;

            CREATE TABLE IF NOT EXISTS metadata (
                key TEXT PRIMARY KEY,
                value TEXT
            );
        """)
        conn.commit()

    def add(self, entry: MemoryEntry):
        """添加记忆"""
        conn = self._get_conn()
        embedding_blob = None
        if entry.embedding:
            import struct

            embedding_blob = struct.pack(f"{len(entry.embedding)}f", *entry.embedding)

        conn.execute(
            """
            INSERT OR REPLACE INTO memories
            (id, content, source, metadata, created_at, updated_at, embedding)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
            (
                entry.id,
                entry.content,
                entry.source,
                json.dumps(entry.metadata),
                entry.created_at,
                entry.updated_at,
                embedding_blob,
            ),
        )
        conn.commit()

    def get(self, entry_id: str) -> MemoryEntry | None:
        """获取记忆"""
        row = (
            self._get_conn().execute("SELECT * FROM memories WHERE id = ?", (entry_id,)).fetchone()
        )
        return self._row_to_entry(row) if row else None

    def search_fts(self, query: str, limit: int = 10) -> list[MemorySearchResult]:
        """FTS 搜索（中文回退到 LIKE）"""
        conn = self._get_conn()
        try:
            rows = conn.execute(
                """
                SELECT m.*, bm25(memories_fts) as score
                FROM memories m
                JOIN memories_fts fts ON m.rowid = fts.rowid
                WHERE memories_fts MATCH ?
                ORDER BY score
                LIMIT ?
            """,
                (query, limit),
            ).fetchall()
            # FTS5 对中文支持不好，如果返回空结果，回退到 LIKE
            if not rows:
                rows = conn.execute(
                    """
                    SELECT *, 1.0 as score
                    FROM memories
                    WHERE content LIKE ?
                    ORDER BY updated_at DESC
                    LIMIT ?
                """,
                    (f"%{query}%", limit),
                ).fetchall()
        except sqlite3.Error:
            # FTS 失败，回退到 LIKE
            rows = conn.execute(
                """
                SELECT *, 1.0 as score
                FROM memories
                WHERE content LIKE ?
                ORDER BY updated_at DESC
                LIMIT ?
            """,
                (f"%{query}%", limit),
            ).fetchall()

        return [
            MemorySearchResult(entry=self._row_to_entry(r), score=abs(r["score"])) for r in rows
        ]

    def delete(self, entry_id: str):
        """删除记忆"""
        self._get_conn().execute("DELETE FROM memories WHERE id = ?", (entry_id,))
        self._get_conn().commit()

    def clear(self, source: str | None = None):
        """清空记忆"""
        conn = self._get_conn()
        if source:
            conn.execute("DELETE FROM memories WHERE source = ?", (source,))
        else:
            conn.execute("DELETE FROM memories")
        conn.commit()

    def stats(self) -> MemoryStats:
        """统计"""
        conn = self._get_conn()
        total = conn.execute("SELECT COUNT(*) FROM memories").fetchone()[0]

        by_source = {}
        for row in conn.execute("SELECT source, COUNT(*) as count FROM memories GROUP BY source"):
            by_source[row["source"]] = row["count"]

        last_sync = conn.execute("SELECT value FROM metadata WHERE key = 'last_sync'").fetchone()

        return MemoryStats(
            total_entries=total,
            by_source=by_source,
            last_sync=last_sync["value"] if last_sync else None,
        )

    def _row_to_entry(self, row: sqlite3.Row) -> MemoryEntry:
        """转换为 MemoryEntry"""
        embedding = None
        if row["embedding"]:
            import struct

            embedding = list(struct.unpack(f"{len(row['embedding']) // 4}f", row["embedding"]))

        return MemoryEntry(
            id=row["id"],
            content=row["content"],
            source=row["source"],
            metadata=json.loads(row["metadata"]),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            embedding=embedding,
        )

    def close(self):
        """关闭连接"""
        if hasattr(self._local, "conn") and self._local.conn:
            self._local.conn.close()
            self._local.conn = None


class MemoryManager:
    """记忆管理器（统一使用 SQLite）"""

    def __init__(self, store: MemoryStore | None = None):
        self.store = store or MemoryStore()

    def remember(
        self, content: str, source: str = "fact", metadata: dict | None = None
    ) -> MemoryEntry:
        """记住"""
        now = datetime.now(timezone.utc).isoformat()
        entry = MemoryEntry(
            id=str(uuid.uuid4()),
            content=content,
            source=source,
            metadata=metadata or {},
            created_at=now,
            updated_at=now,
        )
        self.store.add(entry)
        return entry

    def forget(self, entry_id: str):
        """忘记"""
        self.store.delete(entry_id)

    def search(self, query: str, limit: int = 10) -> list[MemorySearchResult]:
        """搜索"""
        return self.store.search_fts(query, limit)

    def get_context(self, query: str, max_entries: int = 5) -> str:
        """获取上下文"""
        results = self.search(query, max_entries)
        if not results:
            return ""
        return "## 相关记忆\n" + "\n".join(f"- {r.entry.content}" for r in results)

    def stats(self) -> MemoryStats:
        """统计"""
        return self.store.stats()


# 全局实例
memory_manager = MemoryManager()
