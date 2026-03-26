"""
Kuma Claw Gateway - Telegram 适配器
==================================

Telegram Bot 集成，支持命令、文本和图片消息。
"""

from __future__ import annotations

import logging
import uuid
from typing import TYPE_CHECKING

import httpx
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from kuma_claw.service_registry import set_status

from .. import ChannelType, Message
from ..session_manager import SessionKey
from .base import BaseAdapter

if TYPE_CHECKING:
    from ..gateway import Gateway

logger = logging.getLogger("kuma_claw.gateway.adapters.telegram")


class TelegramAdapter(BaseAdapter):
    """Telegram 适配器"""

    channel = ChannelType.TELEGRAM

    def __init__(self, gateway: Gateway, token: str):
        super().__init__(gateway)
        self.token = token
        self.app: Application | None = None

    async def start(self):
        """启动 Telegram Bot"""
        self.app = Application.builder().token(self.token).build()

        # 注册命令处理器
        self.app.add_handler(CommandHandler("start", self._cmd_start))
        self.app.add_handler(CommandHandler("help", self._cmd_help))
        self.app.add_handler(CommandHandler("clear", self._cmd_clear))

        # 注册消息处理器
        self.app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self._handle_text))
        self.app.add_handler(MessageHandler(filters.PHOTO, self._handle_photo))

        logger.info("Telegram Bot 启动中...")
        set_status("telegram", "starting")
        try:
            await self.app.initialize()
            await self.app.start()
            await self.app.updater.start_polling()
            set_status("telegram", "connected")
        except (RuntimeError, ValueError, OSError) as e:
            set_status("telegram", "error", str(e))
            raise

    async def stop(self):
        """停止 Telegram Bot"""
        if self.app:
            await self.app.updater.stop()
            await self.app.stop()
            await self.app.shutdown()
            set_status("telegram", "disabled")
            logger.info("Telegram Bot 已停止")

    async def send(self, chat_id: str, content: str, **kwargs):
        """发送消息到 Telegram 聊天"""
        if self.app:
            await self.app.bot.send_message(chat_id=int(chat_id), text=content)

    # ========================================
    # 命令处理器
    # ========================================

    async def _cmd_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """处理 /start 命令"""
        user = update.effective_user
        await update.message.reply_text(
            f"🦞 你好 {user.first_name}！我是 Kuma Claw。\n\n"
            "我可以帮你：\n"
            "• 搜索网络信息\n"
            "• 管理邮件和日历\n"
            "• 记住重要信息\n\n"
            "发送 /help 查看更多命令。"
        )

    async def _cmd_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """处理 /help 命令"""
        await update.message.reply_text(
            "🦞 **Kuma Claw 帮助**\n\n"
            "**基础命令：**\n"
            "/start - 开始对话\n"
            "/help - 显示帮助\n"
            "/clear - 清除会话\n\n"
            "**功能示例：**\n"
            "• 搜索明天的天气\n"
            "• 查看我的日程\n"
            "• 记住我喜欢简洁回复\n"
            "• 发送邮件给 xxx@example.com",
            parse_mode="Markdown",
        )

    async def _cmd_clear(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """处理 /clear 命令"""
        user_id = str(update.effective_user.id)
        chat_id = str(update.effective_chat.id)

        key = SessionKey(
            channel=ChannelType.TELEGRAM.value,
            user_id=user_id,
            scope=chat_id,
        )
        success = await self.gateway.session_manager.clear(key)

        if success:
            await update.message.reply_text("✅ 会话已清除")
        else:
            await update.message.reply_text("⚠️ 没有活跃的会话")

    # ========================================
    # 消息处理器
    # ========================================

    async def _handle_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """处理文本消息"""
        user_id = str(update.effective_user.id)
        chat_id = str(update.effective_chat.id)
        text = update.message.text

        # 显示"正在输入"
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")

        # 构造统一消息
        message = Message(
            id=str(uuid.uuid4()),
            channel=ChannelType.TELEGRAM,
            user_id=user_id,
            chat_id=chat_id,
            content=text,
            metadata={},
        )

        # 通过 Gateway 处理
        reply = await self.gateway.process_message(message)

        # 发送响应
        await update.message.reply_text(reply.content)

    async def _handle_photo(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """处理图片消息"""
        user_id = str(update.effective_user.id)
        chat_id = str(update.effective_chat.id)

        # 获取图片（最高分辨率）
        photo = update.message.photo[-1]
        text = update.message.caption or "请分析这张图片"

        # 获取图片文件并下载为 bytes
        photo_file = await context.bot.get_file(photo.file_id)
        photo_url = photo_file.file_path

        async with httpx.AsyncClient() as client:
            response = await client.get(photo_url)
            photo_bytes = response.content

        # 显示"正在输入"
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")

        # 构造统一消息（带图片）
        message = Message(
            id=str(uuid.uuid4()),
            channel=ChannelType.TELEGRAM,
            user_id=user_id,
            chat_id=chat_id,
            content=text,
            metadata={
                "images": [(photo_bytes, "image/jpeg")],
            },
        )

        # 通过 Gateway 处理
        reply = await self.gateway.process_message(message)

        # 发送响应
        await update.message.reply_text(reply.content)


# ========================================
# 工厂函数
# ========================================


def create_telegram_adapter(gateway: Gateway, token: str) -> TelegramAdapter:
    """创建 Telegram 适配器实例

    Args:
        gateway: Gateway 实例
        token: Telegram Bot Token

    Returns:
        TelegramAdapter 实例
    """
    return TelegramAdapter(gateway, token)


async def start_telegram_adapter(gateway: Gateway, token: str) -> TelegramAdapter:
    """启动 Telegram 适配器（快捷方式）

    Args:
        gateway: Gateway 实例
        token: Telegram Bot Token

    Returns:
        TelegramAdapter 实例
    """
    adapter = create_telegram_adapter(gateway, token)
    await adapter.start()
    return adapter
