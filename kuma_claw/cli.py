"""
Kuma Claw - CLI 入口
==================

类似 OpenClaw 的安装体验：
- kuma-claw init    # 初始化配置
- kuma-claw config  # 配置向导
- kuma-claw run     # 启动服务（旧方式）
- kuma-claw gateway # 启动网关（新方式）
- kuma-claw doctor  # 健康检查
"""

import subprocess
import sys
from pathlib import Path

import click
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.table import Table

from .i18n import i18n

console = Console()


def print_banner():
    """打印 Banner"""
    console.print(
        Panel.fit(
            f"[bold cyan]🦞 {i18n.t('banner_title')}[/bold cyan]\n\n"
            f"[dim]{i18n.t('banner_desc')}[/dim]",
            border_style="cyan",
        )
    )


def check_python_version():
    """检查 Python 版本"""
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 10):
        console.print(f"[red]{i18n.t('python_req')}[/red]")
        return False
    console.print(f"[green]✅ Python {version.major}.{version.minor}.{version.micro}[/green]")
    return True


def check_dependencies():
    """检查依赖"""
    deps = {
        "google-adk": "google.genai",
        "slack-bolt": "slack_bolt",
        "python-telegram-bot": "telegram",
        "fastapi": "fastapi",
        "websockets": "websockets",
    }

    missing = []
    for name, module in deps.items():
        try:
            __import__(module.split(".")[0])
            console.print(f"[green]  ✅ {name}[/green]")
        except ImportError:
            console.print(f"[yellow]  ⚠️  {name} ({i18n.t('not_installed')})[/yellow]")
            missing.append(name)

    return missing


# ============================================
# 可用模型列表
# ============================================

AVAILABLE_MODELS = {
    "Gemini 3.1 (最新)": [
        ("gemini-3.1-pro", "🧠 最强智能，复杂问题，代码生成"),
        ("gemini-3.1-flash", "⚡ 快速高效（推荐）"),
        ("gemini-3.1-flash-lite-preview", "💨 极低成本，高性能"),
    ],
    "Gemini 3 (预览版)": [
        ("gemini-3-pro", "🔬 最先进多模态理解"),
        ("gemini-3-flash", "⚡ 极低成本卓越性能"),
    ],
    "Nano Banana (轻量)": [
        ("nano-banana-2", "🍌 高速大容量"),
        ("nano-banana-pro", "🍌 复杂任务支持"),
    ],
    "Gemini 2.0": [
        ("gemini-2.0-flash", "🚀 稳定快速响应"),
        ("gemini-2.0-flash-lite-preview", "💨 轻量版极速响应"),
        ("gemini-2.0-pro-exp", "🔬 实验版前沿功能"),
    ],
    "Gemini 1.5 (经典)": [
        ("gemini-1.5-flash", "📦 稳定可靠"),
        ("gemini-1.5-flash-8b", "📦 经济版成本优化"),
        ("gemini-1.5-pro", "📦 经典强大能力"),
    ],
    "GPT (OpenAI)": [
        ("openai/gpt-4.1", "🆕 最新 GPT-4.1"),
        ("openai/gpt-4.1-mini", "🆕 GPT-4.1 Mini"),
        ("openai/gpt-4.1-nano", "🆕 GPT-4.1 Nano"),
        ("openai/gpt-4o", "🎯 GPT-4 Omni"),
        ("openai/gpt-4o-mini", "⚡ GPT-4 Omni Mini"),
        ("openai/o3-mini", "🧠 O3 Mini 推理模型"),
    ],
    "Claude (Anthropic)": [
        ("anthropic/claude-3.7-sonnet", "🆕 最新 Claude 3.7 Sonnet"),
        ("anthropic/claude-3.5-sonnet", "🎯 Claude 3.5 Sonnet"),
        ("anthropic/claude-3.5-haiku", "⚡ Claude 3.5 Haiku"),
    ],
    "DeepSeek": [
        ("deepseek/deepseek-chat", "💬 DeepSeek Chat"),
        ("deepseek/deepseek-reasoner", "🧠 DeepSeek Reasoner"),
    ],
    "本地模型 (Ollama)": [
        ("ollama/llama3.3", "🦙 Llama 3.3"),
        ("ollama/llama3.2", "🦙 Llama 3.2"),
        ("ollama/qwen2.5", "🌟 Qwen 2.5"),
        ("ollama/deepseek-r1", "🧠 DeepSeek R1"),
        ("ollama/gemma3", "💎 Gemma 3"),
    ],
}


