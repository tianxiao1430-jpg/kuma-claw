"""
Kuma Claw - 记忆系统
==================
SQLite + JSON 双重持久化，线程安全
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
        """FTS 搜索"""
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


class SessionStore:
    """会话存储（JSON 文件）"""

    def __init__(self, data_dir: str | None = None):
        self.data_dir = Path(data_dir or str(Path.home() / ".kuma-claw" / "sessions"))
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self._sessions: dict[str, list[dict]] = {}
        self._lock = threading.Lock()
        self._load_all_sessions()

    def _session_file(self, session_id: str) -> Path:
        safe_id = hashlib.sha256(session_id.encode()).hexdigest()[:16]
        return self.data_dir / f"{safe_id}.json"

    def _load_all_sessions(self):
        for json_file in self.data_dir.glob("*.json"):
            try:
                with json_file.open("r", encoding="utf-8") as f:
                    data = json.load(f)
                    if data.get("session_id"):
                        self._sessions[data["session_id"]] = data.get("messages", [])
            except (json.JSONDecodeError, OSError):
                pass

    def load_session(self, session_id: str) -> list[dict]:
        with self._lock:
            return self._sessions.get(session_id, []).copy()

    def save_session(self, session_id: str, messages: list[dict]):
        with self._lock:
            self._sessions[session_id] = messages.copy()
            session_file = self._session_file(session_id)
            temp_file = session_file.with_suffix(".tmp")

            try:
                data = {
                    "session_id": session_id,
                    "messages": messages,
                    "last_updated": datetime.utcnow().isoformat(),
                    "message_count": len(messages),
                }
                with temp_file.open("w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                temp_file.replace(session_file)
            except OSError:
                if temp_file.exists():
                    temp_file.unlink()
                raise

    def add_message(self, session_id: str, role: str, content: str):
        with self._lock:
            if session_id not in self._sessions:
                self._sessions[session_id] = []

            self._sessions[session_id].append(
                {"role": role, "content": content, "timestamp": datetime.utcnow().isoformat()}
            )
            self.save_session(session_id, self._sessions[session_id])

    def delete_session(self, session_id: str):
        with self._lock:
            self._sessions.pop(session_id, None)
            session_file = self._session_file(session_id)
            if session_file.exists():
                session_file.unlink()

    def list_sessions(self) -> list[str]:
        with self._lock:
            return list(self._sessions.keys())


class MemoryManager:
    """记忆管理器"""

    def __init__(self, store: MemoryStore | None = None, session_store: SessionStore | None = None):
        self.store = store or MemoryStore()
        self.session_store = session_store or SessionStore()

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
        """添加会话消息"""
        self.remember(
            content=f"[{role}] {content}",
            source=f"session:{session_id}",
            metadata={"role": role, "session_id": session_id},
        )
        self.session_store.add_message(session_id, role, content)

    def get_session_history(self, session_id: str, limit: int = 50) -> list[dict]:
        """获取会话历史"""
        messages = self.session_store.load_session(session_id)
        return messages[-limit:] if messages else []

    def clear_session(self, session_id: str):
        """清空会话"""
        self.store.clear(f"session:{session_id}")
        self.session_store.delete_session(session_id)

    def stats(self) -> MemoryStats:
        """统计"""
        return self.store.stats()


# 全局实例
memory_manager = MemoryManager()
