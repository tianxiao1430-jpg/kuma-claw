"""
Kuma Claw - 智能 Agent 平台
==========================
"""

__version__ = "0.1.1"


def __getattr__(name):
    if name == "config":
        from .config import config

        return config
    if name in ("create_agent", "get_system_instruction"):
        from .agent import create_agent, get_system_instruction

        return locals()[name]
    if name in ("kuma_claw_agent", "root_agent"):
        from .agent import get_agent

        return get_agent()
    if name in (
        "get_format_prompt",
        "inject_format_prompt",
        "extract_internal_content",
        "strip_internal_tags",
        "convert_markdown_to_channel",
        "get_supported_channels",
    ):
        from .gateway.formats import (
            convert_markdown_to_channel,
            extract_internal_content,
            get_format_prompt,
            get_supported_channels,
            inject_format_prompt,
            strip_internal_tags,
        )

        return locals()[name]
    if name == "build_system_prompt":
        from .prompts import build_system_prompt

        return build_system_prompt
    if name == "Gateway":
        from .gateway import Gateway

        return Gateway
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "__version__",
    "Gateway",
    "build_system_prompt",
    "config",
    "convert_markdown_to_channel",
    "create_agent",
    "extract_internal_content",
    "get_format_prompt",
    "get_supported_channels",
    "get_system_instruction",
    "inject_format_prompt",
    "kuma_claw_agent",
    "root_agent",
    "strip_internal_tags",
]
