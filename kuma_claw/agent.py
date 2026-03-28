"""
Kuma Claw - Agent 定义
====================
基于 Google ADK 的 AI Agent
支持统一资源检索 (Everything is Context) 与 TTL 缓存
"""

import logging
import os
import threading
import time
from datetime import datetime
from typing import Any, Optional

from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool

# 配置日志
logger = logging.getLogger("kuma_claw")

# ============================================
# 缓存管理器（Issue #106：将全局变量重构为单例类）
# ============================================

# 缓存 TTL（秒）
CACHE_TTL = 300  # 5 分钟


class AgentCache:
    """单例缓存管理器

    将原来分散的 6 个全局变量封装为单一类，
    提高可测试性和并发安全性。
    """

    _instance: Optional["AgentCache"] = None
    _lock: threading.Lock = threading.Lock()

    def __new__(cls) -> "AgentCache":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._init()
        return cls._instance

    def _init(self):
        self.model_cache: Any | None = None
        self.model_cache_time: float = 0
        self.google_workspace_toolsets_cache: list | None = None
        self.google_workspace_cache_time: float = 0
        self.skill_manager_cache: Any | None = None
        self.agent_cache: LlmAgent | None = None
        self.agent_cache_time: float = 0

    def reset(self):
        """重置所有缓存"""
        self._init()

    def is_valid(self, cache_time: float) -> bool:
        """检查缓存是否有效"""
        if cache_time == 0:
            return False
        return (time.time() - cache_time) < CACHE_TTL


# 全局缓存实例
_cache = AgentCache()


def reset_cache():
    """重置所有缓存（向后兼容）"""
    _cache.reset()


def _is_cache_valid(cache_time: float) -> bool:
    """检查缓存是否有效（向后兼容）"""
    return _cache.is_valid(cache_time)


def get_model():
    """获取模型配置（懒加载 + TTL 缓存）"""
    if _cache.model_cache is not None and _cache.is_valid(_cache.model_cache_time):
        return _cache.model_cache

    try:
        from .config import config

        model = config.get_model()
    except (ImportError, AttributeError):
        model = os.environ.get("KUMA_MODEL", "gemini-3.1-flash")

    if isinstance(model, str) and model.startswith(("openai/", "anthropic/", "deepseek/")):
        from google.adk.models.lite_llm import LiteLlm

        _cache.model_cache = LiteLlm(model=model)
    else:
        _cache.model_cache = model

    _cache.model_cache_time = time.time()
    return _cache.model_cache


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

        with DDGS(timeout=20) as ddgs:
            results_raw = ddgs.text(query, max_results=limit)
        results = [
            f"标题：{r.get('title')}\n内容：{r.get('body')}\n链接：{r.get('href')}"
            for r in results_raw
        ]
        return "\n\n".join(results) if results else f"没有找到关于 '{query}' 的结果。"
    except (ImportError, OSError, ValueError, RuntimeError) as e:
        logger.error(f"搜索失败：{e}")
        return f"搜索失败：{str(e)}"


# ============================================
# Google Workspace 工具
# ============================================


def _load_google_workspace_toolsets():
    """加载 Google Workspace 工具集（懒加载 + TTL 缓存）"""
    if _cache.google_workspace_toolsets_cache is not None and _cache.is_valid(
        _cache.google_workspace_cache_time
    ):
        return _cache.google_workspace_toolsets_cache

    try:
        from .tools.adk_google_workspace import create_all_google_workspace_toolsets

        _cache.google_workspace_toolsets_cache = create_all_google_workspace_toolsets()
        logger.info(
            f"已加载 {len(_cache.google_workspace_toolsets_cache)} 个 Google Workspace 工具集"
        )
    except ImportError:
        logger.warning("Google Workspace 工具集不可用")
        _cache.google_workspace_toolsets_cache = []
    except (AttributeError, RuntimeError, ValueError) as e:
        logger.error(f"加载 Google Workspace 工具集失败：{e}")
        _cache.google_workspace_toolsets_cache = []

    _cache.google_workspace_cache_time = time.time()
    return _cache.google_workspace_toolsets_cache


# ============================================
# 技能管理与动态注入 (The "Everything is Context" Logic)
# ============================================


def _get_skill_manager():
    """获取 SkillManager 实例"""
    if _cache.skill_manager_cache is not None:
        return _cache.skill_manager_cache

    try:
        from .skills.skill_manager import skill_manager

        _cache.skill_manager_cache = skill_manager
        logger.debug(f"SkillManager 加载完成，技能数量: {len(_cache.skill_manager_cache.skills)}")
    except (ImportError, AttributeError, RuntimeError) as e:
        logger.error(f"无法加载 SkillManager: {e}")
        return None
    return _cache.skill_manager_cache


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


def get_system_instruction() -> str:
    """构建系统提示词

    注意：时间信息使用占位符，由 get_current_time 工具在运行时提供准确时间，
    避免缓存的 agent 使用过期时间（#165）。
    """
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
    time_prompt = "\n\n## 系统信息\n如需当前时间，请调用 get_current_time 工具获取准确时间。\n"

    return base_prompt + time_prompt + internal_prompt


def create_agent(query: str = "") -> LlmAgent:
    """创建 Agent 实例（支持动态工具注入）"""
    # 根据 query 动态选择工具
    tools = get_tools(query)

    return LlmAgent(
        name="kuma_claw",
        model=get_model(),
        instruction=get_system_instruction(),
        description="Kuma Claw - 智能办公助手",
        tools=tools,
    )


def get_agent(query: str = "", force_refresh: bool = False) -> LlmAgent:
    """获取 Agent 实例

    当 query 非空时，总是创建新的 agent 以支持动态工具注入。
    当 query 为空时，使用缓存。

    Args:
        query: 用户消息，用于动态工具注入
        force_refresh: 是否强制刷新缓存
    """
    if query:
        # 动态工具注入：每次创建新 agent
        return create_agent(query)
    if _cache.agent_cache is None or not _cache.is_valid(_cache.agent_cache_time) or force_refresh:
        _cache.agent_cache = create_agent()
        _cache.agent_cache_time = time.time()
        logger.debug("对话 Agent 缓存已过期或不存在，重新创建")
    return _cache.agent_cache


# ============================================
# 导出
# ============================================


def __getattr__(name):
    """懒加载模块属性"""
    if name in ("kuma_claw_agent", "root_agent"):
        return get_agent()
    if name == "TOOLS":
        return get_core_tools()
    if name == "MODEL":
        return get_model()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


if __name__ == "__main__":
    print(f"Kuma Claw Agent 已定义\n总工具数量：{len(get_tools())}")
