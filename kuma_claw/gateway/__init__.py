"""
Kuma Claw Gateway - 网关核心
==========================

统一消息入口，支持多渠道、多 Agent 路由。
"""

import asyncio
import collections
import json
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

from google.adk.agents import LlmAgent

from .agent_runner import AgentRunner
from .formats import extract_internal_content
from .session_manager import SessionKey, UnifiedSessionManager

logger = logging.getLogger("kuma_claw.gateway")

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
    message_id: str  # 原消息 ID
    content: str
    agent: str  # 处理的 agent
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
# Gateway 核心
# ============================================


class Gateway:
    """网关核心"""

    def __init__(self, config_path: str | None = None, db_path: str | None = None):
        self.config = self._load_config(config_path)
        self.router = AgentRouter()
        self.session_manager = UnifiedSessionManager(db_path=db_path)
        self.agent_runner: AgentRunner | None = None
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
            "routing": [{"default": True, "agent": "default"}],
        }

    def set_agent(self, agent: LlmAgent):
        """Set the LLM agent and create the AgentRunner."""
        self.agent_runner = AgentRunner(agent=agent, session_manager=self.session_manager)
        logger.info("AgentRunner initialized")

    def register_adapter(self, channel: ChannelType, adapter: Any):
        """注册渠道适配器"""
        self.adapters[channel] = adapter

    def _check_rate_limit(self, user_id: str) -> bool:
        """检查用户是否超出速率限制。返回 True 表示通过。"""
        from ..config import config
        limit = config.rate_limit_per_minute
        if limit <= 0:
            return True
        if not hasattr(self, "_rate_limits"):
            self._rate_limits: dict[str, list[float]] = {}
        now = time.time()
        timestamps = self._rate_limits.setdefault(user_id, [])
        # 清理 60 秒前的记录
        self._rate_limits[user_id] = [t for t in timestamps if now - t < 60]
        if len(self._rate_limits[user_id]) >= limit:
            return False
        self._rate_limits[user_id].append(now)
        return True

    async def process_message(self, message: Message) -> Reply:
        """处理消息"""
        if not self.agent_runner:
            raise RuntimeError("AgentRunner not initialized. Call set_agent() first.")

        # 用户白名单检查 (#138)
        from ..config import config
        allowed_users = config.get_allowed_users()
        if allowed_users and message.user_id not in allowed_users:
            logger.warning(f"User {message.user_id} not in whitelist, rejecting")
            return Reply(
                id=f"reply-{message.id}",
                message_id=message.id,
                content="抱歉，您没有使用此 Bot 的权限。请联系管理员。",
                agent="default",
            )

        # 速率限制检查 (#166)
        if not self._check_rate_limit(message.user_id):
            logger.warning(f"User {message.user_id} rate limited")
            return Reply(
                id=f"reply-{message.id}",
                message_id=message.id,
                content="请求过于频繁，请稍后再试。",
                agent="default",
            )

        try:
            # 1. Build SessionKey from message
            scope = message.metadata.get("scope", message.chat_id)
            session_key = SessionKey(
                channel=message.channel.value,
                user_id=message.user_id,
                scope=scope,
            )

            # 2. Run via AgentRunner
            images = message.metadata.get("images")
            raw_response = await self.agent_runner.run(
                session_key=session_key,
                text=message.content,
                images=images,
            )

            # 3. Apply extract_internal_content
            internal, visible = extract_internal_content(raw_response)

            # 4. Route to get agent name (for metadata)
            agent_id = self.router.route(message)

            # 5. Return Reply
            metadata: dict[str, Any] = {}
            if internal:
                metadata["internal"] = internal

            return Reply(
                id=f"reply-{message.id}",
                message_id=message.id,
                content=visible,
                agent=agent_id,
                metadata=metadata,
            )
        except Exception as e:
            logger.error(f"Error processing message {message.id}: {e}")
            return Reply(
                id=f"reply-{message.id}",
                message_id=message.id,
                content="抱歉，处理消息时出现错误，请稍后重试。",
                agent="default",
                metadata={"error": str(e)},
            )

    async def start(self):
        """启动网关 - start all registered adapters concurrently."""
        if not self.adapters:
            logger.warning("No adapters registered, nothing to start")
            return

        tasks = []
        for channel, adapter in self.adapters.items():
            logger.info(f"Starting adapter: {channel.value}")
            tasks.append(asyncio.create_task(adapter.start()))

        results = await asyncio.gather(*tasks, return_exceptions=True)
        for (channel, _), result in zip(self.adapters.items(), results):
            if isinstance(result, Exception):
                logger.error(f"Adapter {channel.value} failed to start: {result}")
        logger.info("Gateway started with %d adapters", len(self.adapters))

    async def stop(self):
        """停止网关 - stop all adapters and close session manager."""
        for channel, adapter in self.adapters.items():
            logger.info(f"Stopping adapter: {channel.value}")
            try:
                await adapter.stop()
            except (RuntimeError, ValueError, OSError) as e:
                logger.error(f"Error stopping adapter {channel.value}: {e}")

        await self.session_manager.close()
        logger.info("Gateway stopped")


# ============================================
# 便捷函数
# ============================================


def create_gateway(config_path: str | None = None, db_path: str | None = None) -> Gateway:
    """创建网关实例"""
    return Gateway(config_path, db_path=db_path)
