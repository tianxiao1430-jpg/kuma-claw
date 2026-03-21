"""
Kuma Claw - 智能 Agent 平台
==========================

基于 Google ADK 的开源 AI Agent 平台。
"""

__version__ = "0.1.0"

from .agent import create_agent, get_system_instruction, kuma_claw_agent, root_agent
from .channels.formats import (
    convert_markdown_to_channel,
    extract_internal_content,
    get_format_prompt,
    get_supported_channels,
    inject_format_prompt,
    strip_internal_tags,
)
from .config import config
from .prompts import build_system_prompt

__all__ = [
    # Agent
    "kuma_claw_agent",
    "root_agent",
    "create_agent",
    "get_system_instruction",
    # Config
    "config",
    # Prompts
    "build_system_prompt",
    # Formats
    "get_format_prompt",
    "inject_format_prompt",
    "extract_internal_content",
    "strip_internal_tags",
    "convert_markdown_to_channel",
    "get_supported_channels",
    # Version
    "__version__",
]
