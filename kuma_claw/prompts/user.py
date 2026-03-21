"""
USER - 用户背景和偏好
======================

从配置文件加载用户的个人信息和偏好。
"""

from pathlib import Path

from ..config import config


def get_user_context() -> str:
    """获取用户背景上下文"""
    # 1. 尝试从配置文件加载
    user_file = Path.home() / ".kuma-claw" / "USER.md"
    if user_file.exists():
        return user_file.read_text(encoding="utf-8")

    # 2. 从配置构建
    user_config = config.config.get("user", {})
    if not user_config:
        return ""

    parts = ["## 用户背景 (User Context)"]

    # 基本信息
    if user_config.get("name"):
        parts.append(f"\n**用户：** {user_config['name']}")

    if user_config.get("timezone"):
        parts.append(f"**时区：** {user_config['timezone']}")

    if user_config.get("language"):
        parts.append(f"**语言：** {user_config['language']}")

    # 工作信息
    work = user_config.get("work", {})
    if work:
        parts.append("\n### 工作信息")
        if work.get("company"):
            parts.append(f"- 公司：{work['company']}")
        if work.get("role"):
            parts.append(f"- 职位：{work['role']}")
        if work.get("industry"):
            parts.append(f"- 行业：{work['industry']}")

    # 偏好
    preferences = user_config.get("preferences", {})
    if preferences:
        parts.append("\n### 偏好")
        if preferences.get("communication_style"):
            parts.append(f"- 沟通风格：{preferences['communication_style']}")
        if preferences.get("technical_level"):
            parts.append(f"- 技术水平：{preferences['technical_level']}")

    # 自定义提示
    custom = user_config.get("custom_prompt")
    if custom:
        parts.append(f"\n### 自定义提示\n{custom}")

    return "\n".join(parts) if len(parts) > 1 else ""


# ============================================
# 便捷函数
# ============================================


def set_user_info(
    name: str | None = None,
    timezone: str | None = None,
    language: str | None = None,
    company: str | None = None,
    role: str | None = None,
    industry: str | None = None,
    communication_style: str | None = None,
    technical_level: str | None = None,
    custom_prompt: str | None = None,
):
    """设置用户信息"""
    user_config = config.config.setdefault("user", {})

    if name:
        user_config["name"] = name
    if timezone:
        user_config["timezone"] = timezone
    if language:
        user_config["language"] = language

    if company or role or industry:
        work = user_config.setdefault("work", {})
        if company:
            work["company"] = company
        if role:
            work["role"] = role
        if industry:
            work["industry"] = industry

    if communication_style or technical_level:
        prefs = user_config.setdefault("preferences", {})
        if communication_style:
            prefs["communication_style"] = communication_style
        if technical_level:
            prefs["technical_level"] = technical_level

    if custom_prompt:
        user_config["custom_prompt"] = custom_prompt

    config.save()


def load_user_from_file(file_path: str):
    """从文件加载用户配置"""
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"User file not found: {file_path}")

    content = path.read_text(encoding="utf-8")

    # 保存到 ~/.kuma-claw/USER.md
    target = Path.home() / ".kuma-claw" / "USER.md"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
