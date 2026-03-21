"""
Web 渠道处理器
==================
"""

import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from .base import ChannelHandler
from .formats import extract_internal_content

logger = logging.getLogger("kuma_claw.channels.web")


class WebChannel(ChannelHandler):
    """Web UI 渠道处理器"""

    def __init__(self, agent, port: int = 8080):
        super().__init__("Web", agent)
        self.port = port
        self.app = FastAPI()
        self._setup_routes()

    async def handle_message(self, user_id: str, text: str, **kwargs) -> str:
        """处理消息"""
        return await self.run_agent(user_id, text)

    async def start(self):
        """启动 Web 服务器"""
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_methods=["*"],
            allow_headers=["*"],
        )

        # 注册路由
        @self.app.post("/chat")
        async def chat_endpoint(request: Request):
            """聊天端点"""
            data = await request.json()

            user_id = data.get("user_id", "anonymous")
            text = data.get("text", "")

            if not text:
                return {"error": "缺少 text 参数"}

            response = await self.handle_message(user_id, text)

            # 提取内部内容
            _, final_response = extract_internal_content(response)

            return {"response": final_response}

        @self.app.get("/health")
        async def health():
            """健康检查"""
            return {"status": "ok", "channel": "web"}

        logger.info(f"Web UI 已启动: http://localhost:{self.port}")

    async def stop(self):
        """停止 Web 服务器"""
        # TODO: 实现优雅关闭
        logger.info("Web UI 已停止")


def create_web_channel(agent, port: int = 8080) -> WebChannel:
    """创建 Web 渠道实例"""
    return WebChannel(agent, port)
