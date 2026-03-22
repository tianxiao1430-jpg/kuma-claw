"""会话服务测试"""

import time

import pytest

from kuma_claw.sessions import SQLiteSessionService


@pytest.fixture
async def session_service():
    """创建测试用会话服务"""
    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = f"{tmpdir}/test_sessions.db"
        service = SQLiteSessionService(db_path=db_path)
        yield service
        await service.close()


class TestSQLiteSessionService:
    """SQLiteSessionService 测试"""

    @pytest.mark.asyncio
    async def test_create_and_get_session(self, session_service):
        """测试创建和获取会话"""
        session = await session_service.create_session(
            app_name="test_app", user_id="test_user", state={"key": "value"}
        )

        assert session.id is not None
        assert session.app_name == "test_app"
        assert session.user_id == "test_user"
        assert session.events == []

        # 获取会话
        retrieved = await session_service.get_session(
            app_name="test_app", user_id="test_user", session_id=session.id
        )

        assert retrieved is not None
        assert retrieved.id == session.id
        assert retrieved.state == {"key": "value"}

    @pytest.mark.asyncio
    async def test_append_event(self, session_service):
        """测试 append_event 方法"""
        session = await session_service.create_session(app_name="test_app", user_id="test_user")

        # 创建一个模拟的 Event 对象
        from google.adk.events.event import Event
        from google.genai import types

        content = types.Content(role="user", parts=[types.Part(text="Hello")])
        event = Event(
            author="user",
            content=content,
            timestamp=time.time(),
        )

        # 调用 append_event
        await session_service.append_event(session, event)

        # 验证 events 已更新
        assert len(session.events) == 1
        assert session.events[0].content.role == "user"

        # 重新获取会话，验证持久化
        retrieved = await session_service.get_session(
            app_name="test_app", user_id="test_user", session_id=session.id
        )
        assert retrieved is not None
        assert len(retrieved.events) == 1

    @pytest.mark.asyncio
    async def test_delete_session(self, session_service):
        """测试删除会话"""
        session = await session_service.create_session(app_name="test_app", user_id="test_user")

        await session_service.delete_session(
            app_name="test_app", user_id="test_user", session_id=session.id
        )

        # 验证已删除
        retrieved = await session_service.get_session(
            app_name="test_app", user_id="test_user", session_id=session.id
        )
        assert retrieved is None

    @pytest.mark.asyncio
    async def test_list_sessions(self, session_service):
        """测试列出会话"""
        await session_service.create_session(
            app_name="test_app", user_id="user1", session_id="session1"
        )
        await session_service.create_session(
            app_name="test_app", user_id="user1", session_id="session2"
        )

        response = await session_service.list_sessions(app_name="test_app", user_id="user1")

        assert len(response.sessions) == 2
