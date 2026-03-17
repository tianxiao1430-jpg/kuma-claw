"""
Kuma Claw - SQLite 会话服务
==========================
将会话数据持久化到 SQLite，解决重启后会话丢失问题
"""

import os
import json
import sqlite3
import asyncio
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime
from dataclasses import dataclass, asdict

from google.adk.sessions import Session
import logging

logger = logging.getLogger("kuma_claw")


@dataclass
class SessionData:
    """会话数据"""
    id: str
    user_id: str
    app_name: str
    state: Dict[str, Any]
    created_at: str
    updated_at: str


class SQLiteSessionService:
    """基于 SQLite 的会话服务（持久化）"""
    
    def __init__(self, db_path: Optional[str] = None):
        if db_path is None:
            db_path = str(Path.home() / ".kuma-claw" / "sessions.db")
        
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        
        # SQLite 连接（支持多线程）
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._lock = asyncio.Lock()
        
        self._init_db()
        logger.info(f"SQLite 会话服务已初始化：{db_path}")
    
    def _init_db(self):
        """初始化数据库"""
        self.conn.executescript("""
            -- 会话表
            CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                app_name TEXT NOT NULL,
                state TEXT DEFAULT '{}',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            
            -- 索引：按用户查询
            CREATE INDEX IF NOT EXISTS idx_sessions_user 
            ON sessions(user_id);
            
            -- 索引：按应用查询
            CREATE INDEX IF NOT EXISTS idx_sessions_app 
            ON sessions(app_name);
        """)
        self.conn.commit()
    
    async def create_session(
        self,
        app_name: str,
        user_id: str,
        state: Optional[Dict[str, Any]] = None,
        session_id: Optional[str] = None
    ) -> Session:
        """创建会话
        
        Args:
            app_name: 应用名称
            user_id: 用户 ID
            state: 初始状态
            session_id: 会话 ID（可选，不传则自动生成）
        
        Returns:
            Session 对象
        """
        import uuid
        
        session_id = session_id or str(uuid.uuid4())
        now = datetime.utcnow().isoformat()
        state = state or {}
        
        async with self._lock:
            self.conn.execute(
                """
                INSERT INTO sessions (id, user_id, app_name, state, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (session_id, user_id, app_name, json.dumps(state), now, now)
            )
            self.conn.commit()
        
        logger.debug(f"创建会话：id={session_id}, user={user_id}, app={app_name}")
        
        return Session(
            id=session_id,
            app_name=app_name,
            user_id=user_id,
            state=state,
            created_at=now,
            updated_at=now
        )
    
    async def get_session(
        self,
        app_name: str,
        user_id: str,
        session_id: str
    ) -> Optional[Session]:
        """获取会话
        
        Args:
            app_name: 应用名称
            user_id: 用户 ID
            session_id: 会话 ID
        
        Returns:
            Session 对象，不存在则返回 None
        """
        async with self._lock:
            cursor = self.conn.execute(
                """
                SELECT id, user_id, app_name, state, created_at, updated_at
                FROM sessions
                WHERE id = ? AND app_name = ? AND user_id = ?
                """,
                (session_id, app_name, user_id)
            )
            row = cursor.fetchone()
        
        if not row:
            return None
        
        return Session(
            id=row["id"],
            app_name=row["app_name"],
            user_id=row["user_id"],
            state=json.loads(row["state"]),
            created_at=row["created_at"],
            updated_at=row["updated_at"]
        )
    
    async def update_session(
        self,
        app_name: str,
        user_id: str,
        session_id: str,
        state: Dict[str, Any]
    ) -> Session:
        """更新会话状态
        
        Args:
            app_name: 应用名称
            user_id: 用户 ID
            session_id: 会话 ID
            state: 新状态
        
        Returns:
            更新后的 Session 对象
        """
        now = datetime.utcnow().isoformat()
        
        async with self._lock:
            self.conn.execute(
                """
                UPDATE sessions
                SET state = ?, updated_at = ?
                WHERE id = ? AND app_name = ? AND user_id = ?
                """,
                (json.dumps(state), now, session_id, app_name, user_id)
            )
            self.conn.commit()
        
        return Session(
            id=session_id,
            app_name=app_name,
            user_id=user_id,
            state=state,
            created_at=now,  # We don't have the original created_at here
            updated_at=now
        )
    
    async def delete_session(
        self,
        app_name: str,
        user_id: str,
        session_id: str
    ) -> bool:
        """删除会话
        
        Args:
            app_name: 应用名称
            user_id: 用户 ID
            session_id: 会话 ID
        
        Returns:
            是否成功删除
        """
        async with self._lock:
            cursor = self.conn.execute(
                """
                DELETE FROM sessions
                WHERE id = ? AND app_name = ? AND user_id = ?
                """,
                (session_id, app_name, user_id)
            )
            self.conn.commit()
        
        deleted = cursor.rowcount > 0
        if deleted:
            logger.debug(f"删除会话：id={session_id}")
        
        return deleted
    
    async def list_sessions(
        self,
        app_name: str,
        user_id: str
    ) -> List[Session]:
        """列出用户的所有会话
        
        Args:
            app_name: 应用名称
            user_id: 用户 ID
        
        Returns:
            Session 列表
        """
        async with self._lock:
            cursor = self.conn.execute(
                """
                SELECT id, user_id, app_name, state, created_at, updated_at
                FROM sessions
                WHERE app_name = ? AND user_id = ?
                ORDER BY updated_at DESC
                """,
                (app_name, user_id)
            )
            rows = cursor.fetchall()
        
        return [
            Session(
                id=row["id"],
                app_name=row["app_name"],
                user_id=row["user_id"],
                state=json.loads(row["state"]),
                created_at=row["created_at"],
                updated_at=row["updated_at"]
            )
            for row in rows
        ]
    
    async def close(self):
        """关闭数据库连接"""
        self.conn.close()
        logger.info("SQLite 会话服务已关闭")
