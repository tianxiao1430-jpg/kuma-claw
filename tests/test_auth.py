"""
tests/test_auth.py
OAuthTokenManager / OAuthFlow のユニットテスト（Issue #104）

カバー範囲:
- OAuthTokenManager: Token の保存・取得・有効期限・リフレッシュ
- OAuthFlow: 認証 URL の生成
"""

import json
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from kuma_claw.auth import OAuthTokenManager, OAuthFlow


# ============================================================
# フィクスチャ
# ============================================================


@pytest.fixture
def temp_tokens_file(tmp_path, monkeypatch):
    """テスト用の一時 Token ファイルパス"""
    tokens_file = tmp_path / "oauth_tokens.json"
    monkeypatch.setattr("kuma_claw.auth.OAUTH_TOKENS_FILE", tokens_file)
    return tokens_file


@pytest.fixture
def token_manager(temp_tokens_file):
    """テスト用 OAuthTokenManager インスタンス"""
    return OAuthTokenManager()


# ============================================================
# Token 保存・取得のテスト
# ============================================================


class TestGoogleTokenStorage:
    """OAuthTokenManager の Token 保存・取得テスト"""

    def test_save_and_get_tokens(self, token_manager):
        """Token を保存して取得できる"""
        token_manager.save_google_tokens(
            access_token="test_access_token",
            refresh_token="test_refresh_token",
            expires_in=3600,
        )
        tokens = token_manager.get_google_tokens()
        assert tokens is not None
        assert tokens["access_token"] == "test_access_token"
        assert tokens["refresh_token"] == "test_refresh_token"

    def test_get_tokens_when_not_saved(self, token_manager):
        """Token が保存されていない場合は None を返す"""
        tokens = token_manager.get_google_tokens()
        assert tokens is None

    def test_token_expiry_is_set(self, token_manager):
        """Token 保存時に expires_at が設定される"""
        token_manager.save_google_tokens(
            access_token="token",
            refresh_token="refresh",
            expires_in=3600,
        )
        tokens = token_manager.get_google_tokens()
        assert tokens is not None
        assert "expires_at" in tokens

    def test_overwrite_tokens(self, token_manager):
        """Token を上書き保存できる"""
        token_manager.save_google_tokens("old_token", "old_refresh", 3600)
        token_manager.save_google_tokens("new_token", "new_refresh", 7200)
        tokens = token_manager.get_google_tokens()
        assert tokens["access_token"] == "new_token"

    def test_clear_google_tokens(self, token_manager):
        """Token を削除できる"""
        token_manager.save_google_tokens("token", "refresh", 3600)
        token_manager.clear_google_tokens()
        assert token_manager.get_google_tokens() is None


# ============================================================
# Token 有効期限チェックのテスト
# ============================================================


class TestTokenExpiry:
    """token_expired() のテスト"""

    def test_valid_token_not_expired(self, token_manager):
        """有効期限内の Token は期限切れではない"""
        token_manager.save_google_tokens("token", "refresh", expires_in=3600)
        assert token_manager.token_expired() is False

    def test_expired_token(self, token_manager):
        """有効期限切れの Token は期限切れと判定される"""
        token_manager.save_google_tokens("token", "refresh", expires_in=-600)
        assert token_manager.token_expired() is True

    def test_no_token_is_expired(self, token_manager):
        """Token がない場合は期限切れと判定される"""
        assert token_manager.token_expired() is True

    def test_near_expiry_considered_expired(self, token_manager):
        """有効期限まで 5 分未満の Token は期限切れと判定される（バッファ）"""
        # 3 分後に期限切れ
        token_manager.save_google_tokens("token", "refresh", expires_in=180)
        assert token_manager.token_expired() is True


# ============================================================
# Token リフレッシュのテスト（モック）
# ============================================================


class TestTokenRefresh:
    """refresh_google_token() のテスト"""

    def test_refresh_success(self, token_manager):
        """リフレッシュ成功時に新しい access_token を返す"""
        token_manager.save_google_tokens("old_token", "valid_refresh", expires_in=-600)

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "access_token": "new_access_token",
            "expires_in": 3600,
        }
        mock_response.raise_for_status = MagicMock()

        with patch("kuma_claw.auth.httpx.post", return_value=mock_response):
            result = token_manager.refresh_google_token(
                client_id="test_client_id",
                client_secret="test_client_secret",
            )

        assert result == "new_access_token"

    def test_refresh_no_tokens(self, token_manager):
        """Token がない場合はリフレッシュできず None を返す"""
        result = token_manager.refresh_google_token(
            client_id="test_client_id",
        )
        assert result is None

    def test_refresh_http_error(self, token_manager):
        """HTTP エラー時は None を返す"""
        import httpx

        token_manager.save_google_tokens("old_token", "invalid_refresh", expires_in=-600)

        with patch("kuma_claw.auth.httpx.post", side_effect=httpx.HTTPError("network error")):
            result = token_manager.refresh_google_token(
                client_id="test_client_id",
            )

        assert result is None

    def test_get_valid_access_token_not_expired(self, token_manager):
        """有効な Token は get_valid_access_token でそのまま返る"""
        token_manager.save_google_tokens("valid_token", "refresh", expires_in=3600)
        result = token_manager.get_valid_access_token(client_id="client_id")
        assert result == "valid_token"

    def test_get_valid_access_token_no_tokens(self, token_manager):
        """Token がない場合は None を返す"""
        result = token_manager.get_valid_access_token(client_id="client_id")
        assert result is None


# ============================================================
# OAuth 認証 URL 生成のテスト
# ============================================================


class TestOAuthURL:
    """OAuthFlow.get_authorization_url() のテスト"""

    @pytest.fixture
    def oauth_flow(self):
        return OAuthFlow(client_id="my_client_id", client_secret="my_secret")

    def test_get_auth_url_contains_client_id(self, oauth_flow):
        """認証 URL にクライアント ID が含まれる"""
        url = oauth_flow.get_authorization_url()
        assert "my_client_id" in url

    def test_get_auth_url_is_google_accounts(self, oauth_flow):
        """認証 URL は Google アカウントのドメイン"""
        url = oauth_flow.get_authorization_url()
        assert "google" in url.lower() or "accounts" in url.lower()

    def test_get_auth_url_contains_redirect_uri(self, oauth_flow):
        """認証 URL にリダイレクト URI が含まれる"""
        url = oauth_flow.get_authorization_url()
        assert "redirect_uri" in url or "localhost" in url

    def test_get_auth_url_contains_state(self, oauth_flow):
        """認証 URL に CSRF 対策の state パラメータが含まれる"""
        url = oauth_flow.get_authorization_url()
        assert "state=" in url

    def test_get_auth_url_offline_access(self, oauth_flow):
        """認証 URL に offline access（refresh_token 取得）が含まれる"""
        url = oauth_flow.get_authorization_url()
        assert "offline" in url or "access_type" in url
