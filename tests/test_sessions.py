"""会话服务测试"""
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
            app_name="test_app",
            user_id="test_user",
            state={"key": "value"}
        )
        
        assert session.id is not None
        assert session.app_name == "test_app"
        assert session.user_id == "test_user"
        
        # 获取会话
        retrieved = await session_service.get_session(
            app_name="test_app",
            user_id="test_user",
            session_id=session.id
        )
        
        assert retrieved is not None
        assert retrieved.id == session.id
    
    @pytest.mark.asyncio
    async def test_update_session(self, session_service):
        """测试更新会话"""
        session = await session_service.create_session(
            app_name="test_app",
            user_id="test_user"
        )
        
        updated = await session_service.update_session(
            app_name="test_app",
            user_id="test_user",
            session_id=session.id,
            state={"new_key": "new_value"}
        )
        
        assert updated.state == {"new_key": "new_value"}
    
    @pytest.mark.asyncio
    async def test_delete_session(self, session_service):
        """测试删除会话"""
        session = await session_service.create_session(
            app_name="test_app",
            user_id="test_user"
        )
        
        deleted = await session_service.delete_session(
            app_name="test_app",
            user_id="test_user",
            session_id=session.id
        )
        
        assert deleted is True
        
        # 验证已删除
        retrieved = await session_service.get_session(
            app_name="test_app",
            user_id="test_user",
            session_id=session.id
        )
        assert retrieved is None
    
    @pytest.mark.asyncio
    async def test_list_sessions(self, session_service):
        """测试列出会话"""
        await session_service.create_session(
            app_name="test_app",
            user_id="user1",
            session_id="session1"
        )
        await session_service.create_session(
            app_name="test_app",
            user_id="user1",
            session_id="session2"
        )
        
        sessions = await session_service.list_sessions(
            app_name="test_app",
            user_id="user1"
        )
        
        assert len(sessions) == 2
