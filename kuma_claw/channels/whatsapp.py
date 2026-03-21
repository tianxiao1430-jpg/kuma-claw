"""
WhatsApp 渠道处理器(示例)
==================
"""

import logging

from .base import ChannelHandler

logger = logging.getLogger("kuma_claw.channels.whatsapp")


class WhatsAppChannel(ChannelHandler):
    """WhatsApp 渠道处理器"""

    def __init__(self, agent, phone_id: str, verify_code: str | None = None):
        super().__init__("WhatsApp", agent)
        self.phone_id = phone_id
        self.verify_code = verify_code
        self.client = None

    async def handle_message(self, user_id: str, text: str, **kwargs) -> str:
        """处理消息"""
        return await self.run_agent(user_id, text)

    async def start(self):
        """启动 WhatsApp Bot"""
        # TODO: 实现 WhatsApp Web API 集成
        logger.info("启动 WhatsApp Bot...")
        raise NotImplementedError("WhatsApp 渠道尚未实现")

    async def stop(self):
        """停止 WhatsApp Bot"""
        logger.info("WhatsApp Bot 已停止")


def create_whatsapp_channel(agent, phone_id: str, verify_code: str | None = None) -> WhatsAppChannel:
    return WhatsAppChannel(agent, phone_id, verify_code)
