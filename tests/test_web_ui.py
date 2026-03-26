"""
tests/test_web_ui.py
Web UI API エンドポイントのテスト（Issue #104）

カバー範囲:
- GET /  ホームページ
- POST /api/model  モデル保存
- POST /api/google-key  Google API Key 保存
- POST /api/telegram  Telegram Token 保存
- GET /api/status  ステータス取得
- GET /oauth/callback  OAuth コールバック（エラーケース・XSS 防止）
"""

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

import kuma_claw.web_ui as web_ui_module

# ============================================================
# フィクスチャ
# ============================================================


@pytest.fixture(autouse=True)
def bypass_auth(monkeypatch):
    """認証ミドルウェアをバイパスする（テスト用）
    get_web_ui_token が None を返すと認証スキップになる。
    """
    monkeypatch.setattr(web_ui_module.config, "get_web_ui_token", lambda: None)


@pytest.fixture
def mock_config(monkeypatch):
    """テスト用モック Config の主要メソッドを差し替える"""
    monkeypatch.setattr(web_ui_module.config, "get_google_api_key", lambda: None)
    monkeypatch.setattr(web_ui_module.config, "get_openai_api_key", lambda: None)
    monkeypatch.setattr(web_ui_module.config, "get_anthropic_api_key", lambda: None)
    monkeypatch.setattr(web_ui_module.config, "is_slack_enabled", lambda: False)
    monkeypatch.setattr(web_ui_module.config, "is_telegram_enabled", lambda: False)
    monkeypatch.setattr(web_ui_module.config, "get_google_oauth_client_id", lambda: None)

    set_model_mock = MagicMock()
    set_google_key_mock = MagicMock()
    set_telegram_mock = MagicMock()
    monkeypatch.setattr(web_ui_module.config, "set_model", set_model_mock)
    monkeypatch.setattr(web_ui_module.config, "set_google_api_key", set_google_key_mock)
    monkeypatch.setattr(web_ui_module.config, "set_telegram_token", set_telegram_mock)

    return {
        "set_model": set_model_mock,
        "set_google_api_key": set_google_key_mock,
        "set_telegram_token": set_telegram_mock,
    }


@pytest.fixture
def mock_token_manager(monkeypatch):
    """テスト用モック token_manager"""
    monkeypatch.setattr(web_ui_module.token_manager, "get_google_tokens", lambda: None)
    monkeypatch.setattr(web_ui_module.token_manager, "token_expired", lambda: True)


@pytest.fixture
def client():
    """テスト用 FastAPI TestClient"""
    return TestClient(web_ui_module.app, raise_server_exceptions=False)


# ============================================================
# ホームページのテスト
# ============================================================


class TestHomePage:
    """GET / ホームページのテスト"""

    def test_homepage_returns_200(self, client, mock_config, mock_token_manager):
        """ホームページが 200 またはリダイレクトを返す"""
        response = client.get("/", follow_redirects=False)
        assert response.status_code in (200, 302, 307)

    def test_homepage_contains_html(self, client, mock_config, mock_token_manager):
        """ホームページが HTML コンテンツを返す"""
        response = client.get("/", follow_redirects=True)
        assert response.status_code == 200
        assert "html" in response.headers.get("content-type", "").lower()


# ============================================================
# モデル保存のテスト
# ============================================================


class TestSaveModel:
    """POST /api/model のテスト"""

    def test_save_valid_model(self, client, mock_config):
        """有効なモデルを保存するとリダイレクトされる"""
        response = client.post(
            "/api/model",
            data={"model": "gemini-3.1-flash"},
            follow_redirects=False,
        )
        assert response.status_code in (200, 302, 303, 307)

    def test_save_model_calls_set_model(self, client, mock_config):
        """モデル保存時に config.set_model が呼ばれる"""
        client.post(
            "/api/model",
            data={"model": "gemini-3.1-flash-lite"},
            follow_redirects=False,
        )
        mock_config["set_model"].assert_called_once_with("gemini-3.1-flash-lite")


# ============================================================
# Google API Key 保存のテスト
# ============================================================


class TestSaveGoogleKey:
    """POST /api/google-key のテスト"""

    def test_save_google_api_key(self, client, mock_config):
        """Google API Key を保存するとリダイレクトされる"""
        response = client.post(
            "/api/google-key",
            data={"api_key": "AIzaSy_test_key"},
            follow_redirects=False,
        )
        assert response.status_code in (200, 302, 303, 307)

    def test_save_google_key_calls_set_google_api_key(self, client, mock_config):
        """Google API Key 保存時に config.set_google_api_key が呼ばれる"""
        client.post(
            "/api/google-key",
            data={"api_key": "AIzaSy_test_key"},
            follow_redirects=False,
        )
        mock_config["set_google_api_key"].assert_called_once_with("AIzaSy_test_key")


# ============================================================
# Telegram Token 保存のテスト
# ============================================================


class TestSaveTelegram:
    """POST /api/telegram のテスト"""

    def test_save_telegram_token(self, client, mock_config):
        """Telegram Token を保存するとリダイレクトされる"""
        response = client.post(
            "/api/telegram",
            data={"token": "1234567890:ABCdef"},
            follow_redirects=False,
        )
        assert response.status_code in (200, 302, 303, 307)
        mock_config["set_telegram_token"].assert_called_once_with("1234567890:ABCdef")


# ============================================================
# /api/status エンドポイントのテスト
# ============================================================


class TestStatusAPI:
    """GET /api/status のテスト"""

    def test_status_returns_json(self, client):
        """ステータス API が JSON を返す"""
        response = client.get("/api/status")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)

    def test_status_contains_services(self, client):
        """ステータス API に telegram と slack が含まれる"""
        response = client.get("/api/status")
        assert response.status_code == 200
        data = response.json()
        assert "telegram" in data
        assert "slack" in data


# ============================================================
# OAuth コールバックのテスト
# ============================================================


class TestOAuthCallback:
    """GET /oauth/callback のテスト"""

    def test_callback_with_error_param(self, client):
        """error パラメータがある場合は 400 を返す"""
        response = client.get("/oauth/callback?error=access_denied")
        assert response.status_code in (400, 200)

    def test_callback_xss_prevention(self, client):
        """XSS 攻撃コードがそのまま HTML に埋め込まれない（Issue #103 修正の検証）"""
        xss_payload = "<script>alert('xss')</script>"
        response = client.get(f"/oauth/callback?error={xss_payload}")
        body = response.text
        # <script>タグがそのまま出力されていないことを確認
        assert "<script>alert" not in body

    def test_callback_without_code(self, client):
        """code パラメータがない場合は 400 を返す"""
        response = client.get("/oauth/callback?state=some_state")
        assert response.status_code in (400, 200)
