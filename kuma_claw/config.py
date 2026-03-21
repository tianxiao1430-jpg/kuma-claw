"""
Kuma Claw - 配置管理
==================
支持 keyring 安全存储，带加密文件回退
"""

import base64
import hashlib
import json
import os
import uuid
from pathlib import Path

# 配置目录
CONFIG_DIR = Path.home() / ".kuma-claw"
CONFIG_FILE = CONFIG_DIR / "config.json"
SECRETS_FILE = CONFIG_DIR / "secrets.enc"

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


def _get_machine_key() -> bytes:
    """获取基于机器标识的加密密钥

    使用机器 UUID 和用户名生成唯一密钥
    这确保密钥只能在当前机器/用户上解密
    """
    machine_id = uuid.getnode()  # 机器唯一标识
    user = os.environ.get("USER", "default")
    combined = f"{machine_id}:{user}:kuma-claw-secrets"
    return hashlib.sha256(combined.encode()).digest()


def _encrypt_value(value: str) -> str:
    """简单加密（XOR + Base64）

    注意：这不是军用级加密，但足以防止明文泄露
    对于高安全需求，仍应使用 keyring
    """
    key = _get_machine_key()
    value_bytes = value.encode("utf-8")
    # XOR 加密
    encrypted = bytes(b ^ key[i % len(key)] for i, b in enumerate(value_bytes))
    # Base64 编码
    return base64.b64encode(encrypted).decode("ascii")


def _decrypt_value(encrypted_value: str) -> str:
    """解密"""
    key = _get_machine_key()
    encrypted = base64.b64decode(encrypted_value.encode("ascii"))
    # XOR 解密
    decrypted = bytes(b ^ key[i % len(key)] for i, b in enumerate(encrypted))
    return decrypted.decode("utf-8")


def _load_secrets_file() -> dict:
    """从加密文件加载密钥"""
    if not SECRETS_FILE.exists():
        return {}
    try:
        with SECRETS_FILE.open("r") as f:
            encrypted_data = json.load(f)
        # 解密所有值
        return {k: _decrypt_value(v) for k, v in encrypted_data.items()}
    except Exception:
        return {}


def _save_secrets_file(secrets: dict):
    """保存密钥到加密文件"""
    # 加密所有值
    encrypted_data = {k: _encrypt_value(v) for k, v in secrets.items()}
    with SECRETS_FILE.open("w") as f:
        json.dump(encrypted_data, f)
    # 设置文件权限为仅用户可读写
    SECRETS_FILE.chmod(0o600)


class Config:
    """配置管理器（支持安全存储）"""

    def __init__(self):
        ensure_config_dir()
        self.config = self._load_config()
        self._secrets_cache: dict | None = None

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
    # 安全存储（优先 keyring，回退加密文件，最后环境变量）
    # ============================================

    def _get_secret(self, key: str) -> str | None:
        """获取密钥（keyring > 加密文件 > 环境变量）"""
        # 1. 尝试 keyring
        if KEYRING_AVAILABLE:
            try:
                value = keyring.get_password(KEYRING_SERVICE, key)
                if value:
                    return value
            except Exception:
                pass

        # 2. 尝试加密文件
        if self._secrets_cache is None:
            self._secrets_cache = _load_secrets_file()
        if key in self._secrets_cache:
            return self._secrets_cache[key]

        # 3. 回退环境变量
        return os.environ.get(key.upper())

    def _set_secret(self, key: str, value: str) -> bool:
        """存储密钥（keyring 优先，失败则回退加密文件）

        Returns:
            True 如果成功存储（keyring 或文件）
        """
        stored = False
        storage_type = "none"

        # 1. 尝试 keyring
        if KEYRING_AVAILABLE:
            try:
                keyring.set_password(KEYRING_SERVICE, key, value)
                storage_type = "keyring"
                stored = True
            except Exception:
                pass

        # 2. 回退加密文件
        if not stored:
            try:
                if self._secrets_cache is None:
                    self._secrets_cache = _load_secrets_file()
                self._secrets_cache[key] = value
                _save_secrets_file(self._secrets_cache)
                storage_type = "encrypted-file"
                stored = True
            except Exception as e:
                print(f"⚠️ Warning: Failed to store {key}: {e}")

        if stored and storage_type != "keyring":
            print(f"ℹ️ Info: {key} stored in {storage_type} (keyring unavailable)")

        return stored

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
    # 便捷方法
    # ============================================

    def get_storage_status(self) -> dict:
        """获取安全存储状态（用于调试）"""
        return {
            "keyring_available": KEYRING_AVAILABLE,
            "secrets_file_exists": SECRETS_FILE.exists(),
            "config_dir": str(CONFIG_DIR),
        }


# 全局配置实例
_config: Config | None = None


def get_config() -> Config:
    """获取全局配置实例"""
    global _config
    if _config is None:
        _config = Config()
    return _config
