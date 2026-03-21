"""记忆系统测试"""

import pytest

from kuma_claw.memory import MemoryManager, MemoryStore


@pytest.fixture
def memory_manager():
    """创建测试用记忆管理器"""
    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = f"{tmpdir}/test_memory.db"
        store = MemoryStore(db_path=db_path)
        manager = MemoryManager(store=store)
        yield manager
        store.close()


class TestMemoryStore:
    """MemoryStore 测试"""

    def test_remember_and_recall(self, memory_manager):
        """测试记忆和回忆"""
        # 记住
        entry = memory_manager.remember("用户喜欢简洁回复", source="preference")
        assert entry.content == "用户喜欢简洁回复"

        # 回忆
        results = memory_manager.search("简洁", limit=5)
        assert len(results) > 0
        assert "简洁" in results[0].entry.content

    def test_forget(self, memory_manager):
        """测试忘记"""
        entry = memory_manager.remember("测试内容", source="fact")
        memory_manager.forget(entry.id)

        results = memory_manager.search("测试内容")
        assert len(results) == 0

    def test_stats(self, memory_manager):
        """测试统计"""
        memory_manager.remember("事实1", source="fact")
        memory_manager.remember("偏好1", source="preference")

        stats = memory_manager.stats()
        assert stats.total_entries >= 2
        assert "fact" in stats.by_source
        assert "preference" in stats.by_source


class TestSessionStore:
    """SessionStore 测试"""

    def test_session_messages(self, memory_manager):
        """测试会话消息"""
        session_id = "test_session_001"

        memory_manager.add_session_message(session_id, "user", "你好")
        memory_manager.add_session_message(session_id, "assistant", "你好！")

        history = memory_manager.get_session_history(session_id)
        assert len(history) == 2
        assert history[0]["role"] == "user"
        assert history[1]["role"] == "assistant"

    def test_clear_session(self, memory_manager):
        """测试清空会话"""
        session_id = "test_session_002"

        memory_manager.add_session_message(session_id, "user", "测试")
        memory_manager.clear_session(session_id)

        history = memory_manager.get_session_history(session_id)
        assert len(history) == 0
