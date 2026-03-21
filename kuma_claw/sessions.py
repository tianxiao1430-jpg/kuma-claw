"""
Kuma Claw - SQLite 会话服务
==========================
持久化会话，线程安全
"""

import json
import logging
import sqlite3
import threading
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from google.adk.sessions import Session

logger = logging.getLogger("kuma_claw")


class SQLiteSessionService:
    """基于 SQLite 的会话服务（线程安全）"""

    def __init__(self, db_path: str | None = None):
        self.db_path = db_path or str(Path.home() / ".kuma-claw" / "sessions.db")
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)

        # 线程本地存储 + WAL 模式
        self._local = threading.local()
        self._lock = threading.Lock()
        self._init_db()
        logger.info(f"SQLite 会话服务已初始化：{self.db_path}")

    def _get_conn(self) -> sqlite3.Connection:
        """获取线程本地连接"""
        if not hasattr(self._local, 'conn') or self._local.conn is None:
            self._local.conn = sqlite3.connect(self.db_path, check_same_thread=False)
            self._local.conn.row_factory = sqlite3.Row
            self._local.conn.execute("PRAGMA journal_mode=WAL")
        return self._local.conn

    def _init_db(self):
        """初始化数据库"""
        conn = self._get_conn()
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                app_name TEXT NOT NULL,
                state TEXT DEFAULT '{}',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_sessions_user ON sessions(user_id);
            CREATE INDEX IF NOT EXISTS idx_sessions_app ON sessions(app_name);
        """)
        conn.commit()

    async def create_session(
        self, app_name: str, user_id: str,
        state: dict[str, Any] | None = None,
        session_id: str | None = None
    ) -> Session:
        """创建会话"""
        session_id = session_id or str(uuid.uuid4())
        now = datetime.utcnow().isoformat()
        state = state or {}

        with self._lock:
            self._get_conn().execute(
                "INSERT INTO sessions (id, user_id, app_name, state, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (session_id, user_id, app_name, json.dumps(state), now, now)
            )
            self._get_conn().commit()

        logger.debug(f"创建会话：id={session_id}")
        return Session(id=session_id, app_name=app_name, user_id=user_id,
                      state=state, created_at=now, updated_at=now)

    async def get_session(self, app_name: str, user_id: str, session_id: str) -> Session | None:
        """获取会话"""
        with self._lock:
            row = self._get_conn().execute(
                "SELECT * FROM sessions WHERE id = ? AND app_name = ? AND user_id = ?",
                (session_id, app_name, user_id)
            ).fetchone()

        if not row:
            return None

        return Session(
            id=row["id"], app_name=row["app_name"], user_id=row["user_id"],
            state=json.loads(row["state"]), created_at=row["created_at"],
            updated_at=row["updated_at"]
        )

    async def update_session(self, app_name: str, user_id: str,
                            session_id: str, state: dict[str, Any]) -> Session:
        """更新会话"""
        now = datetime.utcnow().isoformat()

        with self._lock:
            self._get_conn().execute(
                "UPDATE sessions SET state = ?, updated_at = ? "
                "WHERE id = ? AND app_name = ? AND user_id = ?",
                (json.dumps(state), now, session_id, app_name, user_id)
            )
            self._get_conn().commit()

        return Session(id=session_id, app_name=app_name, user_id=user_id,
                      state=state, created_at=now, updated_at=now)

    async def delete_session(self, app_name: str, user_id: str, session_id: str) -> bool:
        """删除会话"""
        with self._lock:
            cursor = self._get_conn().execute(
                "DELETE FROM sessions WHERE id = ? AND app_name = ? AND user_id = ?",
                (session_id, app_name, user_id)
            )
            self._get_conn().commit()

        deleted = cursor.rowcount > 0
        if deleted:
            logger.debug(f"删除会话：id={session_id}")
        return deleted

    async def list_sessions(self, app_name: str, user_id: str) -> list[Session]:
        """列出会话"""
        with self._lock:
            rows = self._get_conn().execute(
                "SELECT * FROM sessions WHERE app_name = ? AND user_id = ? "
                "ORDER BY updated_at DESC",
                (app_name, user_id)
            ).fetchall()

        return [
            Session(id=r["id"], app_name=r["app_name"], user_id=r["user_id"],
                   state=json.loads(r["state"]), created_at=r["created_at"],
                   updated_at=r["updated_at"])
            for r in rows
        ]

    async def close(self):
        """关闭连接"""
        if hasattr(self._local, 'conn') and self._local.conn:
            self._local.conn.close()
            self._local.conn = None
        logger.info("SQLite 会话服务已关闭")
