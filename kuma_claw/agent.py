"""
Kuma Claw - Agent 定义
====================
基于 Google ADK 的 AI Agent，支持按需加载技能工具
"""

import logging
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool

logger = logging.getLogger("kuma_claw")

# ============================================
# 懒加载缓存（带 TTL 失效机制）
# ============================================

_model_cache: Any | None = None
_model_cache_time: float = 0
_google_workspace_toolsets_cache: list | None = None
_google_workspace_cache_time: float = 0
_agent_cache: LlmAgent | None = None
_agent_cache_time: float = 0

# 缓存 TTL（秒）
CACHE_TTL = 300  # 5 分钟


def reset_cache():
    """重置所有缓存"""
    global _agent_cache, _google_workspace_toolsets_cache, _model_cache
    global _agent_cache_time, _google_workspace_cache_time, _model_cache_time
    _model_cache = None
    _model_cache_time = 0
    _agent_cache = None
    _agent_cache_time = 0
    _google_workspace_toolsets_cache = None
    _google_workspace_cache_time = 0


def _is_cache_valid(cache_time: float) -> bool:
    """检查缓存是否有效"""
    if cache_time == 0:
        return False
    return (time.time() - cache_time) < CACHE_TTL


def get_model():
    """获取模型配置（懒加载 + TTL 缓存）"""
    global _model_cache, _model_cache_time

    if _model_cache is not None and _is_cache_valid(_model_cache_time):
        return _model_cache

    try:
        from .config import config

        model = config.get_model()
    except (ImportError, AttributeError):
        model = os.environ.get("KUMA_MODEL", "gemini-3.1-flash")

    if isinstance(model, str) and model.startswith(("openai/", "anthropic/", "deepseek/")):
        from google.adk.models.lite_llm import LiteLlm

        _model_cache = LiteLlm(model=model)
    else:
        _model_cache = model

    _model_cache_time = time.time()
    return _model_cache


# ============================================
# 基础工具
# ============================================


def get_current_time() -> str:
    """获取当前时间"""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def echo_message(message: str) -> str:
    """回显消息（测试用）"""
    return f"收到：{message}"


# ============================================
# 记忆工具
# ============================================


def remember(content: str, source: str = "fact") -> str:
    """记住重要信息"""
    from .memory import memory_manager

    memory_manager.remember(content, source=source)
    return f"✅ 已记住：{content}"


def recall(query: str, limit: int = 5) -> str:
    """回忆相关信息"""
    from .memory import memory_manager

    results = memory_manager.search(query, limit=limit)
    if not results:
        return "没有找到相关记忆"
    return "📚 相关记忆：\n" + "\n".join(f"- {r.entry.content}" for r in results)


def forget(content_pattern: str) -> str:
    """忘记特定记忆"""
    from .memory import memory_manager

    results = memory_manager.search(content_pattern, limit=1)
    if not results:
        return "没有找到匹配的记忆"
    entry = results[0].entry
    memory_manager.forget(entry.id)

    return f"✅ 已忘记：{entry.content}"


def get_memory_stats() -> str:
    """获取记忆统计"""
    from .memory import memory_manager

    stats = memory_manager.stats()
    lines = [f"📊 记忆统计：\n- 总条目：{stats.total_entries}"]
    lines.extend(f"- {k}: {v}" for k, v in stats.by_source.items())
    if stats.last_sync:
        lines.append(f"- 最后同步：{stats.last_sync}")
    return "\n".join(lines)


# ============================================
# 网络搜索工具
# ============================================


def web_search(query: str, limit: int = 5) -> str:
    """通过 DuckDuckGo 搜索网络"""
    try:
        from duckduckgo_search import DDGS

        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=limit))

        if not results:
            return f"没有找到关于 '{query}' 的搜索结果。"

        return "\n\n".join(
            f"标题：{r.get('title')}\n内容：{r.get('body')}\n链接：{r.get('href')}" for r in results
        )
    except ImportError:
        return "❌ 搜索功能不可用：pip install duckduckgo-search"
    except Exception as e:
        logger.error(f"搜索失败：{e}")
        return f"搜索失败：{e}"


# ============================================
# Google Workspace 工具
# ============================================


