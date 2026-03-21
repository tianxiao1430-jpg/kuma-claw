"""
渠道模块测试
============
"""
import pytest


class TestSessionManager:
    """会话管理器测试"""

    def test_session_manager_init(self):
        """测试会话管理器初始化"""
        from kuma_claw.channels.base import SessionManager

        manager = SessionManager()

        assert manager.app_name == "kuma-claw"
        assert manager.user_sessions == {}

    def test_session_manager_custom_app_name(self):
        """测试自定义应用名称"""
        from kuma_claw.channels.base import SessionManager

        manager = SessionManager(app_name="test-app")

        assert manager.app_name == "test-app"


class TestLLMAPIError:
    """LLM API 错误测试"""

    def test_llm_api_error_creation(self):
        """测试 LLM API 错误创建"""
        from kuma_claw.channels.base import LLMAPIError

        error = LLMAPIError("测试错误")

        assert isinstance(error, Exception)
        assert str(error) == "测试错误"

    def test_llm_api_error_inheritance(self):
        """测试 LLM API 错误继承"""
        from kuma_claw.channels.base import LLMAPIError

        error = LLMAPIError("测试")

        assert isinstance(error, Exception)


class TestChannelHandler:
    """渠道处理器测试"""

    def test_channel_handler_abstract(self):
        """测试渠道处理器是抽象类"""
        from kuma_claw.channels.base import ChannelHandler

        # 抽象类不能直接实例化
        with pytest.raises(TypeError):
            ChannelHandler("test", None)
