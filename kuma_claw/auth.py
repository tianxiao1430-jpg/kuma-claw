"""
Kuma Claw - OAuth 认证管理
========================
"""

import json
import logging
import os
import secrets
import threading
import webbrowser
from datetime import datetime, timedelta
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlparse

import httpx

logger = logging.getLogger("kuma_claw.auth")

# ============================================
# 配置
# ============================================

OAUTH_TOKENS_FILE = Path.home() / ".kuma-claw" / "oauth_tokens.json"

# KumaClaw 官方 OAuth Client ID
# 用户无需自己创建，直接使用官方 Client ID 即可
ADKCLAW_OFFICIAL_CLIENT_ID = os.environ.get(
    "ADKCLAW_CLIENT_ID",
    "",  # 占位符，需要填写真实 Client ID
)

# Google OAuth 配置
GOOGLE_OAUTH_SCOPES = [
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.compose",
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/calendar.events",
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/documents",
    "https://www.googleapis.com/auth/drive.readonly",
]

GOOGLE_OAUTH_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_OAUTH_TOKEN_URL = "https://oauth2.googleapis.com/token"


# ============================================
# Token 管理器
# ============================================


class OAuthTokenManager:
    """OAuth Token 管理器"""

    def __init__(self):
        self.tokens_file = OAUTH_TOKENS_FILE
        self.tokens = self._load_tokens()

    def _load_tokens(self) -> dict:
        """加载 Token"""
        if self.tokens_file.exists():
            with self.tokens_file.open("r") as f:
                return json.load(f)
        return {}

    def _save_tokens(self):
        """保存 Token"""
        self.tokens_file.parent.mkdir(parents=True, exist_ok=True)
        with self.tokens_file.open("w") as f:
            json.dump(self.tokens, f, indent=2)

    def save_google_tokens(self, access_token: str, refresh_token: str, expires_in: int):
        """保存 Google Token"""
        self.tokens["google"] = {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "expires_at": (datetime.now() + timedelta(seconds=expires_in)).isoformat(),
            "updated_at": datetime.now().isoformat(),
        }
        self._save_tokens()

    def get_google_tokens(self) -> dict | None:
        """获取 Google Token"""
        return self.tokens.get("google")

    def token_expired(self) -> bool:
        """检查 Token 是否过期"""
        tokens = self.get_google_tokens()
        if not tokens:
            return True

        expires_at = datetime.fromisoformat(tokens["expires_at"])
        # 提前 5 分钟认为过期
        return datetime.now() >= (expires_at - timedelta(minutes=5))

    def refresh_google_token(self, client_id: str, client_secret: str = "") -> str | None:
        """刷新 Google Token"""
        tokens = self.get_google_tokens()
        if not tokens:
            return None

        try:
            data = {
                "client_id": client_id,
                "refresh_token": tokens["refresh_token"],
                "grant_type": "refresh_token",
            }
            # Desktop app 通常不需要 client_secret
            if client_secret:
                data["client_secret"] = client_secret

            response = httpx.post(GOOGLE_OAUTH_TOKEN_URL, data=data, timeout=30.0)
            response.raise_for_status()
            token_data = response.json()

            # 更新 Token
            self.save_google_tokens(
                access_token=token_data["access_token"],
                refresh_token=tokens["refresh_token"],  # refresh_token 不变
                expires_in=token_data["expires_in"],
            )

            return token_data["access_token"]
        except Exception as e:
            logger.error(f"刷新 Token 失败: {e}")
            return None

    def get_valid_access_token(self, client_id: str, client_secret: str = "") -> str | None:
        """获取有效的 access_token（自动刷新）"""
        tokens = self.get_google_tokens()
        if not tokens:
            return None

        if self.token_expired():
            return self.refresh_google_token(client_id, client_secret)

        return tokens["access_token"]

    def clear_google_tokens(self):
        """清除 Google Token"""
        if "google" in self.tokens:
            del self.tokens["google"]
            self._save_tokens()


# ============================================
# OAuth 授权流程
# ============================================


