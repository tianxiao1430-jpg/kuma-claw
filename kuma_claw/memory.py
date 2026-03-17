"""
Kuma Claw - 记忆系统
==================
参考 OpenClaw 的记忆架构设计
支持 SQLite + JSON 文件双重持久化
"""

import os
import json
import sqlite3
import hashlib
import threading
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime
from dataclasses import dataclass, asdict


# ============================================
# 数据结构
# ============================================

@dataclass
class MemoryEntry:
    """记忆条目"""
    id: str
    content: str
    source: str  # "memory", "session", "fact"
    metadata: Dict[str, Any]
    created_at: str
    updated_at: str
    embedding: Optional[List[float]] = None


@dataclass
class MemorySearchResult:
    """搜索结果"""
    entry: MemoryEntry
    score: float
    highlight: Optional[str] = None


@dataclass
class MemoryStats:
    """记忆统计"""
    total_entries: int
    by_source: Dict[str, int]
    last_sync: Optional[str]


# ============================================
# 存储后端：SQLite
# ============================================

class MemoryStore:
    """记忆存储（SQLite + 向量）"""
    
    def __init__(self, db_path: Optional[str] = None):
        if db_path is None:
            db_path = str(Path.home() / ".kuma-claw" / "memory.db")
        
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self._init_db()
    
    def _init_db(self):
        """初始化数据库"""
        self.conn.executescript("""
            -- 记忆表
            CREATE TABLE IF NOT EXISTS memories (
                id TEXT PRIMARY KEY,
                content TEXT NOT NULL,
                source TEXT NOT NULL,
                metadata TEXT DEFAULT '{}',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                embedding BLOB
            );
            
            -- FTS 索引
            CREATE VIRTUAL TABLE IF NOT EXISTS memories_fts 
            USING fts5(content, content='memories', content_rowid='rowid');
            
            -- 触发器：自动同步 FTS
            CREATE TRIGGER IF NOT EXISTS memories_ai 
            AFTER INSERT ON memories BEGIN
                INSERT INTO memories_fts(rowid, content) 
                VALUES (new.rowid, new.content);
            END;
            
            CREATE TRIGGER IF NOT EXISTS memories_ad 
            AFTER DELETE ON memories BEGIN
                INSERT INTO memories_fts(memories_fts, rowid, content) 
                VALUES('delete', old.rowid, old.content);
            END;
            
            CREATE TRIGGER IF NOT EXISTS memories_au 
            AFTER UPDATE ON memories BEGIN
                INSERT INTO memories_fts(memories_fts, rowid, content) 
                VALUES('delete', old.rowid, old.content);
                INSERT INTO memories_fts(rowid, content) 
                VALUES (new.rowid, new.content);
            END;
            
            -- 元数据表
            CREATE TABLE IF NOT EXISTS metadata (
                key TEXT PRIMARY KEY,
                value TEXT
            );
        """)
        self.conn.commit()
    
    def add(self, entry: MemoryEntry):
        """添加记忆"""
        embedding_blob = None
        if entry.embedding:
            import struct
            embedding_blob = struct.pack(f'{len(entry.embedding)}f', *entry.embedding)
        
        self.conn.execute("""
            INSERT OR REPLACE INTO memories 
            (id, content, source, metadata, created_at, updated_at, embedding)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            entry.id,
            entry.content,
            entry.source,
            json.dumps(entry.metadata),
            entry.created_at,
            entry.updated_at,
            embedding_blob
        ))
        self.conn.commit()
    
    def get(self, entry_id: str) -> Optional[MemoryEntry]:
        """获取记忆"""
        row = self.conn.execute(
            "SELECT * FROM memories WHERE id = ?", (entry_id,)
        ).fetchone()
        
        if not row:
            return None
        
        return self._row_to_entry(row)
    
    def search_fts(self, query: str, limit: int = 10) -> List[MemorySearchResult]:
        """FTS 搜索"""
        try:
            rows = self.conn.execute("""
                SELECT m.*, bm25(memories_fts) as score
                FROM memories m
                JOIN memories_fts fts ON m.rowid = fts.rowid
                WHERE memories_fts MATCH ?
                ORDER BY score
                LIMIT ?
            """, (query, limit)).fetchall()
        except sqlite3.Error:
            # FTS 可能失败，使用 LIKE
            rows = self.conn.execute("""
                SELECT *, 1.0 as score
                FROM memories
                WHERE content LIKE ?
                ORDER BY updated_at DESC
                LIMIT ?
            """, (f"%{query}%", limit)).fetchall()
        
        results = []
        for row in rows:
            entry = self._row_to_entry(row)
            score = abs(row["score"]) if "score" in row.keys() else 1.0
            results.append(MemorySearchResult(entry=entry, score=score))
        
        return results
    
    def search_by_source(self, source: str, limit: int = 100) -> List[MemoryEntry]:
        """按来源搜索"""
        rows = self.conn.execute(
            "SELECT * FROM memories WHERE source = ? ORDER BY updated_at DESC LIMIT ?",
            (source, limit)
        ).fetchall()
        
        return [self._row_to_entry(row) for row in rows]
    
    def delete(self, entry_id: str):
        """删除记忆"""
        self.conn.execute("DELETE FROM memories WHERE id = ?", (entry_id,))
        self.conn.commit()
    
    def clear(self, source: Optional[str] = None):
        """清空记忆"""
        if source:
            self.conn.execute("DELETE FROM memories WHERE source = ?", (source,))
        else:
            self.conn.execute("DELETE FROM memories")
        self.conn.commit()
    
    def stats(self) -> MemoryStats:
        """统计"""
        total = self.conn.execute("SELECT COUNT(*) FROM memories").fetchone()[0]
        
        by_source = {}
        rows = self.conn.execute(
            "SELECT source, COUNT(*) as count FROM memories GROUP BY source"
        ).fetchall()
        for row in rows:
            by_source[row["source"]] = row["count"]
        
        last_sync = self.conn.execute(
            "SELECT value FROM metadata WHERE key = 'last_sync'"
        ).fetchone()
        
        return MemoryStats(
            total_entries=total,
            by_source=by_source,
            last_sync=last_sync["value"] if last_sync else None
        )
    
    def _row_to_entry(self, row: sqlite3.Row) -> MemoryEntry:
        """转换为 MemoryEntry"""
        embedding = None
        if row["embedding"]:
            import struct
            embedding = list(struct.unpack(f'{len(row["embedding"])//4}f', row["embedding"]))
        
        return MemoryEntry(
            id=row["id"],
            content=row["content"],
            source=row["source"],
            metadata=json.loads(row["metadata"]),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            embedding=embedding
        )
    
    def close(self):
        """关闭连接"""
        self.conn.close()


# ============================================
# 存储后端：JSON 文件（会话持久化）
# ============================================

class SessionStore:
    """会话存储（JSON 文件落盘）
    
    用于将会话历史保存到文件，支持：
    - 自动保存：每次添加消息时保存
    - 手动保存：调用 save() 方法
    - 加载恢复：启动时从文件加载
    """
    
    def __init__(self, data_dir: Optional[str] = None):
        if data_dir is None:
            data_dir = str(Path.home() / ".kuma-claw" / "sessions")
        
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # 会话数据缓存：{session_id: [messages]}
        self._sessions: Dict[str, List[Dict]] = {}
        self._lock = threading.Lock()
        
        # 启动时加载现有会话
        self._load_all_sessions()
    
    def _session_file(self, session_id: str) -> Path:
        """获取会话文件路径"""
        # 使用 session_id 的哈希值作为文件名，避免特殊字符
        safe_id = hashlib.sha256(session_id.encode()).hexdigest()[:16]
        return self.data_dir / f"{safe_id}.json"
    
    def _load_all_sessions(self):
        """加载所有会话文件"""
        for json_file in self.data_dir.glob("*.json"):
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    session_id = data.get('session_id', '')
                    messages = data.get('messages', [])
                    if session_id:
                        self._sessions[session_id] = messages
            except (json.JSONDecodeError, IOError) as e:
                print(f"Warning: Failed to load session {json_file}: {e}")
    
    def load_session(self, session_id: str) -> List[Dict]:
        """加载会话历史
        
        Args:
            session_id: 会话 ID
            
        Returns:
            消息列表，每条消息包含 {role, content, timestamp}
        """
        with self._lock:
            if session_id in self._sessions:
                return self._sessions[session_id].copy()
            
            # 尝试从文件加载
            session_file = self._session_file(session_id)
            if session_file.exists():
                try:
                    with open(session_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        messages = data.get('messages', [])
                        self._sessions[session_id] = messages
                        return messages.copy()
                except (json.JSONDecodeError, IOError) as e:
                    print(f"Warning: Failed to load session {session_id}: {e}")
            
            return []
    
    def save_session(self, session_id: str, messages: List[Dict]):
        """保存会话到文件
        
        Args:
            session_id: 会话 ID
            messages: 消息列表
        """
        with self._lock:
            self._sessions[session_id] = messages.copy()
            
            session_file = self._session_file(session_id)
            temp_file = session_file.with_suffix('.tmp')
            
            try:
                # 原子写入：先写临时文件，再重命名
                data = {
                    'session_id': session_id,
                    'messages': messages,
                    'last_updated': datetime.utcnow().isoformat(),
                    'message_count': len(messages)
                }
                
                with open(temp_file, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                
                # 原子替换
                temp_file.replace(session_file)
                
            except IOError as e:
                print(f"Error: Failed to save session {session_id}: {e}")
                # 清理临时文件
                if temp_file.exists():
                    try:
                        temp_file.unlink()
                    except:
                        pass
    
    def add_message(self, session_id: str, role: str, content: str):
        """添加会话消息并自动保存
        
        Args:
            session_id: 会话 ID
            role: 角色（user/assistant/system）
            content: 消息内容
        """
        with self._lock:
            if session_id not in self._sessions:
                self._sessions[session_id] = []
            
            message = {
                'role': role,
                'content': content,
                'timestamp': datetime.utcnow().isoformat()
            }
            
            self._sessions[session_id].append(message)
            
            # 异步保存（避免阻塞）
            # 为了简单，这里同步保存，可以改为异步
            self.save_session(session_id, self._sessions[session_id])
    
    def delete_session(self, session_id: str):
        """删除会话文件
        
        Args:
            session_id: 会话 ID
        """
        with self._lock:
            if session_id in self._sessions:
                del self._sessions[session_id]
            
            session_file = self._session_file(session_id)
            if session_file.exists():
                try:
                    session_file.unlink()
                except IOError as e:
                    print(f"Error: Failed to delete session {session_id}: {e}")
    
    def list_sessions(self) -> List[str]:
        """列出所有会话 ID
        
        Returns:
            会话 ID 列表
        """
        with self._lock:
            return list(self._sessions.keys())
    
    def get_session_info(self, session_id: str) -> Optional[Dict]:
        """获取会话元信息
        
        Args:
            session_id: 会话 ID
            
        Returns:
            会话信息 {session_id, message_count, last_updated, created_at}
        """
        with self._lock:
            if session_id not in self._sessions:
                session_file = self._session_file(session_id)
                if session_file.exists():
                    try:
                        with open(session_file, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                            return {
                                'session_id': session_id,
                                'message_count': data.get('message_count', 0),
                                'last_updated': data.get('last_updated'),
                                'created_at': data.get('created_at')
                            }
                    except:
                        pass
                return None
            
            messages = self._sessions[session_id]
            if not messages:
                return None
            
            return {
                'session_id': session_id,
                'message_count': len(messages),
                'last_updated': messages[-1].get('timestamp'),
                'created_at': messages[0].get('timestamp')
            }
    
    def clear_all(self):
        """清空所有会话文件"""
        with self._lock:
            self._sessions.clear()
            
            for json_file in self.data_dir.glob("*.json"):
                try:
                    json_file.unlink()
                except IOError as e:
                    print(f"Error: Failed to delete {json_file}: {e}")


# ============================================
# 记忆管理器
# ============================================

class MemoryManager:
    """记忆管理器
    
    整合 SQLite 和 JSON 文件存储：
    - SQLite：用于长期记忆、事实、偏好
    - JSON 文件：用于会话历史持久化
    """
    
    def __init__(self, store: Optional[MemoryStore] = None, session_store: Optional[SessionStore] = None):
        self.store = store or MemoryStore()
        self.session_store = session_store or SessionStore()
        self.embedding_provider = None
    
    def set_embedding_provider(self, provider):
        """设置嵌入向量提供者"""
        self.embedding_provider = provider
    
    # ============================================
    # 记忆操作
    # ============================================
    
    def remember(self, content: str, source: str = "fact", metadata: Optional[Dict] = None) -> MemoryEntry:
        """记住"""
        now = datetime.utcnow().isoformat()
        entry_id = hashlib.sha256(content.encode()).hexdigest()[:16]
        
        entry = MemoryEntry(
            id=entry_id,
            content=content,
            source=source,
            metadata=metadata or {},
            created_at=now,
            updated_at=now
        )
        
        # 生成嵌入向量
        if self.embedding_provider:
            try:
                entry.embedding = self.embedding_provider.embed(content)
            except Exception as e:
                print(f"Warning: Failed to generate embedding: {e}")
        
        self.store.add(entry)
        return entry
    
    def forget(self, entry_id: str):
        """忘记"""
        self.store.delete(entry_id)
    
    def search(self, query: str, limit: int = 10, min_score: float = 0.0) -> List[MemorySearchResult]:
        """搜索"""
        return self.store.search_fts(query, limit)
    
    def get_context(self, query: str, max_entries: int = 5) -> str:
        """获取上下文（用于 Agent）"""
        results = self.search(query, limit=max_entries)
        
        if not results:
            return ""
        
        context_parts = ["## 相关记忆"]
        for r in results:
            context_parts.append(f"- {r.entry.content}")
        
        return "\n".join(context_parts)
    
    # ============================================
    # 会话记忆（支持文件持久化）
    # ============================================
    
    def add_session_message(self, session_id: str, role: str, content: str):
        """添加会话消息（同时保存到 SQLite 和 JSON 文件）
        
        Args:
            session_id: 会话 ID
            role: 角色（user/assistant）
            content: 消息内容
        """
        # 保存到 SQLite（用于搜索）
        self.remember(
            content=f"[{role}] {content}",
            source=f"session:{session_id}",
            metadata={"role": role, "session_id": session_id}
        )
        
        # 保存到 JSON 文件（用于快速加载会话历史）
        self.session_store.add_message(session_id, role, content)
    
    def get_session_history(self, session_id: str, limit: int = 50) -> List[Dict]:
        """获取会话历史（优先从 JSON 文件加载）
        
        Args:
            session_id: 会话 ID
            limit: 返回数量
            
        Returns:
            消息列表，每条消息包含 {role, content}
        """
        # 优先从 JSON 文件加载（更快）
        messages = self.session_store.load_session(session_id)
        
        if messages:
            # 返回最近的 limit 条
            return messages[-limit:]
        
        # 回退到 SQLite
        entries = self.store.search_by_source(f"session:{session_id}", limit)
        return [
            {
                "role": e.metadata.get("role", "user"),
                "content": e.content.split("] ", 1)[1] if "] " in e.content else e.content
            }
            for e in entries
        ]
    
    def save_session(self, session_id: str):
        """手动保存会话到文件
        
        Args:
            session_id: 会话 ID
        """
        messages = self.get_session_history(session_id, limit=1000)
        self.session_store.save_session(session_id, messages)
    
    def clear_session(self, session_id: str):
        """清空会话（SQLite + JSON 文件）
        
        Args:
            session_id: 会话 ID
        """
        # 清空 SQLite
        self.store.clear(f"session:{session_id}")
        
        # 删除 JSON 文件
        self.session_store.delete_session(session_id)
    
    def list_sessions(self) -> List[Dict]:
        """列出所有会话
        
        Returns:
            会话信息列表
        """
        session_ids = self.session_store.list_sessions()
        return [
            info for info in 
            [self.session_store.get_session_info(sid) for sid in session_ids]
            if info is not None
        ]
    
    # ============================================
    # 长期记忆
    # ============================================
    
    def load_memory_files(self, workspace_dir: str):
        """加载 MEMORY.md 和 memory/*.md"""
        workspace = Path(workspace_dir)
        
        # MEMORY.md
        memory_file = workspace / "MEMORY.md"
        if memory_file.exists():
            content = memory_file.read_text()
            self.remember(content, source="memory:MEMORY.md")
        
        # memory/*.md
        memory_dir = workspace / "memory"
        if memory_dir.exists():
            for md_file in memory_dir.glob("*.md"):
                content = md_file.read_text()
                self.remember(content, source=f"memory:{md_file.name}")
        
        # 更新同步时间
        self.store.conn.execute(
            "INSERT OR REPLACE INTO metadata (key, value) VALUES ('last_sync', ?)",
            (datetime.utcnow().isoformat(),)
        )
        self.store.conn.commit()
    
    def stats(self) -> MemoryStats:
        """统计"""
        return self.store.stats()
    
    def session_stats(self) -> Dict:
        """会话统计"""
        sessions = self.list_sessions()
        total_messages = sum(s['message_count'] for s in sessions)
        
        return {
            'total_sessions': len(sessions),
            'total_messages': total_messages,
            'sessions': sessions
        }


# ============================================
# 嵌入向量提供者（简化版）
# ============================================

class SimpleEmbeddingProvider:
    """简单的嵌入向量提供者（使用 OpenAI）"""
    
    def __init__(self, api_key: Optional[str] = None, model: str = "text-embedding-3-small"):
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        self.model = model
    
    def embed(self, text: str) -> List[float]:
        """生成嵌入向量"""
        if not self.api_key:
            raise ValueError("OpenAI API key required")
        
        import requests
        
        response = requests.post(
            "https://api.openai.com/v1/embeddings",
            headers={"Authorization": f"Bearer {self.api_key}"},
            json={"model": self.model, "input": text}
        )
        
        response.raise_for_status()
        return response.json()["data"][0]["embedding"]


class GeminiEmbeddingProvider:
    """Gemini 嵌入向量提供者"""
    
    def __init__(self, api_key: Optional[str] = None, model: str = "text-embedding-004"):
        self.api_key = api_key or os.environ.get("GOOGLE_API_KEY")
        self.model = model
    
    def embed(self, text: str) -> List[float]:
        """生成嵌入向量"""
        if not self.api_key:
            raise ValueError("Google API key required")
        
        import requests
        
        response = requests.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:embedContent",
            headers={"Content-Type": "application/json"},
            params={"key": self.api_key},
            json={"content": {"parts": [{"text": text}]}}
        )
        
        response.raise_for_status()
        return response.json()["embedding"]["values"]


# ============================================
# 全局实例
# ============================================

memory_manager = MemoryManager()


if __name__ == "__main__":
    # 测试
    mm = MemoryManager()
    
    # 记住
    mm.remember("用户喜欢简洁的回复", source="preference")
    mm.remember("用户的项目是 Kuma Claw", source="fact")
    
    # 搜索
    results = mm.search("用户喜欢什么")
    for r in results:
        print(f"[{r.score:.2f}] {r.entry.content}")
    
    # 会话测试
    session_id = "test_session_001"
    mm.add_session_message(session_id, "user", "你好")
    mm.add_session_message(session_id, "assistant", "你好！有什么可以帮助你的？")
    
    # 加载会话
    history = mm.get_session_history(session_id)
    print(f"\n会话历史：{history}")
    
    # 列出会话
    sessions = mm.list_sessions()
    print(f"\n会话列表：{sessions}")
    
    # 统计
    print(f"\n记忆统计：{mm.stats()}")
    print(f"会话统计：{mm.session_stats()}")
