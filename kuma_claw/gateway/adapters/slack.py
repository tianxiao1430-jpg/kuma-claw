"""
Kuma Claw Gateway - Slack 适配器
===============================

Slack Bot 集成，支持 app_mention 事件、线程隔离和图片下载。
"""

from __future__ import annotations

import logging
import re
import uuid
from typing import TYPE_CHECKING

import httpx
from slack_bolt.adapter.socket_mode.async_handler import AsyncSocketModeHandler
from slack_bolt.async_app import AsyncApp

from kuma_claw.service_registry import set_status

from .. import ChannelType, Message
from .base import BaseAdapter

if TYPE_CHECKING:
    from ..gateway import Gateway

logger = logging.getLogger("kuma_claw.gateway.adapters.slack")


class SlackAdapter(BaseAdapter):
    """Slack 适配器"""

    channel = ChannelType.SLACK

    def __init__(self, gateway: Gateway, bot_token: str, app_token: str):
        super().__init__(gateway)
        self.bot_token = bot_token
        self.app_token = app_token
        self.app: AsyncApp | None = None
        self.handler: AsyncSocketModeHandler | None = None
        self.http_client = httpx.AsyncClient(timeout=30.0)

    async def start(self):
        """启动 Slack Bot"""
        self.app = AsyncApp(token=self.bot_token)

        @self.app.event("app_mention")
        async def handle_app_mention(body, client, logger_bolt):
            """处理 @ 提及"""
            event = body["event"]
            channel = event["channel"]
            thread_ts = event.get("thread_ts") or event["ts"]
            user_id = event["user"]

            # 提取文本并移除 bot mention
            text = event.get("text", "")
            text = re.sub(r"<@[^>]+>", "", text).strip()

            logger.debug(f"Slack 消息: user={user_id}, channel={channel}, thread={thread_ts}")

            # 提取图片（如果有）
            files = event.get("files", [])
            images: list[tuple[bytes, str]] = []

            if files:
                logger.info(f"检测到 {len(files)} 个文件附件")

                for f in files:
                    url_private = f.get("url_private")
                    if url_private:
                        try:
                            img_bytes, mime_type = await self._download_image(url_private)
                            images.append((img_bytes, mime_type))
                            logger.debug(f"成功下载图片: {mime_type}")
                        except (RuntimeError, ValueError, OSError) as e:
                            logger.error(f"下载图片失败: {e}")
                            await client.chat_postMessage(
                                channel=channel,
                                text=f"⚠️ 无法下载图片: {str(e)}",
                                thread_ts=thread_ts,
                            )

            # 构造统一消息
            # scope 使用 channel:thread_ts 实现线程隔离
            metadata: dict = {
                "scope": f"{channel}:{thread_ts}",
            }
            if images:
                metadata["images"] = images

            message = Message(
                id=str(uuid.uuid4()),
                channel=ChannelType.SLACK,
                user_id=user_id,
                chat_id=channel,
                content=text,
                metadata=metadata,
            )

            # 通过 Gateway 处理
            try:
                reply = await self.gateway.process_message(message)

                # 发送响应到线程
                await client.chat_postMessage(
                    channel=channel,
                    text=reply.content,
                    thread_ts=thread_ts,
                )

            except (RuntimeError, ValueError, OSError) as e:
                logger.error(f"处理消息失败: {e}")
                await client.chat_postMessage(
                    channel=channel,
                    text=f"❌ 处理请求时出错: {str(e)}",
                    thread_ts=thread_ts,
                )

        self.handler = AsyncSocketModeHandler(self.app, self.app_token)
        set_status("slack", "starting")
        try:
            await self.handler.start_async()
            set_status("slack", "connected")
            logger.info("Slack Bot 已启动")
        except (RuntimeError, ValueError, OSError) as e:
            set_status("slack", "error", str(e))
            raise

    async def stop(self):
        """停止 Slack Bot"""
        if self.handler:
            await self.handler.stop_async()
        if self.http_client:
            await self.http_client.aclose()
        set_status("slack", "disabled")
        logger.info("Slack Bot 已停止")

    async def send(self, chat_id: str, content: str, **kwargs):
        """发送消息到 Slack 频道"""
        if self.app:
            thread_ts = kwargs.get("thread_ts")
            await self.app.client.chat_postMessage(
                channel=chat_id,
                text=content,
                thread_ts=thread_ts,
            )

    async def _download_image(self, url_private: str) -> tuple[bytes, str]:
        """下载 Slack 私有图片

        Args:
            url_private: Slack 私有图片 URL

        Returns:
            (图片字节数据, MIME类型)

        Raises:
            httpx.HTTPError: 下载失败
        """
        headers = {"Authorization": f"Bearer {self.bot_token}"}

        try:
            response = await self.http_client.get(url_private, headers=headers)
            response.raise_for_status()

            # 从响应头获取 MIME 类型
            content_type = response.headers.get("content-type", "image/jpeg")

            logger.debug(f"下载 Slack 图片成功: {url_private}, size={len(response.content)} bytes")
            return response.content, content_type

        except httpx.HTTPError as e:
            logger.error(f"下载 Slack 图片失败: {url_private}, error={e}")
            raise
