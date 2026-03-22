"""
Kuma Claw - 记忆系统
==================
SQLite 持久化，线程安全（已移除 JSON 冗余）
"""

import hashlib
import json
import sqlite3
import threading
from dataclasses import dataclass
from datetime import datetime
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

            CREATE TABLE IF NOT EXISTS metadata (
                key TEXT PRIMARY KEY,
                value TEXT
            );

            -- 会话消息表（替代 JSON 文件）
            CREATE TABLE IF NOT EXISTS session_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                timestamp TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_session_messages_session
            ON session_messages(session_id);
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

    # ============================================
    # 会话消息（统一使用 SQLite，移除 JSON 冗余）
    # ============================================

    def add_session_message(self, session_id: str, role: str, content: str):
        """添加会话消息（仅 SQLite，不再双重写入 JSON）"""
        conn = self._get_conn()
        conn.execute(
            """
            INSERT INTO session_messages (session_id, role, content, timestamp)
            VALUES (?, ?, ?, ?)
            """,
            (session_id, role, content, datetime.utcnow().isoformat()),
        )
        conn.commit()

    def get_session_messages(self, session_id: str, limit: int = 50) -> list[dict]:
        """获取会话消息"""
        conn = self._get_conn()
        rows = conn.execute(
            """
            SELECT role, content, timestamp FROM session_messages
            WHERE session_id = ?
            ORDER BY id DESC
            LIMIT ?
            """,
            (session_id, limit),
        ).fetchall()
        # 反转顺序（从旧到新）
        messages = [
            {"role": r["role"], "content": r["content"], "timestamp": r["timestamp"]}
            for r in reversed(rows)
        ]
        return messages

    def delete_session(self, session_id: str):
        """删除会话"""
        conn = self._get_conn()
        conn.execute("DELETE FROM session_messages WHERE session_id = ?", (session_id,))
        conn.commit()

    def list_sessions(self) -> list[str]:
        """列出所有会话"""
        conn = self._get_conn()
        rows = conn.execute("SELECT DISTINCT session_id FROM session_messages").fetchall()
        return [r["session_id"] for r in rows]

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
        now = datetime.utcnow().isoformat()
        entry = MemoryEntry(
            id=hashlib.sha256(content.encode()).hexdigest()[:16],
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

    def add_session_message(self, session_id: str, role: str, content: str):
        """添加会话消息（仅 SQLite，不再双重写入 JSON）"""
        self.store.add_session_message(session_id, role, content)

    def get_session_history(self, session_id: str, limit: int = 50) -> list[dict]:
        """获取会话历史"""
        return self.store.get_session_messages(session_id, limit)

    def clear_session(self, session_id: str):
        """清空会话"""
        self.store.clear(f"session:{session_id}")
        self.store.delete_session(session_id)

    def stats(self) -> MemoryStats:
        """统计"""
        return self.store.stats()


# 全局实例
memory_manager = MemoryManager()
