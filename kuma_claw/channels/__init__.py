"""
Kuma Claw - 渠道模块 (已迁移至 Gateway 架构)
==========================================

所有渠道功能已迁移到 kuma_claw.gateway 模块。
此文件保留为向后兼容层。
"""

# Re-export from gateway for backward compatibility
from ..gateway.formats import (
    CHANNEL_FORMATS,
    extract_internal_content,
    get_format_prompt,
    inject_format_prompt,
)

__all__ = [
    "CHANNEL_FORMATS",
    "get_format_prompt",
    "inject_format_prompt",
    "extract_internal_content",
]
