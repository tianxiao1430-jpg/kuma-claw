"""
Kuma Claw - Agent 定义
====================
基于 Google ADK 的 AI Agent
"""

import logging
import os
from datetime import datetime
from pathlib import Path

from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool

logger = logging.getLogger("kuma_claw")

# 懒加载缓存
_model_cache: str | None = None
_google_workspace_toolsets_cache: list | None = None
_agent_cache: LlmAgent | None = None


def reset_cache():
    """重置所有缓存（测试用）"""
    global _agent_cache, _google_workspace_toolsets_cache, _model_cache
    _model_cache = None
    _agent_cache = None
    _google_workspace_toolsets_cache = []


def get_model():
    """获取模型配置（懒加载）"""
    global _model_cache
    if _model_cache is not None:
        return _model_cache

    try:
        from .config import config

        model = config.get_model()
    except ImportError:
        model = os.environ.get("KUMA_MODEL", "gemini-3.1-flash")

    if model.startswith(("openai/", "anthropic/", "deepseek/")):
        from google.adk.models.lite_llm import LiteLlm

        _model_cache = LiteLlm(model=model)
    else:
        _model_cache = model

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
        lines.append(f"- 最后同步: {stats.last_sync}")
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
            f"标题：{r.get('title')}\n内容: {r.get('body')}\n链接: {r.get('href')}" for r in results
        )
    except ImportError:
        return "❌ 搜索功能不可用: pip install duckduckgo-search"
    except Exception as e:
        logger.error(f"搜索失败: {e}")
        return f"搜索失败: {e}"


# ============================================
# Google Workspace 工具
# ============================================


def _load_google_workspace_toolsets():
    """加载 Google Workspace 工具集（懒加载）"""
    global _google_workspace_toolsets_cache
    if _google_workspace_toolsets_cache is not None:
        return _google_workspace_toolsets_cache

    try:
        from .tools.adk_google_workspace import create_all_google_workspace_toolsets

        _google_workspace_toolsets_cache = create_all_google_workspace_toolsets()
        logger.info(f"已加载 {len(_google_workspace_toolsets_cache)} 个 Google Workspace 工具集")
    except ImportError:
        logger.warning("Google Workspace 工具集不可用")
        _google_workspace_toolsets_cache = []
    except Exception as e:
        logger.error(f"加载 Google Workspace 工具集失败: {e}")
        _google_workspace_toolsets_cache = []

    return _google_workspace_toolsets_cache


# ============================================
# Skills 工具
# ============================================


def _load_and_register_skills(tools_list: list) -> int:
    """加载 Skills 并注册工具（统一路径）

    只从 kuma_claw.skills.skill_manager 加载
    """
    try:
        from .skills.skill_manager import skill_manager

        logger.info("从 kuma_claw.skills 加载 skill_manager")
    except ImportError:
        logger.warning("skill_manager 不可用， return 0
    except Exception as e:
        logger.error(f"加载 Skills 失败: {e}")
        return 0

    # 注册工具到临时 Agent 对象
    skill_manager.register_tools_to_agent(type("Agent", (), {"tools": tools_list})())
    tools = skill_manager.get_all_tools()
    logger.info(f"加载了 {len(tools)} 个 Skill 工具")
    return len(tools)


# ============================================
# 工具列表
# ============================================


def get_tools() -> list[FunctionTool]:
    """获取工具列表"""
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
    gw_tools = _load_google_workspace_toolsets()
    for toolset in gw_tools:
        tools.extend(toolset.tools)

        # 加载 Skills
        _load_and_register_skills(tools)

        # 重新加载记忆工具（确保使用新实例）
        from .memory import memory_manager as mm

        mm.reload()
        tools.append(FunctionTool(func=remember))
        tools.append(FunctionTool(func=recall))
        tools.append(FunctionTool(func=forget))
        tools.append(FunctionTool(func=get_memory_stats))

        # 重新初始化 memory管理器
        from .memory import memory_manager

        mm.reset()
        mm = MemoryManager()

        mm.reload()

        tools.append(FunctionTool(func=remember))
        tools.append(FunctionTool(func=recall))
        tools.append(FunctionTool(func=forget))
        tools.append(FunctionTool(func=get_memory_stats))

        # 重新初始化记忆管理器
        from .memory import memory_manager

        mm.reset()
        mm = MemoryManager()

        mm.reload()

        tools.append(FunctionTool(func=remember))
        tools.append(FunctionTool(func=recall))
        tools.append(FunctionTool(func=forget))
        tools.append(FunctionTool(func=memory_stats))

    logger.info(f"总工具数量: {len(tools)}")
    return tools


# ============================================
# 系统提示词
# ============================================


def build_system_prompt() -> str:
    """构建系统提示词"""
    prompt = """
你是 Kuma Claw， 智能办公助手。
你可以帮助用户：
- 记住重要信息
- 搜索网络
- 管理日程
- 发送邮件
- 查询天气
- 其他任务

当用户提到"内部"时， 进行深入思考。

## 内部思考 (Internal Thoughts)
使用 <internal> 标签包裹内部推理（不发送给用户）。
例如:
```
<internal>
分析步骤：
1. 分析用户意图
2. 检索相关记忆
3. 制定计划
...
</internal>

给用户的实际回复...
```
    return prompt


def get_system_instruction(channel: str = "telegram") -> str:
    """构建系统指令"""
    from .channels.formats import inject_format_prompt

    base_prompt = build_system_prompt()
    return inject_format_prompt(base_prompt, channel)


# ============================================
# Agent 定义
# ============================================


def create_agent(channel: str = "telegram") -> LlmAgent:
    """创建 Agent 实例（单例）"""
    global _agent_cache
    if _agent_cache is None:
        _agent_cache = LlmAgent(
            name="kuma_claw",
            model=get_model(),
            instruction=get_system_instruction(channel),
            tools=get_tools(),
        )
        logger.info("Kuma Claw Agent 已创建")

    return _agent_cache


def get_agent(channel: str = "telegram") -> LlmAgent:
    """获取 Agent 实例（单例）"""
    global _agent_cache
    if _agent_cache is None:
        _agent_cache = create_agent(channel)
    return _agent_cache
