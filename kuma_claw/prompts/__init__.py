"""
Kuma Claw - 系统提示词模块
=========================

参考 OpenClaw 的三层设计：
- SOUL: 核心价值观和行为准则
- IDENTITY: 可自定义的人设
- USER: 用户背景和偏好
"""

from .identity import get_identity_prompt, load_identity_from_file, set_identity, set_name
from .soul import get_soul_prompt
from .user import get_user_context, load_user_from_file, set_user_info


def build_system_prompt() -> str:
    """构建完整的系统提示词"""
    parts = []

    # 1. Soul - 核心价值观（固定）
    parts.append(get_soul_prompt())

    # 2. Identity - 人设（可自定义）
    identity = get_identity_prompt()
    if identity:
        parts.append(identity)

    # 3. User - 用户背景
    user_ctx = get_user_context()
    if user_ctx:
        parts.append(user_ctx)

    return "\n\n---\n\n".join(parts)


__all__ = [
    "build_system_prompt",
    "get_soul_prompt",
    "get_identity_prompt",
    "get_user_context",
    "set_identity",
    "set_name",
    "load_identity_from_file",
    "set_user_info",
    "load_user_from_file",
]
