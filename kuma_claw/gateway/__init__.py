"""
Kuma Claw Gateway - 网关核心
==========================

统一消息入口，支持多渠道、多 Agent 路由。
"""

import json
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any


# ============================================
# 数据模型
# ============================================

class ChannelType(Enum):
    TELEGRAM = "telegram"
    SLACK = "slack"
    DISCORD = "discord"
    WEB = "web"
    WHATSAPP = "whatsapp"


@dataclass
class Message:
    """统一消息格式"""
    id: str
    channel: ChannelType
    user_id: str
    chat_id: str
    content: str
    timestamp: datetime = field(default_factory=datetime.now)
    reply_to: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "channel": self.channel.value,
            "user_id": self.user_id,
            "chat_id": self.chat_id,
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
            "reply_to": self.reply_to,
            "metadata": self.metadata,
        }


@dataclass
class Reply:
    """回复消息"""
    id: str
    message_id: str          # 原消息 ID
    content: str
    agent: str               # 处理的 agent
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "message_id": self.message_id,
            "content": self.content,
            "agent": self.agent,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
        }


@dataclass
class Session:
    """会话"""
    id: str
    user_id: str
    channel: ChannelType
    chat_id: str
    agent_id: str = "default"
    context: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    def touch(self):
        self.updated_at = datetime.now()


# ============================================
# 路由规则
# ============================================

@dataclass
class RoutingRule:
    """路由规则"""
    agent: str
    channel: str | None = None
    mention: str | None = None
    keyword: str | None = None
    user_id: str | None = None
    is_default: bool = False

    def matches(self, message: Message) -> bool:
        """检查是否匹配"""
        if self.is_default:
            return True

        if self.channel and message.channel.value != self.channel:
            return False

        if self.mention and self.mention not in message.metadata.get("mentions", []):
            return False

        if self.keyword and self.keyword not in message.content:
            return False

        if self.user_id and message.user_id != self.user_id:
            return False

        return True


class AgentRouter:
    """Agent 路由器"""

    def __init__(self):
        self.rules: list[RoutingRule] = []

    def add_rule(self, rule: RoutingRule):
        """添加路由规则"""
        self.rules.append(rule)

    def load_rules(self, config: list[dict]):
        """从配置加载规则"""
        for rule_config in config:
            rule = RoutingRule(
                agent=rule_config.get("agent", "default"),
                channel=rule_config.get("channel"),
                mention=rule_config.get("mention"),
                keyword=rule_config.get("keyword"),
                user_id=rule_config.get("user_id"),
                is_default=rule_config.get("default", False),
            )
            self.add_rule(rule)

    def route(self, message: Message) -> str:
        """路由消息到对应的 Agent"""
        for rule in self.rules:
            if rule.matches(message):
                return rule.agent

        # 默认返回 default agent
        return "default"


# ============================================
# 会话管理器
# ============================================

class SessionManager:
    """会话管理器"""

    def __init__(self):
        self.sessions: dict[str, Session] = {}

    def _session_key(self, channel: ChannelType, chat_id: str) -> str:
        return f"{channel.value}:{chat_id}"

    def get_or_create(
        self,
        channel: ChannelType,
        chat_id: str,
        user_id: str,
    ) -> Session:
        """获取或创建会话"""
        key = self._session_key(channel, chat_id)

        if key not in self.sessions:
            self.sessions[key] = Session(
                id=key,
                user_id=user_id,
                channel=channel,
                chat_id=chat_id,
            )

        session = self.sessions[key]
        session.touch()
        return session

    def get(self, channel: ChannelType, chat_id: str) -> Session | None:
        """获取会话"""
        key = self._session_key(channel, chat_id)
        return self.sessions.get(key)

    def set_agent(self, channel: ChannelType, chat_id: str, agent_id: str):
        """设置会话绑定的 Agent"""
        session = self.get(channel, chat_id)
        if session:
            session.agent_id = agent_id
            session.touch()


# ============================================
# Gateway 核心
# ============================================

class Gateway:
    """网关核心"""

    def __init__(self, config_path: str | None = None):
        self.config = self._load_config(config_path)
        self.router = AgentRouter()
        self.session_manager = SessionManager()
        self.agents: dict[str, Any] = {}  # agent_id -> Agent 实例
        self.adapters: dict[ChannelType, Any] = {}  # channel -> Adapter 实例

        # 加载路由规则
        if "routing" in self.config:
            self.router.load_rules(self.config["routing"])

    def _load_config(self, config_path: str | None) -> dict:
        """加载配置"""
        if config_path:
            path = Path(config_path)
        else:
            path = Path.home() / ".kuma-claw" / "gateway.json"

        if path.exists():
            with path.open("r") as f:
                return json.load(f)

        return {
            "gateway": {
                "host": "0.0.0.0",
                "port": 19001,
            },
            "routing": [
                {"default": True, "agent": "default"}
            ]
        }

    def register_agent(self, agent_id: str, agent: Any):
        """注册 Agent"""
        self.agents[agent_id] = agent

    def register_adapter(self, channel: ChannelType, adapter: Any):
        """注册渠道适配器"""
        self.adapters[channel] = adapter

    async def process_message(self, message: Message) -> Reply:
        """处理消息"""
        # 1. 获取/创建会话
        session = self.session_manager.get_or_create(
            message.channel,
            message.chat_id,
            message.user_id,
        )

        # 2. 路由到对应的 Agent
        agent_id = self.router.route(message)

        # 3. 如果会话已绑定特定 Agent，优先使用
        if session.agent_id != "default":
            agent_id = session.agent_id

        # 4. 获取 Agent 实例
        agent = self.agents.get(agent_id)
        if not agent:
            raise ValueError(f"Agent not found: {agent_id}")

        # 5. 调用 Agent 处理
        response = await agent.process(message, session)

        # 6. 返回回复
        return Reply(
            id=f"reply-{message.id}",
            message_id=message.id,
            content=response,
            agent=agent_id,
        )

    async def start(self):
        """启动网关"""
        # TODO: 启动 WebSocket 服务器
        # TODO: 启动所有已配置的适配器
        pass

    async def stop(self):
        """停止网关"""
        # TODO: 停止所有适配器
        # TODO: 停止 WebSocket 服务器
        pass


# ============================================
# 便捷函数
# ============================================

def create_gateway(config_path: str | None = None) -> Gateway:
    """创建网关实例"""
    return Gateway(config_path)
