"""
Kuma Claw - Agent 定义
====================
基于 Google ADK 的 AI Agent
支持统一资源检索 (Everything is Context) 与 TTL 缓存
"""

import logging
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool

# 配置日志
logger = logging.getLogger("kuma_claw")

# ============================================
# 懒加载缓存（带 TTL 失效机制）
# ============================================

_model_cache: Any | None = None
_model_cache_time: float = 0
_google_workspace_toolsets_cache: list | None = None
_google_workspace_cache_time: float = 0
_skill_manager_cache: Any | None = None
_agent_cache: LlmAgent | None = None
_agent_cache_time: float = 0

# 缓存 TTL（秒）
CACHE_TTL = 300  # 5 分钟


def reset_cache():
    """重置所有缓存"""
    global _agent_cache, _google_workspace_toolsets_cache, _model_cache, _skill_manager_cache
    global _agent_cache_time, _google_workspace_cache_time, _model_cache_time
    _model_cache = None
    _model_cache_time = 0
    _agent_cache = None
    _agent_cache_time = 0
    _google_workspace_toolsets_cache = None
    _google_workspace_cache_time = 0
    _skill_manager_cache = None


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
# 基础工具 (Permanent Tools)
# ============================================


def get_current_time() -> str:
    """获取当前日期和时间"""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def echo_message(message: str) -> str:
    """回显消息（测试用）"""
    return f"收到：{message}"


def remember(content: str, source: str = "fact") -> str:
    """记住重要信息、事实或用户偏好"""
    from .memory import memory_manager
    memory_manager.remember(content, source=source)
    return f"✅ 已记住：{content}"


def recall(query: str, limit: int = 5) -> str:
    """回忆之前记住的相关信息或会话历史"""
    from .memory import memory_manager
    results = memory_manager.search(query, limit=limit)
    if not results:
        return "没有找到相关记忆"
    lines = ["📚 相关记忆："]
    for r in results:
        lines.append(f"- {r.entry.content}")
    return "\n".join(lines)


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
    """通过 DuckDuckGo 搜索网络获取实时信息"""
    try:
        from duckduckgo_search import DDGS
        with DDGS() as ddgs:
            results_raw = ddgs.text(query, max_results=limit)
        results = [
            f"标题：{r.get('title')}\n内容：{r.get('body')}\n链接：{r.get('href')}"
            for r in results_raw
        ]
        return "\n\n".join(results) if results else f"没有找到关于 '{query}' 的结果。"
    except Exception as e:
        logger.error(f"搜索失败：{e}")
        return f"搜索失败：{str(e)}"


# ============================================
# Google Workspace 工具
# ============================================


def _load_google_workspace_toolsets():
    """加载 Google Workspace 工具集（懒加载 + TTL 缓存）"""
    global _google_workspace_toolsets_cache, _google_workspace_cache_time

    if _google_workspace_toolsets_cache is not None and _is_cache_valid(
        _google_workspace_cache_time
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
# 技能管理与动态注入 (The "Everything is Context" Logic)
# ============================================


def _get_skill_manager():
    """获取 SkillManager 实例"""
    global _skill_manager_cache
    if _skill_manager_cache is not None:
        return _skill_manager_cache

    try:
        from .skills.skill_manager import skill_manager
        _skill_manager_cache = skill_manager
        logger.debug(f"SkillManager 加载完成，技能数量: {len(_skill_manager_cache.skills)}")
    except Exception as e:
        logger.error(f"无法加载 SkillManager: {e}")
        return None
    return _skill_manager_cache


def get_core_tools() -> list:
    """获取核心基础工具"""
    return [
        FunctionTool(func=web_search),
        FunctionTool(func=get_current_time),
        FunctionTool(func=remember),
        FunctionTool(func=recall),
        FunctionTool(func=forget),
        FunctionTool(func=get_memory_stats),
        FunctionTool(func=echo_message),
    ]


def get_tools(message_text: str | None = None) -> list:
    """根据输入动态检索并返回相关的工具/技能 (Everything is Context)"""
    from .memory import memory_manager

    tools = get_core_tools()

    # 加载 Google Workspace 工具集
    gw_toolsets = _load_google_workspace_toolsets()
    for toolset in gw_toolsets:
        if hasattr(toolset, "tools"):
            tools.extend(toolset.tools)

    if not message_text:
        return tools

    # 1. 在记忆库中检索相关的 Skill/Tool 注册信息
    search_results = memory_manager.search(message_text, limit=5)

    sm = _get_skill_manager()
    if not sm:
        logger.warning("SkillManager 未加载，无法动态注入技能")
        return tools

    matched_skills = set()
    for r in search_results:
        metadata = r.entry.metadata
        logger.debug(f"检查搜索结果: {r.entry.content[:50]}... Metadata: {metadata}")
        if metadata.get("type") == "skill":
            skill_name = metadata.get("skill_name")
            matched_skills.add(skill_name)

    # 2. 从 SkillManager 加载匹配的技能工具
    for skill_name in matched_skills:
        skill = sm.skills.get(skill_name)
        if skill:
            logger.info(f"动态注入技能: {skill_name}")
            for t in skill.tools:
                if t not in tools:
                    tools.append(t)
        else:
            logger.warning(f"技能已索引但加载失败: {skill_name}")

    # 3. 如果通过记忆搜索没搜到，尝试触发词兜底
    if not matched_skills:
        skill = sm.get_skill_by_trigger(message_text)
        if skill:
            logger.info(f"根据触发词注入技能: {skill.name}")
            for t in skill.tools:
                if t not in tools:
                    tools.append(t)

    return tools


# ============================================
# Agent 工厂
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
    time_prompt = (
        f"\n\n## 系统信息\n当前时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
    )

    return inject_format_prompt(base_prompt + time_prompt + internal_prompt, channel)


def create_agent(query: str = "", channel: str = "telegram") -> LlmAgent:
    """创建 Agent 实例（支持动态工具注入）"""
    # 根据 query 动态选择工具
    tools = get_tools(query)

    return LlmAgent(
        name="kuma_claw",
        model=get_model(),
        instruction=get_system_instruction(channel),
        description="Kuma Claw - 智能办公助手",
        tools=tools,
    )


def get_agent(channel: str = "telegram", force_refresh: bool = False) -> LlmAgent:
    """获取 Agent 实例（单例 + TTL 缓存）

    Args:
        channel: 渠道名称
        force_refresh: 是否强制刷新缓存
    """
    global _agent_cache, _agent_cache_time

    if _agent_cache is None or not _is_cache_valid(_agent_cache_time) or force_refresh:
        _agent_cache = create_agent(channel=channel)
        _agent_cache_time = time.time()
        logger.debug("Agent 缓存已过期或不存在，重新创建")
    return _agent_cache


# ============================================
# 导出
# ============================================


def __getattr__(name):
    """懒加载模块属性"""
    if name in ("kuma_claw_agent", "root_agent"):
        return get_agent("telegram")
    if name == "TOOLS":
        return get_core_tools()
    if name == "MODEL":
        return get_model()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


if __name__ == "__main__":
    print(f"Kuma Claw Agent 已定义\n总工具数量：{len(get_tools())}")