def get_all_models_flat():
    """获取扁平化的模型列表"""
    models = []
    for model_list in AVAILABLE_MODELS.values():
        models.extend(model_list)
    return models


# ============================================
# Commands
# ============================================


@click.group()
def cli():
    """Kuma Claw - 智能 Agent 平台"""
    pass


@cli.command()
@click.option("--non-interactive", is_flag=True, help="非交互模式")
def init(non_interactive: bool):
    if not non_interactive:
        i18n.prompt_language()
    """初始化配置（类似 openclaw setup）"""
    print_banner()
    console.print()

    # 1. 检查 Python 版本
    console.print(f"[bold]{i18n.t('env_check')}[/bold]")
    if not check_python_version():
        sys.exit(1)
    console.print()

    # 2. 检查依赖
    console.print(f"[bold]{i18n.t('dep_check')}[/bold]")
    missing = check_dependencies()
    if missing:
        console.print()
        if non_interactive:
            console.print(f"[yellow]{i18n.t('missing_dep')}: {', '.join(missing)}[/yellow]")
            console.print(f"{i18n.t('run_cmd')}: [cyan]pip install -r requirements.txt[/cyan]")
            sys.exit(1)

        if Confirm.ask(i18n.t("install_missing")):
            console.print(f"[cyan]{i18n.t('installing')}[/cyan]")
            subprocess.run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
    console.print()

    # 3. 配置向导
    if not non_interactive:
        run_config_wizard()

    console.print()
    console.print(
        Panel.fit(
            f"[green]{i18n.t('init_done')}[/green]\n\n[cyan]{i18n.t('next_step')}[/cyan]\n"
            f"  [bold]kuma-claw run --web[/bold]      {i18n.t('start_web')}\n"
            f"  [bold]kuma-claw run --telegram[/bold] {i18n.t('start_tg')}",
            title=i18n.t("success"),
            border_style="green",
        )
    )


@cli.command()
@click.option(
    "--section",
    type=click.Choice(["api", "channels", "model", "oauth", "all"]),
    default="all",
)
def config(section: str):
    """配置向导（类似 openclaw configure）"""
    print_banner()
    run_config_wizard(section)


def run_config_wizard(section: str = "all"):
    """运行配置向导"""
    from .config import config as app_config

    # API Keys
    if section in ["api", "all"]:
        console.print("[bold]🔑 API 配置[/bold]")
        console.print("[dim]至少配置一个 API Key[/dim]")
        console.print()

        # Google
        current = "已配置" if app_config.get_google_api_key() else "未配置"
        google_key = Prompt.ask(f"Google API Key [{current}]", default="", show_default=False)
        if google_key:
            app_config.set_google_api_key(google_key)
            console.print("[green]✅ Google API Key 已保存[/green]")

        # OpenAI (可选)
        openai_key = Prompt.ask("OpenAI API Key (可选)", default="", show_default=False)
        if openai_key:
            app_config.set_openai_api_key(openai_key)
            console.print("[green]✅ OpenAI API Key 已保存[/green]")

        console.print()

    # OAuth (Google Workspace)
    if section in ["oauth", "all"]:
        run_oauth_config(app_config)

    # Channels
    if section in ["channels", "all"]:
        console.print("[bold]📱 渠道配置[/bold]")
        console.print("[dim]至少配置一个渠道[/dim]")
        console.print()

        # Telegram
        telegram_enabled = app_config.is_telegram_enabled()
        status = "✅ 已启用" if telegram_enabled else "❌ 未配置"
        console.print(f"Telegram: {status}")

        if Confirm.ask("配置 Telegram？", default=not telegram_enabled):
            token = Prompt.ask("Telegram Bot Token")
            if token:
                app_config.set_telegram_token(token)
                console.print("[green]✅ Telegram 已配置[/green]")

        # Slack
        slack_enabled = app_config.is_slack_enabled()
        status = "✅ 已启用" if slack_enabled else "❌ 未配置"
        console.print(f"Slack: {status}")

        if Confirm.ask("配置 Slack？", default=False):
            bot_token = Prompt.ask("Slack Bot Token (xoxb-...)")
            app_token = Prompt.ask("Slack App Token (xapp-...)")
            if bot_token and app_token:
                app_config.set_slack_tokens(bot_token, app_token)
                console.print("[green]✅ Slack 已配置[/green]")

        console.print()

    # Model
    if section in ["model", "all"]:
        run_model_selection(app_config)


