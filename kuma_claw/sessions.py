"""
Kuma Claw - SQLite 会话服务
==========================
持久化会话，线程安全

参考 ADK 的 InMemorySessionService 和 DatabaseSessionService 实现
"""

import json
import logging
import sqlite3
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from google.adk.events.event import Event
from google.adk.sessions import BaseSessionService, Session
from google.adk.sessions.base_session_service import GetSessionConfig, ListSessionsResponse

logger = logging.getLogger("kuma_claw")


class SQLiteSessionService(BaseSessionService):
    """基于 SQLite 的会话服务（线程安全）

    完整实现 ADK SessionService 接口，包括：
    - 持久化 session state
    - 持久化 events（对话历史）
    - 通过 append_event 方法保存对话轮次
    """

    def __init__(self, db_path: str | None = None):
        self.db_path = db_path or str(Path.home() / ".kuma-claw" / "sessions.db")
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)

        self._local = threading.local()
        self._lock = threading.Lock()
        self._init_db()
        logger.info(f"SQLite 会话服务已初始化：{self.db_path}")

    def _get_conn(self) -> sqlite3.Connection:
        """获取线程本地连接"""
        if not hasattr(self._local, "conn") or self._local.conn is None:
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
                events TEXT DEFAULT '[]',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS session_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                event_data TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_sessions_user ON sessions(user_id);
            CREATE INDEX IF NOT EXISTS idx_sessions_app ON sessions(app_name);
            CREATE INDEX IF NOT EXISTS idx_session_events_sid ON session_events(session_id);
        """)
        conn.commit()

    def _serialize_event(self, event: Event) -> dict:
        """将 Event 对象序列化为 dict（参考 ADK StorageEvent.from_event）"""
        try:
            return event.model_dump(exclude_none=True, mode="json")
        except (ValueError, TypeError, AttributeError) as e:
            logger.error(f"序列化 Event 失败：{e}")
            return {}

    def _deserialize_event(self, event_dict: dict) -> Event | None:
        """将 dict 反序列化为 Event 对象（参考 ADK StorageEvent.to_event）"""
        try:
            return Event.model_validate(event_dict)
        except (ValueError, TypeError, KeyError) as e:
            logger.error(f"反序列化 Event 失败：{e}")
            return None

    def _deserialize_events(self, events_json: str) -> list[Event]:
        """从 JSON 反序列化 events 列表"""
        try:
            events_data = json.loads(events_json) if events_json else []
            events = []
            for event_dict in events_data:
                event = self._deserialize_event(event_dict)
                if event:
                    events.append(event)
            return events
        except json.JSONDecodeError as e:
            logger.error(f"反序列化 events 失败：{e}")
            return []

    async def create_session(
        self,
        *,
        app_name: str,
        user_id: str,
        state: dict[str, Any] | None = None,
        session_id: str | None = None,
    ) -> Session:
        """创建会话"""
        session_id = session_id or str(uuid.uuid4())
        now_iso = datetime.now(timezone.utc).isoformat()
        now_ts = datetime.now(timezone.utc).timestamp()
        state = state or {}

        with self._lock:
            self._get_conn().execute(
                "INSERT INTO sessions (id, user_id, app_name, state, events, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (session_id, user_id, app_name, json.dumps(state), "[]", now_iso, now_iso),
            )
            self._get_conn().commit()

        logger.debug(f"创建会话：id={session_id}")
        return Session(
            id=session_id,
            app_name=app_name,
            user_id=user_id,
            state=state,
            events=[],
            last_update_time=now_ts,
        )

    async def get_session(
        self,
        *,
        app_name: str,
        user_id: str,
        session_id: str,
        config: GetSessionConfig | None = None,
    ) -> Session | None:
        """获取会话，包括完整的对话历史（events）"""
        with self._lock:
            row = (
                self._get_conn()
                .execute(
                    "SELECT * FROM sessions WHERE id = ? AND app_name = ? AND user_id = ?",
                    (session_id, app_name, user_id),
                )
                .fetchone()
            )

        if not row:
            return None

        updated_at_str = row["updated_at"]
        try:
            last_update_time = datetime.fromisoformat(updated_at_str).timestamp()
        except (ValueError, TypeError):
            last_update_time = 0.0

        # 优先从 session_events 表加载（新格式），回退到 events 列（旧格式）
        with self._lock:
            event_rows = (
                self._get_conn()
                .execute(
                    "SELECT event_data FROM session_events WHERE session_id = ? ORDER BY id",
                    (session_id,),
                )
                .fetchall()
            )
        if event_rows:
            events = []
            for er in event_rows:
                ev = self._deserialize_event(json.loads(er["event_data"]))
                if ev:
                    events.append(ev)
        else:
            events = self._deserialize_events(row["events"])

        # 应用 config 过滤
        if config:
            if hasattr(config, "num_recent_events") and config.num_recent_events:
                events = events[-config.num_recent_events :]
            if hasattr(config, "after_timestamp") and config.after_timestamp:
                events = [e for e in events if e.timestamp >= config.after_timestamp]

        return Session(
            id=row["id"],
            app_name=row["app_name"],
            user_id=row["user_id"],
            state=json.loads(row["state"]),
            events=events,
            last_update_time=last_update_time,
        )

    async def list_sessions(
        self, *, app_name: str, user_id: str | None = None
    ) -> ListSessionsResponse:
        """列出会话"""
        with self._lock:
            if user_id:
                rows = (
                    self._get_conn()
                    .execute(
                        "SELECT * FROM sessions WHERE app_name = ? AND user_id = ? "
                        "ORDER BY updated_at DESC",
                        (app_name, user_id),
                    )
                    .fetchall()
                )
            else:
                rows = (
                    self._get_conn()
                    .execute(
                        "SELECT * FROM sessions WHERE app_name = ? ORDER BY updated_at DESC",
                        (app_name,),
                    )
                    .fetchall()
                )

        sessions = [
            Session(
                id=r["id"],
                app_name=r["app_name"],
                user_id=r["user_id"],
                state=json.loads(r["state"]),
                events=[],  # 列表不需要返回 events
                last_update_time=datetime.fromisoformat(r["updated_at"]).timestamp()
                if r["updated_at"]
                else 0.0,
            )
            for r in rows
        ]
        return ListSessionsResponse(sessions=sessions)

    async def append_event(self, session: Session, event: Event) -> Event:
        """将事件持久化到数据库

        这是 ADK 调用的核心方法，用于保存对话历史。
        参考 ADK InMemorySessionService._append_event_impl
        """
        # 调用父类实现（更新内存中的 session）
        await super().append_event(session=session, event=event)

        if event.partial:
            return event

        # 持久化到数据库：只 INSERT 新 event（O(1) 而非 O(n)）
        now_iso = datetime.now(timezone.utc).isoformat()
        event_data = json.dumps(self._serialize_event(event))

        with self._lock:
            conn = self._get_conn()
            conn.execute(
                "INSERT INTO session_events (session_id, event_data, created_at) VALUES (?, ?, ?)",
                (session.id, event_data, now_iso),
            )
            cursor = conn.execute(
                "UPDATE sessions SET state = ?, updated_at = ? WHERE id = ? AND app_name = ? AND user_id = ?",
                (json.dumps(session.state), now_iso, session.id, session.app_name, session.user_id),
            )
            conn.commit()

        if cursor.rowcount == 0:
            logger.warning(f"持久化事件失败：会话 {session.id} 不存在")
        else:
            logger.debug(f"持久化事件到会话：id={session.id}, events_count={len(session.events)}")

        return event

    async def delete_session(self, *, app_name: str, user_id: str, session_id: str) -> None:
        """删除会话"""
        with self._lock:
            cursor = self._get_conn().execute(
                "DELETE FROM sessions WHERE id = ? AND app_name = ? AND user_id = ?",
                (session_id, app_name, user_id),
            )
            self._get_conn().commit()

        if cursor.rowcount > 0:
            logger.debug(f"删除会话：id={session_id}")

    async def close(self):
        """关闭连接"""
        if hasattr(self._local, "conn") and self._local.conn:
            self._local.conn.close()
            self._local.conn = None
        logger.info("SQLite 会话服务已关闭")
