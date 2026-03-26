"""
Kuma Claw Gateway - Unified Session Manager
============================================

Wraps SQLiteSessionService to provide a simple key-based session interface.
"""

import logging
from dataclasses import dataclass

from kuma_claw.sessions import SQLiteSessionService

logger = logging.getLogger("kuma_claw.gateway")


@dataclass(frozen=True)
class SessionKey:
    """Identifies a session by channel, user, and scope."""

    channel: str
    user_id: str
    scope: str

    def __str__(self) -> str:
        return f"{self.channel}:{self.user_id}:{self.scope}"


class UnifiedSessionManager:
    """Unified session manager backed by SQLiteSessionService."""

    def __init__(self, app_name: str = "kuma-claw", db_path: str | None = None):
        self.app_name = app_name
        self.session_service = SQLiteSessionService(db_path=db_path)
        self._sessions: dict[str, str] = {}  # key_str -> session_id

    async def get_or_create(self, key: SessionKey) -> str:
        """Get or create a session for the given key. Returns the session_id."""
        key_str = str(key)

        if key_str in self._sessions:
            return self._sessions[key_str]

        try:
            sessions_response = await self.session_service.list_sessions(
                app_name=self.app_name, user_id=key.user_id
            )
            existing_sessions = (
                sessions_response.sessions if hasattr(sessions_response, "sessions") else []
            )

            if existing_sessions:
                session = max(existing_sessions, key=lambda s: getattr(s, "last_update_time", 0))
                session_id = session.id if hasattr(session, "id") else str(session)
            else:
                session = await self.session_service.create_session(
                    app_name=self.app_name, user_id=key.user_id, state={}
                )
                session_id = session.id if hasattr(session, "id") else str(session)

            self._sessions[key_str] = session_id
            logger.debug(f"Session ready: key={key_str}, session_id={session_id}")
            return session_id

        except (RuntimeError, ValueError, OSError) as e:
            logger.error(f"Failed to get/create session for {key_str}: {e}")
            raise

    async def clear(self, key: SessionKey) -> bool:
        """Clear (delete) the session for the given key."""
        key_str = str(key)

        if key_str not in self._sessions:
            return False

        session_id = self._sessions[key_str]
        try:
            await self.session_service.delete_session(
                app_name=self.app_name, user_id=key.user_id, session_id=session_id
            )
            del self._sessions[key_str]
            logger.debug(f"Session cleared: key={key_str}")
            return True
        except (RuntimeError, ValueError, OSError) as e:
            logger.error(f"Failed to clear session {key_str}: {e}")
            return False

    async def close(self):
        """Close the underlying session service."""
        await self.session_service.close()
