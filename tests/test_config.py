"""配置管理测试"""

import pytest

from kuma_claw.config import Config


@pytest.fixture
def config():
    """创建测试用配置"""
    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        import os

        original_home = os.environ.get("HOME")
        os.environ["HOME"] = tmpdir

        from kuma_claw import config as config_module

        config_module.CONFIG_DIR = f"{tmpdir}/.kuma-claw"
        config_module.CONFIG_FILE = f"{tmpdir}/.kuma-claw/config.json"

        yield Config()

        if original_home:
            os.environ["HOME"] = original_home


class TestConfig:
    """Config 测试"""

    def test_get_default_model(self, config):
        """测试获取默认模型"""
        model = config.get_model()
        assert model == "gemini-3.1-flash"

    def test_set_model(self, config):
        """测试设置模型"""
        config.set_model("openai/gpt-4")
        assert config.get_model() == "openai/gpt-4"

    def test_google_api_key_from_env(self, config, monkeypatch):
        """测试从环境变量获取 API key"""
        monkeypatch.setenv("GOOGLE_API_KEY", "test_key")
        assert config.get_google_api_key() == "test_key"

    def test_slack_tokens(self, config):
        """测试 Slack tokens"""
        config.set_slack_tokens("bot_token", "app_token")
        assert config.is_slack_enabled() is True

    def test_telegram_token(self, config):
        """测试 Telegram token"""
        config.set_telegram_token("telegram_token")
        assert config.is_telegram_enabled() is True
