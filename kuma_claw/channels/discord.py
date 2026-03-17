"""
Discord 渠道处理器（示例)
==================
"""

import logging

from discord.ext import commands

from .base import ChannelHandler
from .formats import extract_internal_content

logger = logging.getLogger("kuma_claw.channels.discord")


class DiscordChannel(ChannelHandler):
    """Discord 渠道处理器"""

    def __init__(self, agent, token: str):
        super().__init__("Discord", agent)
        self.token = token
        self.app = None

    async def handle_message(self, user_id: str, text: str, **kwargs) -> str:
        """处理消息"""
        return await self.run_agent(user_id, text)

    async def start(self):
        """启动 Discord Bot"""
        self.app = commands.Bot(command_prefix="!", case_insensitive=True)

        @self.app.event
        async def on_message(message):
            """处理消息"""
            user_id = str(message.author.id)

            # 处理命令
            if message.content.startswith("!"):
                return

            # 处理文本
            text = message.content
            response = await self.run_agent(user_id, text)

            # 提取内部内容
            _, final_response = extract_internal_content(response)

            # 发送响应
            await message.reply(final_response)

    async def stop(self):
        """停止 Discord Bot"""
        if self.app:
            await self.app.close()
            logger.info("Discord Bot 已停止")


def create_discord_channel(agent, token: str) -> DiscordChannel:
    return DiscordChannel(agent, token)
