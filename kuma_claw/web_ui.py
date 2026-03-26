"""
Web UI 启动
===========
"""

import json
import logging
import secrets
from html import escape
from pathlib import Path

import httpx
import uvicorn
from fastapi import FastAPI, Form, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from .auth import OAuthFlow, token_manager
from .config import config

logger = logging.getLogger("kuma_claw.web_ui")

app = FastAPI(title="Kuma Claw")

TEMPLATES_DIR = Path(__file__).parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

# ============================================
# 认证中间件（Issue #103-2）
# ============================================

# 公开路径（无需认证）
_PUBLIC_PATHS = {"/oauth/callback", "/api/status", "/api/oauth/status"}


class WebUIAuthMiddleware(BaseHTTPMiddleware):
    """简单的 Bearer Token 认证中间件

    防止未授权用户读写 API Key 和配置。
    Token 在首次启动时自动生成并写入配置目录。
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        # 公开路径和 OAuth 回调不需要认证
        if request.url.path in _PUBLIC_PATHS or request.url.path.startswith("/oauth/"):
            return await call_next(request)

        # 获取当前有效 token
        expected = config.get_web_ui_token()
        if not expected:
            # 未配置 token 时允许访问（首次启动配置阶段）
            return await call_next(request)

        # 检查 Cookie（浏览器访问）
        cookie_token = request.cookies.get("kuma_ui_token")
        if cookie_token and secrets.compare_digest(cookie_token, expected):
            return await call_next(request)

        # 检查 Authorization header（API 访问）
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            bearer = auth_header[7:]
            if secrets.compare_digest(bearer, expected):
                return await call_next(request)

        # 未认证：返回登录页
        if request.url.path == "/" or not request.url.path.startswith("/api/"):
            return RedirectResponse(url="/login")
        return JSONResponse({"detail": "Unauthorized"}, status_code=401)


app.add_middleware(WebUIAuthMiddleware)


@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """登录页面"""
    return HTMLResponse(
        content="""
        <!DOCTYPE html>
        <html lang="zh-CN">
        <head>
            <meta charset="UTF-8">
            <title>Kuma Claw - 登录</title>
            <style>
                body { font-family: sans-serif; display: flex; justify-content: center;
                       align-items: center; min-height: 100vh; margin: 0;
                       background: linear-gradient(135deg, #667eea, #764ba2); }
                .card { background: white; padding: 40px; border-radius: 12px;
                        box-shadow: 0 4px 20px rgba(0,0,0,0.15); width: 320px; }
                h1 { text-align: center; color: #333; margin-bottom: 24px; }
                input { width: 100%; padding: 12px; border: 2px solid #e0e0e0;
                        border-radius: 8px; font-size: 14px; box-sizing: border-box;
                        margin-bottom: 16px; }
                button { width: 100%; padding: 12px; background: linear-gradient(135deg, #667eea, #764ba2);
                         color: white; border: none; border-radius: 8px;
                         font-size: 14px; font-weight: 600; cursor: pointer; }
                .hint { text-align: center; color: #888; font-size: 12px; margin-top: 12px; }
            </style>
        </head>
        <body>
            <div class="card">
                <h1>🦞 Kuma Claw</h1>
                <form method="post" action="/login">
                    <input type="password" name="token" placeholder="请输入访问密码" required>
                    <button type="submit">登录</button>
                </form>
                <p class="hint">密码保存在 ~/.kuma-claw/ui_token.txt</p>
            </div>
        </body>
        </html>
        """
    )


@app.post("/login")
async def login(request: Request, token: str = Form(...)):
    """处理登录"""
    expected = config.get_web_ui_token()
    if not expected or not secrets.compare_digest(token, expected):
        return HTMLResponse(
            content="<script>alert('密码错误'); history.back();</script>",
            status_code=401,
        )
    response = RedirectResponse(url="/", status_code=303)
    response.set_cookie(
        "kuma_ui_token", token, httponly=True, samesite="lax", max_age=86400 * 7
    )
    return response


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """主页"""
    # OAuth 状态
    client_id = config.get_google_oauth_client_id()
    tokens = token_manager.get_google_tokens()
    oauth_configured = bool(client_id)
    oauth_authorized = bool(tokens)

    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "config": config.config,
            "has_google_key": bool(config.get_google_api_key()),
            "has_openai_key": bool(config.get_openai_api_key()),
            "has_anthropic_key": bool(config.get_anthropic_api_key()),
            "slack_enabled": config.is_slack_enabled(),
            "telegram_enabled": config.is_telegram_enabled(),
            "oauth_configured": oauth_configured,
            "oauth_authorized": oauth_authorized,
        },
    )


# ============================================
# API Keys
# ============================================


@app.post("/api/model")
async def set_model(model: str = Form(...)):
    """设置模型"""
    config.set_model(model)
    return RedirectResponse(url="/?saved=model", status_code=303)


@app.post("/api/google-key")
async def set_google_key(api_key: str = Form(...)):
    """设置 Google API Key"""
    config.set_google_api_key(api_key)
    return RedirectResponse(url="/?saved=google", status_code=303)


@app.post("/api/openai-key")
async def set_openai_key(api_key: str = Form(...)):
    """设置 OpenAI API Key"""
    config.set_openai_api_key(api_key)
    return RedirectResponse(url="/?saved=openai", status_code=303)


@app.post("/api/anthropic-key")
async def set_anthropic_key(api_key: str = Form(...)):
    """设置 Anthropic API Key"""
    config.set_anthropic_api_key(api_key)
    return RedirectResponse(url="/?saved=anthropic", status_code=303)


# ============================================
# Channels
# ============================================


@app.post("/api/slack")
async def set_slack(bot_token: str = Form(...), app_token: str = Form(...)):
    """设置 Slack"""
    config.set_slack_tokens(bot_token, app_token)
    return RedirectResponse(url="/?saved=slack", status_code=303)


@app.post("/api/telegram")
async def set_telegram(token: str = Form(...)):
    """设置 Telegram"""
    config.set_telegram_token(token)
    return RedirectResponse(url="/?saved=telegram", status_code=303)


# ============================================
# OAuth
# ============================================


@app.post("/api/google-oauth")
async def set_google_oauth(client_id: str = Form(...), client_secret: str = Form(...)):
    """设置 Google OAuth"""
    config.set_google_oauth(client_id, client_secret)
    return RedirectResponse(url="/?saved=oauth", status_code=303)


@app.get("/oauth/authorize")
async def oauth_authorize():
    """重定向到 Google 授权页面"""
    client_id = config.get_google_oauth_client_id()
    client_secret = config.get_google_oauth_client_secret()

    if not client_id or not client_secret:
        return HTMLResponse(
            content="<h1>❌ OAuth 未配置</h1><p>请先配置 Google OAuth 凭证</p>", status_code=400
        )

    # 创建 OAuth 流程
    flow = OAuthFlow(client_id, client_secret)

    # 保存 state 用于验证
    state_file = Path.home() / ".kuma-claw" / "oauth_state.json"
    state_file.parent.mkdir(parents=True, exist_ok=True)
    with open(state_file, "w") as f:
        json.dump(
            {
                "state": flow.state,
                "client_id": client_id,
                "client_secret": client_secret,
            },
            f,
        )

    # 重定向到 Google
    auth_url = flow.get_authorization_url()
    return RedirectResponse(url=auth_url)


@app.get("/oauth/callback")
async def oauth_callback(
    code: str | None = Query(None), state: str | None = Query(None), error: str | None = Query(None)
):
    """处理 Google OAuth 回调"""
    # 错误处理
    if error:
        logger.error(f"OAuth error: {error}")
        return HTMLResponse(
            content=f"""
            <html>
            <head><title>授权失败</title></head>
            <body style="font-family: sans-serif; text-align: center; padding: 50px;">
                <h1 style="color: #e74c3c;">❌ 授权失败</h1>
                <p style="color: #7f8c8d;">错误: {escape(error)}</p>
                <p><a href="/" style="color: #3498db;">返回首页</a></p>
            </body>
            </html>
            """,
            status_code=400,
        )

    # 缺少参数
    if not code or not state:
        return HTMLResponse(
            content="""
            <html>
            <head><title>授权失败</title></head>
            <body style="font-family: sans-serif; text-align: center; padding: 50px;">
                <h1 style="color: #e74c3c;">❌ 授权失败</h1>
                <p style="color: #7f8c8d;">缺少必要参数</p>
                <p><a href="/" style="color: #3498db;">返回首页</a></p>
            </body>
            </html>
            """,
            status_code=400,
        )

    # 验证 state
    state_file = Path.home() / ".kuma-claw" / "oauth_state.json"
    if not state_file.exists():
        return HTMLResponse(
            content="""
            <html>
            <head><title>授权失败</title></head>
            <body style="font-family: sans-serif; text-align: center; padding: 50px;">
                <h1 style="color: #e74c3c;">❌ 授权失败</h1>
                <p style="color: #7f8c8d;">授权会话已过期，请重新授权</p>
                <p><a href="/" style="color: #3498db;">返回首页</a></p>
            </body>
            </html>
            """,
            status_code=400,
        )

    with open(state_file) as f:
        saved_state = json.load(f)

    if state != saved_state["state"]:
        return HTMLResponse(
            content="""
            <html>
            <head><title>授权失败</title></head>
            <body style="font-family: sans-serif; text-align: center; padding: 50px;">
                <h1 style="color: #e74c3c;">❌ 授权失败</h1>
                <p style="color: #7f8c8d;">State 验证失败</p>
                <p><a href="/" style="color: #3498db;">返回首页</a></p>
            </body>
            </html>
            """,
            status_code=400,
        )

    # 换取 Token
    try:
        client_id = saved_state["client_id"]
        client_secret = saved_state["client_secret"]

        flow = OAuthFlow(client_id, client_secret)
        tokens = flow.exchange_code_for_tokens(code)

        # 保存 Token
        token_manager.save_google_tokens(
            access_token=tokens["access_token"],
            refresh_token=tokens["refresh_token"],
            expires_in=tokens["expires_in"],
        )

        # 清理 state 文件
        state_file.unlink()

        logger.info("Google OAuth 授权成功")

        # 返回成功页面
        return HTMLResponse(
            content="""
            <html>
            <head><title>授权成功</title></head>
            <body style="font-family: sans-serif; text-align: center; padding: 50px;">
                <h1 style="color: #27ae60;">✅ 授权成功！</h1>
                <p style="color: #7f8c8d;">Google Workspace 已成功授权</p>
                <p style="color: #7f8c8d;">您现在可以关闭此页面</p>
                <script>
                    setTimeout(function() {
                        window.close();
                    }, 3000);
                </script>
            </body>
            </html>
            """
        )

    except (httpx.HTTPError, ValueError, KeyError, OSError) as e:
        logger.error(f"OAuth token exchange failed: {e}")
        return HTMLResponse(
            content=f"""
            <html>
            <head><title>授权失败</title></head>
            <body style="font-family: sans-serif; text-align: center; padding: 50px;">
                <h1 style="color: #e74c3c;">❌ 授权失败</h1>
                <p style="color: #7f8c8d;">Token 交换失败: {escape(str(e))}</p>
                <p><a href="/" style="color: #3498db;">返回首页</a></p>
            </body>
            </html>
            """,
            status_code=500,
        )


@app.get("/api/status")
async def service_status():
    """获取各渠道实时运行状态（供前端轮询）"""
    from .service_registry import get_all as registry_get_all

    status = registry_get_all()

    # 对未注册的渠道，根据配置返回 disabled
    if "telegram" not in status:
        status["telegram"] = "connected" if config.is_telegram_enabled() else "disabled"
    if "slack" not in status:
        status["slack"] = "connected" if config.is_slack_enabled() else "disabled"

    return JSONResponse(status)


@app.get("/api/oauth/status")
async def oauth_status():
    """获取 OAuth 状态（JSON API）"""
    client_id = config.get_google_oauth_client_id()
    tokens = token_manager.get_google_tokens()

    return JSONResponse(
        {
            "configured": bool(client_id),
            "authorized": bool(tokens),
            "expired": token_manager.token_expired() if tokens else True,
        }
    )


@app.post("/api/oauth/clear")
async def oauth_clear():
    """清除 OAuth Token"""
    token_manager.clear_google_tokens()
    return RedirectResponse(url="/?cleared=oauth", status_code=303)


# ============================================
# 启动
# ============================================


def start_web_ui(host: str = "0.0.0.0", port: int | None = None):
    """启动 Web UI（Issue #107：端口优先从环境变量 KUMA_WEB_PORT 读取）"""
    if port is None:
        port = config.web_ui_port
    logger.info(f"Web UI 已启动： http://{host}:{port}")
    uvicorn.run(app, host=host, port=port, log_level="warning")


if __name__ == "__main__":
    start_web_ui()
