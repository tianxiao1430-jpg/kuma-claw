"""
Slack 渠道处理器
==================
"""

import logging
import re

import httpx
from slack_bolt.adapter.socket_mode.async_handler import AsyncSocketModeHandler
from slack_bolt.async_app import AsyncApp

from ..service_registry import set_status
from .base import ChannelHandler
from .formats import extract_internal_content

logger = logging.getLogger("kuma_claw.channels.slack")


class SlackChannel(ChannelHandler):
    """Slack 渠道处理器"""

    def __init__(self, agent, bot_token: str, app_token: str):
        super().__init__("Slack", agent)
        self.bot_token = bot_token
        self.app_token = app_token
        self.app = None
        self.handler = None
        self.http_client = httpx.AsyncClient(timeout=30.0)

    async def download_slack_image(self, url_private: str) -> tuple[bytes, str]:
        """下载 Slack 图片

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

    async def handle_message(self, user_id: str, text: str, **kwargs) -> str:
        """处理消息"""
        return await self.run_agent(user_id, text)

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

            # 提取文本
            text = event.get("text", "")

            # 移除 bot mention
            text = re.sub(r"<@[^>]+>", "", text).strip()

            # 构造 session_key（按线程隔离）
            # 格式："{user_id}:{channel}:{thread_ts}"
            session_key = f"{user_id}:{channel}:{thread_ts}"

            logger.debug(
                f"Slack 消息: user={user_id}, channel={channel}, thread={thread_ts}, "
                f"session_key={session_key}"
            )

            # 提取图片（如果有）
            files = event.get("files", [])
            images: list[tuple[bytes, str]] = []

            if files:
                logger.info(f"检测到 {len(files)} 个文件附件")

                for f in files:
                    url_private = f.get("url_private")
                    if url_private:
                        try:
                            img_bytes, mime_type = await self.download_slack_image(url_private)
                            images.append((img_bytes, mime_type))
                            logger.debug(f"成功下载图片: {mime_type}")
                        except Exception as e:
                            logger.error(f"下载图片失败: {e}")
                            # 发送错误提示
                            await client.chat_postMessage(
                                channel=channel,
                                text=f"⚠️ 无法下载图片: {str(e)}",
                                thread_ts=thread_ts,
                            )

            # 处理消息（传入 session_key）
            try:
                response = await self.run_agent(
                    user_id=user_id,
                    text=text,
                    images=images if images else None,
                    session_key=session_key,  # ← 关键：按线程隔离
                )

                # 提取内部内容
                _, final_response = extract_internal_content(response)

                # 发送响应
                await client.chat_postMessage(
                    channel=channel, text=final_response, thread_ts=thread_ts
                )

            except Exception as e:
                logger.error(f"处理消息失败: {e}")
                await client.chat_postMessage(
                    channel=channel, text=f"❌ 处理请求时出错: {str(e)}", thread_ts=thread_ts
                )

        self.handler = AsyncSocketModeHandler(self.app, self.app_token)
        set_status("slack", "starting")
        try:
            await self.handler.start_async()
            set_status("slack", "connected")
            logger.info("Slack Bot 已启动")
        except Exception as e:
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