def run_oauth_config(app_config):
    """配置 Google OAuth"""
    from .auth import ADKCLAW_OFFICIAL_CLIENT_ID, token_manager

    console.print("[bold]🔐 Google Workspace OAuth 配置[/bold]")
    console.print("[dim]用于 Gmail/Calendar/Sheets/Docs 集成[/dim]")
    console.print()

    # 检查当前状态
    client_id = app_config.get_google_oauth_client_id()
    tokens = token_manager.get_google_tokens()

    # 显示状态
    if tokens:
        console.print("[green]  ✅ Google Workspace 已授权[/green]")
        console.print()
        console.print("[dim]已授权的服务：[/dim]")
        console.print("[dim]  • Gmail - 发送/读取邮件[/dim]")
        console.print("[dim]  • Calendar - 管理日程[/dim]")
        console.print("[dim]  • Sheets - 读写表格[/dim]")
        console.print("[dim]  • Docs - 创建文档[/dim]")
        console.print()

        if Confirm.ask("重新授权？", default=False):
            run_oauth_authorization(client_id or ADKCLAW_OFFICIAL_CLIENT_ID, "")
        return

    console.print("[yellow]  ○ Google Workspace 未启用[/yellow]")
    console.print()

    # 选择授权方式
    console.print("[bold]选择授权方式：[/bold]")
    console.print()

    if ADKCLAW_OFFICIAL_CLIENT_ID:
        console.print("  [cyan]1[/cyan]. 🚀 快速授权（推荐）")
        console.print("      [dim]使用 KumaClaw 官方 Client ID，一键授权[/dim]")
        console.print()

    console.print(
        f"  [cyan]{2 if ADKCLAW_OFFICIAL_CLIENT_ID else 1}[/cyan]. 🔧 自定义 Client ID（高级）"
    )
    console.print("      [dim]使用您自己的 Google Cloud 项目[/dim]")
    console.print()

    choice = Prompt.ask("选择", default="1" if ADKCLAW_OFFICIAL_CLIENT_ID else "2")

    if choice == "1" and ADKCLAW_OFFICIAL_CLIENT_ID:
        # 使用官方 Client ID
        console.print()
        console.print("[cyan]🌐 正在准备授权...[/cyan]")
        run_oauth_authorization(ADKCLAW_OFFICIAL_CLIENT_ID, "")

    else:
        # 自定义 Client ID
        console.print()
        console.print(
            Panel.fit(
                "[cyan]📋 创建 Google OAuth Client ID 步骤：[/cyan]\n\n"
                "1. 访问 [link]https://console.cloud.google.com/apis/credentials[/link]\n"
                "2. 点击 [bold]Create Credentials[/bold] → [bold]OAuth client ID[/bold]\n"
                "3. 选择 [bold]Desktop app[/bold] 类型\n"
                "4. 添加授权重定向 URI:\n"
                "   [dim]http://localhost:8080/oauth/callback[/dim]\n"
                "5. 复制 Client ID",
                title="配置指南",
                border_style="cyan",
            )
        )
        console.print()

        client_id_input = Prompt.ask("Google OAuth Client ID")

        if client_id_input:
            # 保存 Client ID（不保存 secret，Desktop app 不需要）
            app_config.set_google_oauth(client_id_input, "")
            console.print("[green]✅ Client ID 已保存[/green]")
            console.print()

            if Confirm.ask("现在进行授权？", default=True):
                run_oauth_authorization(client_id_input, "")

    console.print()


def run_oauth_authorization(client_id: str, client_secret: str):
    """运行 OAuth 授权流程"""
    from .auth import OAuthFlow

    console.print("[bold]🌐 启动 OAuth 授权流程[/bold]")
    console.print()

    # 创建 OAuth 流程
    flow = OAuthFlow(client_id, client_secret)

    # 提示用户
    console.print(
        Panel.fit(
            "[yellow]⚠️  请按以下步骤操作：[/yellow]\n\n"
            "1. 浏览器将自动打开 Google 授权页面\n"
            "2. 登录您的 Google 账号\n"
            "3. 授权 Kuma Claw 访问您的 Google Workspace\n"
            "4. 授权成功后会自动跳转",
            title="授权步骤",
            border_style="yellow",
        )
    )
    console.print()

    if not Confirm.ask("准备好了吗？", default=True):
        console.print(
            "[yellow]已取消授权。稍后运行 [bold]kuma-claw oauth-authorize[/bold] 进行授权。[/yellow]"
        )
        return

    # 保存 state 用于验证
    import json

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

    # 打开浏览器
    console.print("[cyan]正在打开浏览器...[/cyan]")
    flow.start_authorization()

    console.print()
    console.print(
        Panel.fit(
            "[yellow]⏳ 等待授权...[/yellow]\n\n"
            "[dim]完成授权后，页面会自动显示成功信息[/dim]\n\n"
            "[cyan]如果没有自动打开浏览器，请手动访问：[/cyan]\n"
            f"[link]{flow.get_authorization_url()}[/link]",
            title="OAuth 授权",
            border_style="yellow",
        )
    )

    console.print()
    console.print("[dim]提示：授权完成后，运行 [bold]kuma-claw oauth-status[/bold] 查看状态[/dim]")


