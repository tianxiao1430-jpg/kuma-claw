"""
Kuma Claw Gateway - Web 适配器
============================

Web UI 和 WebSocket 通信。
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Set

import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse

from .. import ChannelType, Message
from .base import BaseAdapter

if TYPE_CHECKING:
    from ..gateway import Gateway


class WebAdapter(BaseAdapter):
    """Web 适配器"""

    channel = ChannelType.WEB

    def __init__(
        self,
        gateway: Gateway,
        host: str = "0.0.0.0",
        port: int = 8080,
    ):
        super().__init__(gateway)
        self.host = host
        self.port = port
        self.app = FastAPI(title="Kuma Claw Web UI")
        self.connections: Set[WebSocket] = set()

        self._setup_routes()

    def _setup_routes(self):
        """设置路由"""

        @self.app.get("/")
        async def index():
            return HTMLResponse(self._get_html())

        @self.app.websocket("/ws")
        async def websocket_endpoint(websocket: WebSocket):
            await self._handle_websocket(websocket)

    async def start(self):
        """启动 Web 服务器"""
        config = uvicorn.Config(
            self.app,
            host=self.host,
            port=self.port,
            log_level="warning",
        )
        self.server = uvicorn.Server(config)
        await self.server.serve()

    async def stop(self):
        """停止 Web 服务器"""
        if hasattr(self, "server"):
            self.server.should_exit = True

    async def send(self, chat_id: str, content: str, **kwargs):
        """发送消息到 WebSocket"""
        message = {
            "type": "reply",
            "chat_id": chat_id,
            "content": content,
        }

        for ws in self.connections:
            try:
                await ws.send_json(message)
            except Exception:
                self.connections.discard(ws)

    async def _handle_websocket(self, websocket: WebSocket):
        """处理 WebSocket 连接"""
        await websocket.accept()
        self.connections.add(websocket)

        try:
            while True:
                data = await websocket.receive_json()

                # 转换为统一消息格式
                message = Message(
                    id=str(uuid.uuid4()),
                    channel=ChannelType.WEB,
                    user_id=data.get("user_id", "anonymous"),
                    chat_id=data.get("chat_id", "default"),
                    content=data.get("content", ""),
                    metadata=data.get("metadata", {}),
                )

                # 处理消息
                reply = await self._handle_message(message)

                # 发送回复
                if reply:
                    await websocket.send_json({
                        "type": "reply",
                        "message_id": reply.message_id,
                        "content": reply.content,
                        "agent": reply.agent,
                    })

        except WebSocketDisconnect:
            self.connections.discard(websocket)

    def _get_html(self) -> str:
        """返回 Web UI HTML"""
        return """
<!DOCTYPE html>
<html>
<head>
    <title>Kuma Claw</title>
    <style>
        body { font-family: system-ui; max-width: 800px;
               margin: 0 auto; padding: 20px; }
        #chat { height: 400px; overflow-y: auto;
                border: 1px solid #ccc; padding: 10px;
                margin: 10px 0; }
        .msg { margin: 5px 0; }
        .user { color: #0066cc; }
        .bot { color: #009933; }
        #input { width: 70%; padding: 10px; }
        #send { padding: 10px 20px; }
    </style>
</head>
<body>
    <h1>🦞 Kuma Claw</h1>
    <div id="chat"></div>
    <input id="input" type="text" placeholder="输入消息...">
    <button id="send">发送</button>

    <script>
        const ws = new WebSocket(`ws://${location.host}/ws`);
        const chat = document.getElementById('chat');
        const input = document.getElementById('input');
        const send = document.getElementById('send');

        ws.onmessage = (e) => {
            const data = JSON.parse(e.data);
            if (data.type === 'reply') {
                addMessage('Bot', data.content, 'bot');
            }
        };

        send.onclick = () => {
            const content = input.value.trim();
            if (content) {
                ws.send(JSON.stringify({
                    content, user_id: 'user', chat_id: 'web'
                }));
                addMessage('You', content, 'user');
                input.value = '';
            }
        };

        input.onkeypress = (e) => {
            if (e.key === 'Enter') send.click();
        };

        function addMessage(who, text, cls) {
            chat.innerHTML += `<div class="msg ${cls}">
                <b>${who}:</b> ${text}</div>`;
            chat.scrollTop = chat.scrollHeight;
        }
    </script>
</body>
</html>
        """