def _load_google_workspace_toolsets():
    """加载 Google Workspace 工具集（懒加载 + TTL 缓存）"""
    global _google_workspace_toolsets_cache, _google_workspace_cache_time

    if (
        _google_workspace_toolsets_cache is not None
        and _is_cache_valid(_google_workspace_cache_time)
    ):
        return _google_workspace_toolsets_cache

    try:
        from .tools.adk_google_workspace import create_all_google_workspace_toolsets

        _google_workspace_toolsets_cache = create_all_google_workspace_toolsets()
        logger.info(f"已加载 {len(_google_workspace_toolsets_cache)} 个 Google Workspace 工具集")
    except ImportError:
        logger.warning("Google Workspace 工具集不可用")
        _google_workspace_toolsets_cache = []
    except Exception as e:
        logger.error(f"加载 Google Workspace 工具集失败：{e}")
        _google_workspace_toolsets_cache = []

    _google_workspace_cache_time = time.time()
    return _google_workspace_toolsets_cache


# ============================================
# Skills 工具 - 按需加载（基于触发词）
# ============================================


def _load_and_register_skills(tools_list: list, message_text: str | None = None) -> int:
    """加载 Skills 并注册工具（支持按需加载）

    Args:
        tools_list: 工具列表
        message_text: 用户消息文本（用于触发词匹配）

    Returns:
        加载的工具数量
    """
    try:
        from .skills.skill_manager import skill_manager

        logger.info("从 kuma_claw.skills 加载 skill_manager")

        # 检查是否有匹配的技能
        if message_text:
            matched_skill = skill_manager.get_skill_by_trigger(message_text)
            if matched_skill:
                # 按需加载：只注册匹配的工具
                count = 0
                for tool in matched_skill.tools:
                    if tool not in tools_list:
                        tools_list.append(tool)
                        count += 1
                logger.info(f"按需加载技能: {matched_skill.name} ({count} 个新工具)")
                return count

        # 回退：加载所有技能
        skill_manager.register_tools_to_agent(type("Agent", (), {"tools": tools_list})())
        return len(tools_list)

    except Exception as e:
        logger.error(f"加载 Skills 失败：{e}")
        return 0


# ============================================
# 工具列表
# ============================================


def get_tools(message_text: str | None = None) -> list[FunctionTool]:
    """获取工具列表（支持按需加载）

    Args:
        message_text: 用户消息文本（用于 Skill 触发词匹配）
    """
    tools = [
        FunctionTool(func=web_search),
        FunctionTool(func=get_current_time),
        FunctionTool(func=echo_message),
        FunctionTool(func=remember),
        FunctionTool(func=recall),
        FunctionTool(func=forget),
        FunctionTool(func=get_memory_stats),
    ]

    # 加载 Google Workspace 工具集
    gw_toolsets = _load_google_workspace_toolsets()
    for toolset in gw_toolsets:
        if hasattr(toolset, "tools"):
            tools.extend(toolset.tools)

    # 按需加载技能（基于消息内容）
    _load_and_register_skills(tools, message_text)

    return tools


# ============================================
# Agent 定义
# ============================================


def get_system_instruction(channel: str = "telegram") -> str:
    """构建系统提示词"""
    from .channels.formats import inject_format_prompt
    from .prompts import build_system_prompt

    base_prompt = build_system_prompt()
    internal_prompt = """

## 内部思考 (Internal Thoughts)

使用 `<internal>` 标签包裹内部推理（不发送给用户）：
```
<internal>
分析步骤、决策逻辑...
</internal>

给用户的实际回复...
```
"""
    time_prompt = f"\\n\\n## 系统信息\\n当前时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\\n"

    return inject_format_prompt(base_prompt + time_prompt + internal_prompt, channel)


def create_agent(channel: str = "telegram") -> LlmAgent:
    """创建 Agent 实例"""
    return LlmAgent(
        name="kuma_claw",
        model=get_model(),
        instruction=get_system_instruction(channel),
        description="Kuma Claw - 智能办公助手",
        tools=get_tools(),
    )


def get_agent(channel: str = "telegram", force_refresh: bool = False) -> LlmAgent:
    """获取 Agent 实例（单例 + TTL 缓存）

    Args:
        channel: 渠道名称
        force_refresh: 是否强制刷新缓存
    """
    global _agent_cache, _agent_cache_time

    if _agent_cache is None or not _is_cache_valid(_agent_cache_time) or force_refresh:
        _agent_cache = create_agent(channel)
        _agent_cache_time = time.time()
        logger.debug("Agent 缓存已过期或不存在，重新创建")
    return _agent_cache


def __getattr__(name):
    """懒加载模块属性"""
    if name in ("kuma_claw_agent", "root_agent"):
        return get_agent("telegram")
    if name == "TOOLS":
        return get_tools()
    if name == "MODEL":
        return get_model()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


if __name__ == "__main__":
    print(f"Kuma Claw Agent 已定义\n总工具数量：{len(get_tools())}")