@cli.command()
def oauth_authorize():
    """启动 Google OAuth 授权流程"""
    from .config import config as app_config

    print_banner()
    console.print()

    client_id = app_config.get_google_oauth_client_id()
    client_secret = app_config.get_google_oauth_client_secret()

    if not client_id or not client_secret:
        console.print("[red]❌ OAuth 凭证未配置[/red]")
        console.print()
        console.print("[cyan]请先运行：[/cyan]")
        console.print("  [bold]kuma-claw config --section oauth[/bold]")
        return

    run_oauth_authorization(client_id, client_secret)


@cli.command()
def oauth_status():
    """查看 Google OAuth 状态"""
    from .auth import token_manager
    from .config import config as app_config

    print_banner()
    console.print()

    console.print("[bold]🔐 Google OAuth 状态[/bold]")
    console.print()

    # 凭证状态
    client_id = app_config.get_google_oauth_client_id()
    client_secret = app_config.get_google_oauth_client_secret()

    if client_id and client_secret:
        console.print("[green]  ✅ OAuth 凭证已配置[/green]")
        console.print(f"[dim]     Client ID: {client_id[:20]}...[/dim]")
    else:
        console.print("[red]  ❌ OAuth 凭证未配置[/red]")

    # Token 状态
    tokens = token_manager.get_google_tokens()

    if tokens:
        from datetime import datetime

        expires_at = datetime.fromisoformat(tokens["expires_at"])
        is_expired = token_manager.token_expired()

        if is_expired:
            console.print("[yellow]  ⚠️  Token 已过期（需要刷新）[/yellow]")
        else:
            console.print(
                f"[green]  ✅ Token 有效（过期时间: {expires_at.strftime('%Y-%m-%d %H:%M')}）[/green]"  # noqa: E501
            )

        console.print(f"[dim]     更新时间: {tokens['updated_at']}[/dim]")
    else:
        console.print("[red]  ❌ Token 未获取[/red]")

    console.print()

    # 可用服务
    if client_id and client_secret and tokens and not token_manager.token_expired():
        console.print("[bold]📦 可用服务：[/bold]")
        console.print("  [green]✅ Gmail[/green] - 发送/读取邮件")
        console.print("  [green]✅ Calendar[/green] - 管理日程")
        console.print("  [green]✅ Sheets[/green] - 读写表格")
        console.print("  [green]✅ Docs[/green] - 创建文档")
        console.print()


@cli.command()
def oauth_clear():
    """清除 Google OAuth Token"""
    from .auth import token_manager

    print_banner()
    console.print()

    if Confirm.ask("确定要清除 Google OAuth Token 吗？", default=False):
        token_manager.clear_google_tokens()
        console.print("[green]✅ Token 已清除[/green]")
    else:
        console.print("[yellow]已取消[/yellow]")


def run_model_selection(app_config):
    """运行模型选择向导"""
    console.print("[bold]🤖 模型配置[/bold]")
    console.print("[dim]选择 AI 模型（按数字选择）[/dim]")
    console.print()

    current = app_config.get_model()

    # 显示所有模型
    idx = 1
    model_map = {}

    for provider, models in AVAILABLE_MODELS.items():
        console.print(f"[bold yellow]{provider}[/bold yellow]")
        for model_id, desc in models:
            marker = " ✓" if model_id == current else ""
            console.print(f"  [cyan]{idx:2d}[/cyan]. {model_id:35s} [dim]{desc}[/dim]{marker}")
            model_map[idx] = model_id
            idx += 1
        console.print()

    # 选择
    choice = Prompt.ask(f"选择模型 (当前: {current})", default="1")

    try:
        selected_idx = int(choice)
        if selected_idx in model_map:
            selected_model = model_map[selected_idx]
            app_config.set_model(selected_model)
            console.print(f"[green]✅ 模型已设置为 {selected_model}[/green]")
    except ValueError:
        console.print("[yellow]无效选择，保持当前模型[/yellow]")

    console.print()


