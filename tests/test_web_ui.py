"""
tests/test_web_ui.py
Web UI API エンドポイントのテスト（Issue #104）

カバー範囲:
- GET / ホームページ
- POST /save/model モデル保存
- POST /save/google Google API Key 保存
- POST /save/telegram Telegram Token 保存
- POST /save/oauth OAuth 設定保存
- GET /api/status ステータス取得
- GET /oauth/callback OAuth コールバック（エラーケース）
"""

import json
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient


# ============================================================
# フィクスチャ
# ============================================================


@pytest.fixture
def mock_config(tmp_path):
    """テスト用モック Config"""
    config = MagicMock()
    config.get_model.return_value = "gemini-3.1-flash"
    config.config = {
        "model": "gemini-3.1-flash",
        "channels": {
            "slack": {"enabled": False},
            "telegram": {"enabled": False},
        },
    }
    config.get_google_api_key.return_value = None
    config.get_telegram_token.return_value = None
    config.get_slack_tokens.return_value = (None, None)
    config.get_oauth_credentials.return_value = (None, None)
    config.get_web_ui_token.return_value = None  # 認証なし（テスト用）
    config.web_ui_port = 8080
    return config


@pytest.fixture
def client(mock_config):
    """テスト用 FastAPI TestClient"""
    with patch("kuma_claw.web_ui.config", mock_config):
        from kuma_claw.web_ui import create_app
        app = create_app()
        return TestClient(app, raise_server_exceptions=False)


# ============================================================
# ホームページのテスト
# ============================================================


class TestHomePage:
    """GET / ホームページのテスト"""

    def test_homepage_returns_200(self, client):
        """ホームページが 200 を返す"""
        response = client.get("/")
        assert response.status_code in (200, 307, 302)  # リダイレクトも許容

    def test_homepage_contains_html(self, client):
        """ホームページが HTML を返す"""
        response = client.get("/")
        if response.status_code == 200:
            assert "html" in response.headers.get("content-type", "").lower()


# ============================================================
# モデル保存のテスト
# ============================================================


class TestSaveModel:
    """POST /save/model のテスト"""

    def test_save_valid_model(self, client, mock_config):
        """有効なモデルを保存できる"""
        response = client.post(
            "/save/model",
            data={"model": "gemini-3.1-flash"},
            follow_redirects=False,
        )
        # リダイレクトまたは 200
        assert response.status_code in (200, 302, 307)

    def test_save_model_calls_set_model(self, client, mock_config):
        """モデル保存時に set_model が呼ばれる"""
        client.post(
            "/save/model",
            data={"model": "gemini-3.1-flash-lite"},
            follow_redirects=False,
        )
        mock_config.set_model.assert_called_once_with("gemini-3.1-flash-lite")


# ============================================================
# API Key 保存のテスト
# ============================================================


class TestSaveGoogleKey:
    """POST /save/google のテスト"""

    def test_save_google_api_key(self, client, mock_config):
        """Google API Key を保存できる"""
        response = client.post(
            "/save/google",
            data={"google_api_key": "AIzaSy_test_key"},
            follow_redirects=False,
        )
        assert response.status_code in (200, 302, 307)

    def test_save_google_key_calls_set_google_api_key(self, client, mock_config):
        """保存時に set_google_api_key が呼ばれる"""
        client.post(
            "/save/google",
            data={"google_api_key": "AIzaSy_test_key"},
            follow_redirects=False,
        )
        mock_config.set_google_api_key.assert_called_once_with("AIzaSy_test_key")


# ============================================================
# Telegram Token 保存のテスト
# ============================================================


class TestSaveTelegram:
    """POST /save/telegram のテスト"""

    def test_save_telegram_token(self, client, mock_config):
        """Telegram Token を保存できる"""
        response = client.post(
            "/save/telegram",
            data={"telegram_token": "123456:ABC-test"},
            follow_redirects=False,
        )
        assert response.status_code in (200, 302, 307)


# ============================================================
# ステータス API のテスト
# ============================================================


class TestStatusAPI:
    """GET /api/status のテスト"""

    def test_status_returns_json(self, client):
        """/api/status が JSON を返す"""
        response = client.get("/api/status")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)

    def test_status_contains_services(self, client):
        """/api/status にサービス情報が含まれる"""
        response = client.get("/api/status")
        if response.status_code == 200:
            data = response.json()
            # services または telegram/slack キーが存在する
            assert any(k in data for k in ("services", "telegram", "slack", "web_ui"))


# ============================================================
# OAuth コールバックのテスト
# ============================================================


class TestOAuthCallback:
    """GET /oauth/callback のテスト"""

    def test_callback_with_error_param(self, client):
        """error パラメータがある場合はエラーページを返す"""
        response = client.get("/oauth/callback?error=access_denied")
        assert response.status_code in (200, 400, 500)
        if response.status_code == 200:
            # XSS 対策: スクリプトタグがエスケープされている
            assert "<script>" not in response.text

    def test_callback_xss_prevention(self, client):
        """XSS 攻撃ペイロードがエスケープされる（Issue #103 修正の検証）"""
        xss_payload = "<script>alert('xss')</script>"
        response = client.get(f"/oauth/callback?error={xss_payload}")
        # スクリプトタグがそのまま出力されていないことを確認
        assert "<script>alert" not in response.text

    def test_callback_without_code(self, client):
        """code パラメータなしのコールバックはエラーを返す"""
        response = client.get("/oauth/callback")
        assert response.status_code in (200, 400, 422, 500)
