"""
Kuma Claw - 主入口
================
"""

import asyncio
import logging
import os
import sys
import threading
import time

from .config import config

# 配置日志
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(message)s")
logger = logging.getLogger("kuma_claw")


def check_requirements():
    """检查必要配置"""
    missing = []

    # 至少需要一个渠道
    has_slack = bool(config.get_slack_bot_token())
    has_telegram = bool(config.get_telegram_token())

    if not has_slack and not has_telegram:
        missing.append("至少配置一个渠道（Slack 或 Telegram）")

    # 至少需要一个 API Key
    has_google = bool(config.get_google_api_key())
    has_openai = bool(config.get_openai_api_key())
    has_anthropic = bool(config.get_anthropic_api_key())

    if not has_google and not has_openai and not has_anthropic:
        missing.append("至少配置一个 API Key（Google/OpenAI/Anthropic)")

    return missing


def print_banner():
    """打印 Banner"""
    print("""
╔════════════════════════════════════════════════════════════╗
║          🦞 Kuma Claw - 智能 Agent 平台                    ║
║                                                            ║
║  基于 Google ADK | 多模型支持 | 本地部署                  ║
╚════════════════════════════════════════════════════════════╝
    """)


def print_status():
    """打印状态"""
    print("📊 当前状态:")
    print(f"   模型: {config.get_model()}")
    print(f"   Slack: {'✅ 已配置' if config.get_slack_bot_token() else '❌ 未配置'}")
    print(f"   Telegram: {'✅ 已配置' if config.get_telegram_token() else '❌ 未配置'}")
    print()


def main():
    """主函数"""
    import argparse

    # 注入 API Key 到环境变量
    google_key = config.get_google_api_key()
    if google_key:
        os.environ["GEMINI_API_KEY"] = google_key

    parser = argparse.ArgumentParser(description="Kuma Claw")
    parser.add_argument("--web", action="store_true", help="启动 Web UI")
    parser.add_argument("--slack", action="store_true", help="启动 Slack Bot")
    parser.add_argument("--telegram", action="store_true", help="启动 Telegram Bot")
    parser.add_argument("--all", action="store_true", help="启动所有服务")
    parser.add_argument("--port", type=int, default=8080, help="Web UI 端口")
    args = parser.parse_args()

    print_banner()
    print_status()

    # 如果没有指定任何参数， 启动 Web UI
    if not args.web and not args.slack and not args.telegram and not args.all:
        print("💡 使用 --help 查看帮助")
        print("🌐 启动 Web UI 进行配置...")
        args.web = True

    # 检查配置
    if args.slack or args.telegram or args.all:
        missing = check_requirements()
        if missing:
            print("❌ 配置不完整: ")
            for m in missing:
                print(f"   - {m}")
            print("\n💡 请先通过 Web UI 配置: kuma-claw run --web")
            sys.exit(1)

    # Web UI
    if args.web or args.all:
        from .web_ui import start_web_ui

        web_thread = threading.Thread(target=start_web_ui, kwargs={"port": args.port}, daemon=True)
        web_thread.start()
        print(f"🌐 Web UI: http://localhost:{args.port}")

    # 异步服务启动逻辑
    async def run_services():
        from .agent import create_agent
        from .gateway import ChannelType, Gateway
        from .gateway.adapters.slack import SlackAdapter
        from .gateway.adapters.telegram import TelegramAdapter

        gateway = Gateway()
        agent = create_agent()
        gateway.set_agent(agent)

        # Register adapters based on config
        if args.telegram or args.all:
            token = config.get_telegram_token()
            if token:
                adapter = TelegramAdapter(gateway, token)
                gateway.register_adapter(ChannelType.TELEGRAM, adapter)
                print("📱 Telegram Bot 已就绪")
            else:
                print("⚠️  Telegram 未配置，跳过")

        if args.slack or args.all:
            bot_token = config.get_slack_bot_token()
            app_token = config.get_slack_app_token()
            if bot_token:
                adapter = SlackAdapter(gateway, bot_token, app_token)
                gateway.register_adapter(ChannelType.SLACK, adapter)
                print("💬 Slack Bot 已就绪")
            else:
                print("⚠️  Slack 未配置，跳过")

        await gateway.start()

        # Keep running
        try:
            while True:
                await asyncio.sleep(3600)
        except (asyncio.CancelledError, KeyboardInterrupt):
            pass
        finally:
            await gateway.stop()

    if args.slack or args.telegram or args.all:
        try:
            asyncio.run(run_services())
        except KeyboardInterrupt:
            print("\n👋 再见!")

    # 如果只启动了 Web，保持运行
    elif args.web:
        print("\n✅ Kuma Claw 运行中...")
        print("   按 Ctrl+C 退出")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n👋 再见!")


if __name__ == "__main__":
    main()