@cli.command()
@click.option("--web", is_flag=True, help="启动 Web UI")
@click.option("--slack", is_flag=True, help="启动 Slack Bot")
@click.option("--telegram", is_flag=True, help="启动 Telegram Bot")
@click.option("--all", "all_services", is_flag=True, help="启动所有服务")
@click.option("--port", default=8080, help="Web UI 端口")
def run(web: bool, slack: bool, telegram: bool, all_services: bool, port: int):
    """启动服务"""
    from .main import main as run_main

    # 构建参数
    args = []
    if web or all_services:
        args.append("--web")
        args.extend(["--port", str(port)])
    if slack or all_services:
        args.append("--slack")
    if telegram or all_services:
        args.append("--telegram")
    if all_services:
        args.append("--all")

    if not args:
        args = ["--web"]

    # 调用 main.py（同步调用，不用 asyncio）
    sys.argv = ["main.py"] + args
    run_main()


@cli.command()
def doctor():
    """健康检查（类似 openclaw doctor）"""
    print_banner()
    console.print()

    from .auth import token_manager
    from .config import config as app_config

    issues = []

    # Python
    console.print("[bold]📋 环境[/bold]")
    check_python_version()
    console.print()

    # Dependencies
    console.print("[bold]📦 依赖[/bold]")
    missing = check_dependencies()
    if missing:
        issues.append(f"缺少依赖: {', '.join(missing)}")
    console.print()

    # Config
    console.print("[bold]⚙️  配置[/bold]")

    # API Keys
    has_api = bool(
        app_config.get_google_api_key()
        or app_config.get_openai_api_key()
        or app_config.get_anthropic_api_key()
    )
    if has_api:
        console.print("[green]  ✅ API Key 已配置[/green]")
    else:
        console.print("[red]  ❌ API Key 未配置[/red]")
        issues.append("API Key 未配置")

    # Channels
    has_channel = app_config.is_telegram_enabled() or app_config.is_slack_enabled()
    if has_channel:
        console.print("[green]  ✅ 渠道已配置[/green]")
    else:
        console.print("[yellow]  ⚠️  渠道未配置[/yellow]")
        issues.append("渠道未配置（仅 Web UI 可用）")

    # OAuth
    client_id = app_config.get_google_oauth_client_id()
    tokens = token_manager.get_google_tokens()
    if client_id and tokens:
        console.print("[green]  ✅ Google Workspace 已配置[/green]")
    elif client_id:
        console.print("[yellow]  ⚠️  Google Workspace 凭证已配置，但未授权[/yellow]")
        issues.append("Google Workspace 未授权")
    else:
        console.print("[dim]  ○ Google Workspace 未配置（可选）[/dim]")

    console.print()

    # Summary
    if issues:
        console.print(
            Panel.fit(
                "[yellow]⚠️  发现问题：[/yellow]\n" + "\n".join(f"  • {i}" for i in issues),
                title="诊断结果",
                border_style="yellow",
            )
        )
        console.print()
        console.print("[cyan]修复建议：[/cyan]")
        console.print("  [bold]kuma-claw config[/bold]  运行配置向导")
    else:
        console.print(
            Panel.fit("[green]✅ 所有检查通过！[/green]", title="诊断结果", border_style="green")
        )


@cli.command()
def version():
    """显示版本"""
    from . import __version__

    console.print(f"[bold cyan]Kuma Claw[/bold cyan] v{__version__}")


@cli.command("list-models")
def list_models():
    """列出所有可用模型"""
    console.print(Panel.fit("[bold cyan]🤖 可用模型列表[/bold cyan]", border_style="cyan"))
    console.print()

    for provider, models in AVAILABLE_MODELS.items():
        console.print(f"[bold yellow]{provider}[/bold yellow]")
        table = Table(show_header=False, box=None, padding=(0, 2))
        for model_id, desc in models:
            table.add_row(f"[cyan]{model_id}[/cyan]", f"[dim]{desc}[/dim]")
        console.print(table)
        console.print()


# ============================================
# Entry Point
# ============================================


if __name__ == "__main__":
    cli()
