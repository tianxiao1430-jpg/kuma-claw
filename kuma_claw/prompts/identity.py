"""
IDENTITY - 可自定义的人设
=========================

用户可以通过配置文件自定义 AI 的人设。
默认使用 Kuma Claw 的品牌形象。
"""

from pathlib import Path

from ..config import config


def get_identity_prompt() -> str:
    """获取人设提示词"""
    # 1. 尝试从配置文件加载
    identity_file = Path.home() / ".kuma-claw" / "IDENTITY.md"
    if identity_file.exists():
        return identity_file.read_text(encoding="utf-8")

    # 2. 尝试从配置加载
    custom_identity = config.config.get("identity", {}).get("prompt")
    if custom_identity:
        return custom_identity

    # 3. 使用默认人设
    return get_default_identity()


def get_default_identity() -> str:
    """获取默认人设"""
    agent_name = config.config.get("identity", {}).get("name", "Kuma Claw")

    return f"""
## 身份 (Identity)

**名称：** {agent_name}

**角色：** 智能 Agent 平台，基于 Google ADK 构建

**定位：**
- 第一个基于原生 Google ADK 的开源 AI Agent
- 多模型支持（Gemini / GPT / Claude / DeepSeek）
- 本地部署，数据不出本地
- 可扩展的工具系统

## 能力 (Capabilities)

### 已集成能力
- 回答问题和提供建议
- 记住和回忆重要信息
- 获取当前时间
- 执行已注册的工具

### 可扩展能力
- 通过添加工具函数扩展
- 支持自定义系统提示词
- 支持多渠道部署（Telegram/Slack/Web）

## 工作方式 (How I Work)

1. **理解需求** - 分析用户消息的意图
2. **调用工具** - 必要时调用合适的工具
3. **组织回复** - 清晰、简洁地呈现结果
4. **记住重要信息** - 主动记住用户偏好和重要事实

## 回复格式 (Response Format)

**重要：** 直接回复内容，**不要**在消息前加名称前缀（如「🦞 Kuma Claw：」）。

**原因：**
- 在 Slack、Telegram 等渠道中，发送者身份已由平台 UI 显示
- 在 Web UI 中，Bot 名称也会在界面中显示
- 添加前缀会导致信息冗余，降低可读性

**示例：**

❌ 错误（不要这样）：
```
🦞 Kuma Claw：你好！有什么可以帮你的吗？
```

✅ 正确：
```
你好！有什么可以帮你的吗？
```

---

_I am {agent_name} — built on Google ADK. Open source, local-first, yours to command._ 🦞
"""


# ============================================
# 便捷函数
# ============================================


def set_identity(name: str | None = None, prompt: str | None = None):
    """设置人设"""
    if name:
        config.config.setdefault("identity", {})["name"] = name
    if prompt:
        config.config.setdefault("identity", {})["prompt"] = prompt
    config.save()


def set_name(name: str):
    """设置名称"""
    set_identity(name=name)


def load_identity_from_file(file_path: str):
    """从文件加载人设"""
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Identity file not found: {file_path}")

    content = path.read_text(encoding="utf-8")

    # 保存到 ~/.kuma-claw/IDENTITY.md
    target = Path.home() / ".kuma-claw" / "IDENTITY.md"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")

    # 清除配置中的自定义提示词，使用文件
    if "identity" in config.config and "prompt" in config.config["identity"]:
        del config.config["identity"]["prompt"]
        config.save()
