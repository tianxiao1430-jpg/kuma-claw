"""
Kuma Claw - 配置管理
==================
"""

import os
import json
from pathlib import Path
from typing import Optional, Dict

# 配置文件路径
OLD_CONFIG_DIR = Path.home() / ".adk-claw"
CONFIG_DIR = Path.home() / ".kuma-claw"

if OLD_CONFIG_DIR.exists() and not CONFIG_DIR.exists():
    import shutil
    try:
        shutil.copytree(str(OLD_CONFIG_DIR), str(CONFIG_DIR))
        print(f"📦 [Kuma Claw] 自动迁移旧配置：{OLD_CONFIG_DIR} -> {CONFIG_DIR}")
    except Exception as e:
        print(f"⚠️ [Kuma Claw] 配置迁移失败：{e}")

CONFIG_FILE = CONFIG_DIR / "config.json"
SECRETS_FILE = CONFIG_DIR / "secrets.json"


def ensure_config_dir():
    """确保配置目录存在"""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)


class Config:
    """配置管理器"""
    
    def __init__(self):
        ensure_config_dir()
        self.config = self._load_config()
        self.secrets = self._load_secrets()
    
    def _load_config(self) -> Dict:
        """加载配置"""
        if CONFIG_FILE.exists():
            with open(CONFIG_FILE, "r") as f:
                return json.load(f)
        return {
            "model": "gemini-3.1-flash",
            "channels": {
                "slack": {"enabled": False},
                "telegram": {"enabled": False}
            }
        }
    
    def _load_secrets(self) -> Dict:
        """加载密钥"""
        if SECRETS_FILE.exists():
            with open(SECRETS_FILE, "r") as f:
                return json.load(f)
        return {}
    
    def save(self):
        """保存配置"""
        with open(CONFIG_FILE, "w") as f:
            json.dump(self.config, f, indent=2)
        
        with open(SECRETS_FILE, "w") as f:
            json.dump(self.secrets, f, indent=2)
    
    # ============================================
    # API Keys
    # ============================================
    
    def set_google_api_key(self, key: str):
        """设置 Google API Key"""
        self.secrets["google_api_key"] = key
        self.save()
    
    def get_google_api_key(self) -> Optional[str]:
        """获取 Google API Key"""
        return self.secrets.get("google_api_key") or os.environ.get("GOOGLE_API_KEY")
    
    def set_openai_api_key(self, key: str):
        """设置 OpenAI API Key"""
        self.secrets["openai_api_key"] = key
        self.save()
    
    def get_openai_api_key(self) -> Optional[str]:
        """获取 OpenAI API Key"""
        return self.secrets.get("openai_api_key") or os.environ.get("OPENAI_API_KEY")
    
    def set_anthropic_api_key(self, key: str):
        """设置 Anthropic API Key"""
        self.secrets["anthropic_api_key"] = key
        self.save()
    
    def get_anthropic_api_key(self) -> Optional[str]:
        """获取 Anthropic API Key"""
        return self.secrets.get("anthropic_api_key") or os.environ.get("ANTHROPIC_API_KEY")
    
    # ============================================
    # Slack
    # ============================================
    
    def set_slack_tokens(self, bot_token: str, app_token: str):
        """设置 Slack Tokens"""
        self.secrets["slack_bot_token"] = bot_token
        self.secrets["slack_app_token"] = app_token
        self.config["channels"]["slack"]["enabled"] = True
        self.save()
    
    def get_slack_bot_token(self) -> Optional[str]:
        """获取 Slack Bot Token"""
        return self.secrets.get("slack_bot_token") or os.environ.get("SLACK_BOT_TOKEN")
    
    def get_slack_app_token(self) -> Optional[str]:
        """获取 Slack App Token"""
        return self.secrets.get("slack_app_token") or os.environ.get("SLACK_APP_TOKEN")
    
    def is_slack_enabled(self) -> bool:
        """Slack 是否启用"""
        return self.config["channels"]["slack"]["enabled"]
    
    # ============================================
    # Telegram
    # ============================================
    
    def set_telegram_token(self, token: str):
        """设置 Telegram Token"""
        self.secrets["telegram_token"] = token
        self.config["channels"]["telegram"]["enabled"] = True
        self.save()
    
    def get_telegram_token(self) -> Optional[str]:
        """获取 Telegram Token"""
        return self.secrets.get("telegram_token") or os.environ.get("TELEGRAM_BOT_TOKEN")
    
    def is_telegram_enabled(self) -> bool:
        """Telegram 是否启用"""
        return self.config["channels"]["telegram"]["enabled"]
    
    # ============================================
    # 模型
    # ============================================
    
    def set_model(self, model: str):
        """设置模型"""
        self.config["model"] = model
        self.save()
    
    def get_model(self) -> str:
        """获取模型"""
        return self.config.get("model", "gemini-3.1-flash")
    
    # ============================================
    # OAuth
    # ============================================
    
    def set_google_oauth(self, client_id: str, client_secret: str):
        """设置 Google OAuth"""
        self.secrets["google_oauth_client_id"] = client_id
        self.secrets["google_oauth_client_secret"] = client_secret
        self.save()
    
    def get_google_oauth_client_id(self) -> Optional[str]:
        """获取 Google OAuth Client ID"""
        return self.secrets.get("google_oauth_client_id")
    
    def get_google_oauth_client_secret(self) -> Optional[str]:
        """获取 Google OAuth Client Secret"""
        return self.secrets.get("google_oauth_client_secret")


# 全局配置实例
config = Config()
