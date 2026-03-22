"""
Gateway 模块测试（原渠道模块测试，已迁移至 Gateway 架构）
============
"""

import pytest


class TestUnifiedSessionManager:
    """统一会话管理器测试"""

    def test_session_manager_init(self):
        """测试会话管理器初始化"""
        from kuma_claw.gateway.session_manager import UnifiedSessionManager

        manager = UnifiedSessionManager()

        assert manager.app_name == "kuma-claw"
        assert manager._sessions == {}

    def test_session_manager_custom_app_name(self):
        """测试自定义应用名称"""
        from kuma_claw.gateway.session_manager import UnifiedSessionManager

        manager = UnifiedSessionManager(app_name="test-app")

        assert manager.app_name == "test-app"


class TestLLMAPIError:
    """LLM API 错误测试"""

    def test_llm_api_error_creation(self):
        """测试 LLM API 错误创建"""
        from kuma_claw.gateway.agent_runner import LLMAPIError

        error = LLMAPIError("测试错误")

        assert isinstance(error, Exception)
        assert str(error) == "测试错误"

    def test_llm_api_error_inheritance(self):
        """测试 LLM API 错误继承"""
        from kuma_claw.gateway.agent_runner import LLMAPIError

        error = LLMAPIError("测试")

        assert isinstance(error, Exception)


class TestSessionKey:
    """SessionKey 测试"""

    def test_session_key_str(self):
        """测试 SessionKey 字符串表示"""
        from kuma_claw.gateway.session_manager import SessionKey

        key = SessionKey(channel="telegram", user_id="123", scope="456")

        assert str(key) == "telegram:123:456"

    def test_session_key_frozen(self):
        """测试 SessionKey 不可变"""
        from kuma_claw.gateway.session_manager import SessionKey

        key = SessionKey(channel="telegram", user_id="123", scope="456")

        with pytest.raises(AttributeError):
            key.channel = "slack"
