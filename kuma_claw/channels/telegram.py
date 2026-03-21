"""
Telegram 渠道处理器
===================
"""

import logging

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

from ..service_registry import set_status
from .base import ChannelHandler
from .formats import extract_internal_content

logger = logging.getLogger("kuma_claw.channels.telegram")


class TelegramChannel(ChannelHandler):
    """Telegram 渠道处理器"""

    def __init__(self, agent, token: str):
        super().__init__("Telegram", agent)
        self.token = token
        self.app = None

    async def handle_message(self, user_id: str, text: str, **kwargs) -> str:
        """处理消息"""
        return await self.run_agent(user_id, text)

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
        except Exception as e:
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
        success = await self.session_manager.clear_session(user_id)

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
        text = update.message.text

        # 显示"正在输入"
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")

        # 运行 Agent
        response = await self.handle_message(user_id, text)

        # 提取内部内容（不发送给用户）
        _, final_response = extract_internal_content(response)

        # 发送响应
        await update.message.reply_text(final_response)

    async def _handle_photo(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """处理图片消息"""
        user_id = str(update.effective_user.id)

        # 获取图片
        photo = update.message.photo[-1]
        text = update.message.caption or "请分析这张图片"

        # 获取图片文件
        photo_file = await context.bot.get_file(photo.file_id)
        photo_url = photo_file.file_path

        # 运行 Agent（带图片）
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")

        response = await self.run_agent(user_id, text, images=[photo_url])
        _, final_response = extract_internal_content(response)

        await update.message.reply_text(final_response)


# ========================================
# 工厂函数
# ========================================


def create_telegram_channel(agent, token: str) -> TelegramChannel:
    """创建 Telegram 渠道实例

    Args:
        agent: ADK Agent 实例
        token: Telegram Bot Token

    Returns:
        TelegramChannel 实例
    """
    return TelegramChannel(agent, token)


async def start_telegram_bot(agent, token: str):
    """启动 Telegram Bot（快捷方式）

    Args:
        agent: ADK Agent 实例
        token: Telegram Bot Token

    Returns:
        TelegramChannel 实例
    """
    channel = create_telegram_channel(agent, token)
    await channel.start()
    return channel
