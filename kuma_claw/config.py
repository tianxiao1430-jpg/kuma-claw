"""
Kuma Claw - 配置管理
==================
支持 keyring 安全存储
"""

import json
import os
from pathlib import Path

# 配置目录
CONFIG_DIR = Path.home() / ".kuma-claw"
CONFIG_FILE = CONFIG_DIR / "config.json"

# 尝试导入 keyring
try:
    import keyring

    KEYRING_AVAILABLE = True
except ImportError:
    KEYRING_AVAILABLE = False

# 服务名称（用于 keyring）
KEYRING_SERVICE = "kuma-claw"


def ensure_config_dir():
    """确保配置目录存在"""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)


class Config:
    """配置管理器（支持安全存储）"""

    def __init__(self):
        ensure_config_dir()
        self.config = self._load_config()

    def _load_config(self) -> dict:
        """加载配置"""
        if CONFIG_FILE.exists():
            with CONFIG_FILE.open("r") as f:
                return json.load(f)
        return {
            "model": "gemini-3.1-flash",
            "channels": {"slack": {"enabled": False}, "telegram": {"enabled": False}},
        }

    def save(self):
        """保存配置"""
        with CONFIG_FILE.open("w") as f:
            json.dump(self.config, f, indent=2)

    # ============================================
    # 安全存储（优先 keyring，回退环境变量）
    # ============================================

    def _get_secret(self, key: str) -> str | None:
        """获取密钥（keyring > 环境变量）"""
        # 1. 尝试 keyring
        if KEYRING_AVAILABLE:
            try:
                value = keyring.get_password(KEYRING_SERVICE, key)
                if value:
                    return value
            except Exception:
                pass

        # 2. 回退环境变量
        return os.environ.get(key.upper())

    def _set_secret(self, key: str, value: str):
        """存储密钥（keyring）"""
        if KEYRING_AVAILABLE:
            try:
                keyring.set_password(KEYRING_SERVICE, key, value)
                return
            except Exception:
                pass

        # 回退：打印警告
        print(f"⚠️ Warning: keyring not available, {key} not stored securely")

    # ============================================
    # API Keys
    # ============================================

    def set_google_api_key(self, key: str):
        self._set_secret("google_api_key", key)

    def get_google_api_key(self) -> str | None:
        return self._get_secret("google_api_key")

    def set_openai_api_key(self, key: str):
        self._set_secret("openai_api_key", key)

    def get_openai_api_key(self) -> str | None:
        return self._get_secret("openai_api_key")

    def set_anthropic_api_key(self, key: str):
        self._set_secret("anthropic_api_key", key)

    def get_anthropic_api_key(self) -> str | None:
        return self._get_secret("anthropic_api_key")

    # ============================================
    # Slack
    # ============================================

    def set_slack_tokens(self, bot_token: str, app_token: str):
        self._set_secret("slack_bot_token", bot_token)
        self._set_secret("slack_app_token", app_token)
        self.config["channels"]["slack"]["enabled"] = True
        self.save()

    def get_slack_bot_token(self) -> str | None:
        return self._get_secret("slack_bot_token")

    def get_slack_app_token(self) -> str | None:
        return self._get_secret("slack_app_token")

    def is_slack_enabled(self) -> bool:
        return self.config["channels"]["slack"]["enabled"]

    # ============================================
    # Telegram
    # ============================================

    def set_telegram_token(self, token: str):
        self._set_secret("telegram_bot_token", token)
        self.config["channels"]["telegram"]["enabled"] = True
        self.save()

    def get_telegram_token(self) -> str | None:
        return self._get_secret("telegram_bot_token")

    def is_telegram_enabled(self) -> bool:
        return self.config["channels"]["telegram"]["enabled"]

    # ============================================
    # 模型
    # ============================================

    def set_model(self, model: str):
        self.config["model"] = model
        self.save()

    def get_model(self) -> str:
        return self.config.get("model", "gemini-3.1-flash")

    # ============================================
    # OAuth
    # ============================================

    def set_google_oauth(self, client_id: str, client_secret: str):
        self._set_secret("google_oauth_client_id", client_id)
        self._set_secret("google_oauth_client_secret", client_secret)

    def get_google_oauth_client_id(self) -> str | None:
        return self._get_secret("google_oauth_client_id")

    def get_google_oauth_client_secret(self) -> str | None:
        return self._get_secret("google_oauth_client_secret")


# 全局配置实例
config = Config()
