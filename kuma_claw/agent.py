"""
Kuma Claw - Agent 定义
====================
基于 Google ADK 的 AI Agent
"""

import os
import logging
from typing import Optional, List
from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool

# 配置日志
logger = logging.getLogger("kuma_claw")

# 懒加载：模型配置在首次调用时初始化
_model_cache: Optional[str] = None
_google_workspace_toolsets_cache: Optional[List] = None
_agent_cache: Optional[LlmAgent] = None


# ============================================
# 懒加载：模型配置
# ============================================

def get_model():
    """获取模型配置（懒加载）"""
    global _model_cache
    
    if _model_cache is not None:
        return _model_cache
    
    # 首次调用时加载
    try:
        from .config import config
        model = config.get_model()
    except ImportError:
        model = os.environ.get("KUMA_MODEL", "gemini-3.1-flash")
    
    # 根据模型类型初始化
    if model.startswith("openai/") or model.startswith("anthropic/") or model.startswith("deepseek/"):
        from google.adk.models.lite_llm import LiteLlm
        _model_cache = LiteLlm(model=model)
    else:
        # 默认 Gemini
        _model_cache = model
    
    return _model_cache


# ============================================
# 工具定义
# ============================================

def get_current_time() -> str:
    """获取当前时间"""
    from datetime import datetime
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def echo_message(message: str) -> str:
    """回显消息（测试用）"""
    return f"收到：{message}"


# ============================================
# 记忆工具
# ============================================

def remember(content: str, source: str = "fact") -> str:
    """记住重要信息

    Args:
        content: 要记住的内容
        source: 来源类型（fact/preference/note）

    Returns:
        确认消息
    """
    from .memory import memory_manager
    entry = memory_manager.remember(content, source=source)
    return f"✅ 已记住：{content}"


def recall(query: str, limit: int = 5) -> str:
    """回忆相关信息

    Args:
        query: 搜索关键词
        limit: 返回数量

    Returns:
        相关记忆
    """
    from .memory import memory_manager
    results = memory_manager.search(query, limit=limit)

    if not results:
        return "没有找到相关记忆"

    lines = ["📚 相关记忆："]
    for r in results:
        lines.append(f"- {r.entry.content}")

    return "\n".join(lines)


def forget(content_pattern: str) -> str:
    """忘记特定记忆

    Args:
        content_pattern: 要忘记的内容模式

    Returns:
        确认消息
    """
    from .memory import memory_manager
    results = memory_manager.search(content_pattern, limit=1)

    if not results:
        return "没有找到匹配的记忆"

    entry = results[0].entry
    memory_manager.forget(entry.id)
    return f"✅ 已忘记：{entry.content}"


def get_memory_stats() -> str:
    """获取记忆统计

    Returns:
        记忆统计信息
    """
    from .memory import memory_manager
    stats = memory_manager.stats()

    lines = [
        f"📊 记忆统计：",
        f"- 总条目：{stats.total_entries}",
    ]

    for source, count in stats.by_source.items():
        lines.append(f"- {source}: {count}")

    if stats.last_sync:
        lines.append(f"- 最后同步：{stats.last_sync}")

    return "\n".join(lines)


# ============================================
# 网络搜索工具
# ============================================

def web_search(query: str, limit: int = 5) -> str:
    """通过 DuckDuckGo 搜索网络获取实时信息

    Args:
        query: 搜索关键词
        limit: 返回的结果数量上限

    Returns:
        包含标题、摘要和链接的搜索结果文本
    """
    try:
        # 优先使用新包 ddgs
        try:
            from ddgs import DDGS
            logger.debug("使用 ddgs 包（新）")

            # 新包：直接返回 list
            with DDGS() as ddgs:
                results_raw = ddgs.text(query, max_results=limit)

            results = []
            for r in results_raw:
                results.append(
                    f"标题：{r.get('title')}\n"
                    f"内容：{r.get('body')}\n"
                    f"链接：{r.get('href')}"
                )

        except ImportError:
            # 备选：旧包 duckduckgo_search
            try:
                from duckduckgo_search import DDGS
                logger.debug("使用 duckduckgo-search 包（旧）")

                # 旧包：需要 with 语句
                results = []
                with DDGS() as ddgs:
                    for r in ddgs.text(query, max_results=limit):
                        results.append(
                            f"标题：{r.get('title')}\n"
                            f"内容：{r.get('body')}\n"
                            f"链接：{r.get('href')}"
                        )

            except ImportError:
                return (
                    "❌ 搜索功能不可用：未安装搜索库\n"
                    "安装新包：pip install ddgs>=9.0.0\n"
                    "或旧包：pip install duckduckgo-search"
                )

        if not results:
            return f"没有找到关于 '{query}' 的搜索结果。"

        return "\n\n".join(results)

    except Exception as e:
        logger.error(f"搜索失败：{str(e)}")
        return f"搜索失败：{str(e)}"


# ============================================
# Google Workspace 工具（ADK 内置）
# ============================================

def _load_google_workspace_toolsets():
    """加载 ADK 内置的 Google Workspace 工具集（懒加载 + 缓存）

    Returns:
        工具集列表（失败时返回空列表）
    """
    global _google_workspace_toolsets_cache
    
    if _google_workspace_toolsets_cache is not None:
        return _google_workspace_toolsets_cache
    
    try:
        from .tools.adk_google_workspace import create_all_google_workspace_toolsets
        _google_workspace_toolsets_cache = create_all_google_workspace_toolsets()
        logger.info(f"已加载 {len(_google_workspace_toolsets_cache)} 个 Google Workspace 工具集")
        return _google_workspace_toolsets_cache
    except ImportError as e:
        logger.warning(f"Google Workspace 工具集不可用：{e}")
        _google_workspace_toolsets_cache = []
        return []
    except Exception as e:
        logger.error(f"加载 Google Workspace 工具集失败：{e}")
        _google_workspace_toolsets_cache = []
        return []