class OAuthFlow:
    """OAuth 授权流程"""

    def __init__(self, client_id: str, client_secret: str = ""):
        self.client_id = client_id
        self.client_secret = client_secret
        self.state = secrets.token_urlsafe(16)
        # 使用环境变量配置端口，默认 8080（Issue #107）
        self.redirect_port = int(os.getenv("KUMA_WEB_PORT", "8080"))
        self.redirect_uri = f"http://localhost:{self.redirect_port}/oauth/callback"

    def get_authorization_url(self) -> str:
        """生成授权 URL"""
        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "response_type": "code",
            "scope": " ".join(GOOGLE_OAUTH_SCOPES),
            "access_type": "offline",
            "state": self.state,
            "prompt": "consent",
        }
        return f"{GOOGLE_OAUTH_AUTH_URL}?{urlencode(params)}"

    def exchange_code_for_tokens(self, code: str) -> dict:
        """用授权码换取 Token"""
        data = {
            "client_id": self.client_id,
            "code": code,
            "redirect_uri": self.redirect_uri,
            "grant_type": "authorization_code",
        }
        # Desktop app 通常不需要 client_secret
        if self.client_secret:
            data["client_secret"] = self.client_secret

        response = httpx.post(GOOGLE_OAUTH_TOKEN_URL, data=data, timeout=30.0)
        response.raise_for_status()
        return response.json()

    def start_authorization(self) -> bool:
        """启动授权流程

        Returns:
            是否成功启动
        """
        auth_url = self.get_authorization_url()

        # 创建回调接收器
        callback_received = {"code": None, "error": None}
        server_ready = threading.Event()

        class OAuthCallbackHandler(BaseHTTPRequestHandler):
            def do_GET(self):
                parsed = urlparse(self.path)
                if parsed.path == "/oauth/callback":
                    params = dict(parse_qsl(parsed.query))
                    if "code" in params:
                        callback_received["code"] = params["code"]
                        self.send_response(200)
                        self.send_header("Content-type", "text/html")
                        self.end_headers()
                        self.wfile.write(
                            "<html><body><h1>✅ 授权成功！</h1>"
                            "<p>您可以关闭此页面，返回 CLI 继续操作。</p></body></html>".encode()
                        )
                    elif "error" in params:
                        callback_received["error"] = params["error"]
                        self.send_response(200)
                        self.send_header("Content-type", "text/html")
                        self.end_headers()
                        error_msg = params["error"].encode()
                        self.wfile.write(
                            "<html><body><h1>❌ 授权失败</h1><p>Error: %s</p></body></html>".encode()
                            % error_msg
                        )
                    else:
                        self.send_response(400)
                        self.end_headers()
                else:
                    self.send_response(404)
                    self.end_headers()

            def log_message(self, format, *args):
                pass  # 静默日志

        # 启动临时服务器
        server = HTTPServer(("localhost", self.redirect_port), OAuthCallbackHandler)
        server.timeout = 300  # 5 分钟超时

        def run_server():
            server_ready.set()
            server.handle_request()  # 只处理一次请求

        server_thread = threading.Thread(target=run_server, daemon=True)
        server_thread.start()

        # 等待服务器启动
        server_ready.wait(timeout=5)

        logger.info(f"授权地址：{auth_url}")
        logger.info("正在打开浏览器进行授权，如果浏览器没有自动打开，请手动访问上方地址")

        # 打开浏览器
        webbrowser.open(auth_url)

        # 等待回调
        logger.info("等待授权完成（最多 5 分钟）...")
        server_thread.join(timeout=300)

        if callback_received["error"]:
            logger.error(f"授权失败：{callback_received['error']}")
            return False
        elif callback_received["code"]:
            logger.info("授权成功，正在换取 Token...")
            # 用 code 换取 tokens
            tokens = self.exchange_code_for_tokens(callback_received["code"])
            # 保存 tokens
            from .auth import token_manager

            token_manager.save_google_tokens(
                access_token=tokens["access_token"],
                refresh_token=tokens.get("refresh_token", ""),
                expires_in=tokens["expires_in"],
            )
            logger.info("Token 已保存")
            return True
        else:
            logger.warning("授权超时，请重试")
            return False


# ============================================
# 便捷函数
# ============================================


def get_oauth_client_id(config_client_id: str | None = None) -> str:
    """获取 OAuth Client ID

    优先级：
    1. 用户配置的 Client ID
    2. KumaClaw 官方 Client ID
    3. 环境变量 ADKCLAW_CLIENT_ID

    Args:
        config_client_id: 用户配置的 Client ID

    Returns:
        Client ID

    Raises:
        ValueError: 没有可用的 Client ID
    """
    if config_client_id:
        return config_client_id

    if ADKCLAW_OFFICIAL_CLIENT_ID:
        return ADKCLAW_OFFICIAL_CLIENT_ID

    raise ValueError(
        "未配置 OAuth Client ID。\n"
        "请运行: kuma-claw config --section oauth\n"
        "或设置环境变量: ADKCLAW_CLIENT_ID"
    )


def is_official_client_id(client_id: str) -> bool:
    """检查是否使用官方 Client ID"""
    return client_id == ADKCLAW_OFFICIAL_CLIENT_ID


# ============================================
# 全局实例
# ============================================

token_manager = OAuthTokenManager()
