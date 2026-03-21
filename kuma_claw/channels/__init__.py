"""
Kuma Claw - 渠道模块
==================

统一的多渠道支持（Telegram, Slack, Discord, WhatsApp, Web）
"""

from .base import ChannelHandler, SessionManager, run_agent_with_session
from .formats import (
    CHANNEL_FORMATS,
    extract_internal_content,
    get_format_prompt,
    inject_format_prompt,
)

__all__ = [
    # 基础类
    "ChannelHandler",
    "SessionManager",
    "run_agent_with_session",
    # 格式工具
    "CHANNEL_FORMATS",
    "get_format_prompt",
    "inject_format_prompt",
    "extract_internal_content",
]