# ============================================
# 懒加载：工具列表
# ============================================

def get_tools() -> List[FunctionTool]:
    """获取工具列表（懒加载）

    Returns:
        工具列表
    """
    # 基础工具
    tools = [
        FunctionTool(func=web_search),
        FunctionTool(func=get_current_time),
        FunctionTool(func=echo_message),
        FunctionTool(func=remember),
        FunctionTool(func=recall),
        FunctionTool(func=forget),
        FunctionTool(func=get_memory_stats),
    ]

    # 添加 ADK 内置 Google Workspace 工具集
    google_workspace_toolsets = _load_google_workspace_toolsets()
    if google_workspace_toolsets:
        tools.extend(google_workspace_toolsets)

    return tools


# ============================================
# Agent 定义
# ============================================

def get_system_instruction(channel: str = "telegram") -> str:
    """构建系统提示词（支持动态格式注入）

    Args:
        channel: 渠道名称（telegram, slack, discord, web, whatsapp）

    Returns:
        完整的系统提示词
    """
    from .prompts import build_system_prompt
    from .channels.formats import get_format_prompt, inject_format_prompt

    base_prompt = build_system_prompt()

    # 检查 Google Workspace 工具集状态
    google_workspace_toolsets = _load_google_workspace_toolsets()
    google_workspace_status = "已启用" if google_workspace_toolsets else "未配置"

    # 添加工具说明
    tools_prompt = f"""

## 可用工具 (Tools)

### 基础工具
- **get_current_time**: 获取当前时间
- **web_search**: 通过 DuckDuckGo 搜索网络获取实时信息
  - 用法：web_search(query, limit=5)
  - 核心指令：遇到需要最新数据的问题时**必须**使用此工具

### 记忆工具
- **remember**: 记住重要信息
  - 用法：remember(content, source)
  - source: "fact" | "preference" | "note"
- **recall**: 回忆相关信息
  - 用法：recall(query, limit=5)
- **forget**: 忘记特定记忆
  - 用法：forget(content_pattern)
- **get_memory_stats**: 获取记忆统计

### Google Workspace 工具 ({google_workspace_status})

使用 ADK 内置的 GoogleApiToolset，支持：
- **Gmail**: 邮件发送、列表、搜索、草稿
- **Calendar**: 事件列表、创建、更新、删除
- **Sheets**: 单元格读写、追加、创建表格
- **Docs**: 文档读取、创建

工具会根据 OAuth 配置自动启用。

## 记忆策略

- 用户偏好 → remember(source="preference")
- 重要事实 → remember(source="fact")
- 临时笔记 → remember(source="note")
- 需要回忆时 → recall()

## 工具使用原则

1. **网络搜索**：遇到需要最新数据的问题（天气、新闻、股价），**必须**使用 web_search
2. **Google Workspace**：用户请求邮件/日历/文件操作时，**主动**使用相应工具
3. **确认操作**：执行敏感操作（发送邮件、删除文件）前，**先确认**用户意图
"""

    # 添加内部思考标签说明
    internal_prompt = """

## 内部思考 (Internal Thoughts)

如果部分输出是你的内部推理过程而非给用户的内容，使用 `<internal>` 标签：

```
<internal>
你的内部思考过程...
分析步骤、决策逻辑、调试信息等...
</internal>

给用户的实际回复...
```

`<internal>` 标签内的内容会被记录到日志但**不会发送给用户**。
"""

    # 组合基础提示词
    import datetime
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    time_prompt = f"\n\n## 系统信息\n当前时间：{now_str}\n"

    full_prompt = base_prompt + time_prompt + tools_prompt + internal_prompt

    # 动态注入格式规范
    full_prompt = inject_format_prompt(full_prompt, channel)

    return full_prompt


def create_agent(channel: str = "telegram") -> LlmAgent:
    """创建 Agent 实例（懒加载 + 支持渠道适配）

    Args:
        channel: 渠道名称

    Returns:
        配置好的 Agent 实例
    """
    return LlmAgent(
        name="kuma_claw",
        model=get_model(),
        instruction=get_system_instruction(channel),
        description="Kuma Claw - 智能办公助手",
        tools=get_tools(),
    )


def get_agent(channel: str = "telegram") -> LlmAgent:
    """获取 Agent 实例（单例模式，懒加载）

    Args:
        channel: 渠道名称

    Returns:
        Agent 实例
    """
    global _agent_cache
    
    if _agent_cache is not None:
        return _agent_cache
    
    _agent_cache = create_agent(channel)
    return _agent_cache


# ============================================
# 导出（向后兼容）
# ============================================

# 懒加载：仅在访问时创建
def __getattr__(name):
    """支持模块级属性的懒加载"""
    if name == "kuma_claw_agent":
        return get_agent("telegram")
    elif name == "root_agent":
        return get_agent("telegram")
    elif name == "TOOLS":
        return get_tools()
    elif name == "MODEL":
        return get_model()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


if __name__ == "__main__":
    print("Kuma Claw Agent 已定义")
    tools = get_tools()
    google_workspace_toolsets = _load_google_workspace_toolsets()
    print(f"基础工具数量：{len(tools) - len(google_workspace_toolsets)}")
    print(f"Google Workspace 工具集：{len(google_workspace_toolsets)} 个")
    print(f"总工具数量：{len(tools)}")
    print("\n支持的渠道：telegram, slack, discord, web, whatsapp, console")
