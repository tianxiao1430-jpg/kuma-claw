"""
Kuma Claw Gateway - Telegram 适配器
=================================

处理 Telegram 消息。
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from telegram import Bot, Update
from telegram.ext import Application, ContextTypes, MessageHandler, filters

from .. import ChannelType, Message
from .base import BaseAdapter

if TYPE_CHECKING:
    from ..gateway import Gateway


class TelegramAdapter(BaseAdapter):
    """Telegram 适配器"""

    channel = ChannelType.TELEGRAM

    def __init__(self, gateway: Gateway, token: str):
        super().__init__(gateway)
        self.token = token
        self.app: Application | None = None
        self.bot: Bot | None = None

    async def start(self):
        """启动 Telegram Bot"""
        self.app = Application.builder().token(self.token).build()
        self.bot = self.app.bot

        # 添加消息处理器
        handler = MessageHandler(filters.TEXT & ~filters.COMMAND, self._handle_update)
        self.app.add_handler(handler)

        # 启动 polling
        await self.app.initialize()
        await self.app.start()
        await self.app.updater.start_polling()

    async def stop(self):
        """停止 Telegram Bot"""
        if self.app:
            await self.app.updater.stop()
            await self.app.stop()
            await self.app.shutdown()

    async def send(self, chat_id: str, content: str, **kwargs):
        """发送消息到 Telegram"""
        if self.bot:
            await self.bot.send_message(chat_id=chat_id, text=content)

    async def _handle_update(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """处理 Telegram Update"""
        if not update.message or not update.message.text:
            return

        # 转换为统一消息格式
        message = Message(
            id=str(update.message.message_id),
            channel=ChannelType.TELEGRAM,
            user_id=str(update.effective_user.id),
            chat_id=str(update.effective_chat.id),
            content=update.message.text,
            metadata={
                "username": update.effective_user.username,
                "first_name": update.effective_user.first_name,
                "mentions": self._extract_mentions(update.message.text),
            },
        )

        # 处理消息
        reply = await self._handle_message(message)

        # 发送回复
        if reply:
            await self.send(message.chat_id, reply.content)

    def _extract_mentions(self, text: str) -> list:
        """提取 @ 提及"""
        return re.findall(r"@(\w+)", text)
