"""
Kuma Claw Gateway - Adapter 基类
==============================

所有渠道适配器的基类。
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Awaitable, Callable, Optional

from .. import ChannelType, Message, Reply

if TYPE_CHECKING:
    from ..gateway import Gateway


class BaseAdapter(ABC):
    """适配器基类"""

    channel: ChannelType

    def __init__(self, gateway: Gateway):
        self.gateway = gateway
        self.on_message: Optional[Callable[[Message], Awaitable[Reply]]] = None

    @abstractmethod
    async def start(self):
        """启动适配器"""
        pass

    @abstractmethod
    async def stop(self):
        """停止适配器"""
        pass

    @abstractmethod
    async def send(self, chat_id: str, content: str, **kwargs):
        """发送消息"""
        pass

    async def _handle_message(self, message: Message) -> Reply:
        """处理接收到的消息"""
        if self.on_message:
            return await self.on_message(message)
        return await self.gateway.process_message(message)
