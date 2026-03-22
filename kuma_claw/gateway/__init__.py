"""
Kuma Claw Gateway - 统一入口
===========================

参考 OpenClaw 架构，提供：
- 统一消息入口
- 会话管理
- Agent 路由
- 渠道适配器管理
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable

logger = logging.getLogger("kuma_claw.gateway")


class ChannelType(Enum):
    TELEGRAM = "telegram"
    SLACK = "slack"
    DISCORD = "discord"
    WEB = "web"


@dataclass
class Message:
    """统一消息格式"""
    id: str
    channel: ChannelType
    user_id: str
    chat_id: str
    content: str
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class Reply:
    """回复消息"""
    id: str
    message_id: str
    content: str
    agent: str
    timestamp: datetime = field(default_factory=datetime.now)


class Gateway:
    """网关核心
    
    职责：
    - 统一消息入口
    - 会话管理（委托给 sessions.py）
    - Agent 路由
    - 渠道适配器管理
    """
    
    def __init__(self):
        self.channels: dict[ChannelType, Any] = {}  # channel -> ChannelHandler
        self.agents: dict[str, Any] = {}  # agent_id -> Agent
        self._running = False
        
    def register_channel(self, channel_type: ChannelType, handler: Any):
        """注册渠道处理器"""
        self.channels[channel_type] = handler
        logger.info(f"注册渠道: {channel_type.value}")
        
    def register_agent(self, agent_id: str, agent: Any):
        """注册 Agent"""
        self.agents[agent_id] = agent
        logger.info(f"注册 Agent: {agent_id}")
    
    async def process_message(self, message: Message) -> Reply:
        """处理消息（统一入口）"""
        # 获取渠道处理器
        channel = self.channels.get(message.channel)
        if not channel:
            raise ValueError(f"未注册的渠道: {message.channel}")
        
        # 调用渠道处理
        response = await channel.handle_message(
            user_id=message.user_id,
            text=message.content,
            chat_id=message.chat_id,
            metadata=message.metadata,
        )
        
        return Reply(
            id=f"reply-{message.id}",
            message_id=message.id,
            content=response,
            agent="default",
        )
    
    async def start(self):
        """启动网关"""
        self._running = True
        logger.info("网关启动")
        
        # 启动所有渠道
        tasks = []
        for channel_type, channel in self.channels.items():
            if hasattr(channel, 'start'):
                tasks.append(channel.start())
                logger.info(f"启动渠道: {channel_type.value}")
        
        if tasks:
            await asyncio.gather(*tasks)
    
    async def stop(self):
        """停止网关"""
        self._running = False
        logger.info("网关停止")
        
        # 停止所有渠道
        for channel_type, channel in self.channels.items():
            if hasattr(channel, 'stop'):
                await channel.stop()
                logger.info(f"停止渠道: {channel_type.value}")
    
    @property
    def is_running(self) -> bool:
        return self._running


# 全局网关实例
_gateway: Gateway | None = None


def get_gateway() -> Gateway:
    """获取全局网关实例"""
    global _gateway
    if _gateway is None:
        _gateway = Gateway()
    return _gateway


async def start_gateway():
    """启动网关（便捷函数）"""
    gateway = get_gateway()
    await gateway.start()


async def stop_gateway():
    """停止网关（便捷函数）"""
    gateway = get_gateway()
    await gateway.stop()
