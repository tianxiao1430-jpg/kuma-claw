"""
Kuma Claw - Agent 定义
====================
基于 Google ADK 的 AI Agent
"""

import os
import logging
from pathlib import Path
from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool

# 配置日志
logger = logging.getLogger("kuma_claw")

try:
    from .config import config
    MODEL = config.get_model()
except ImportError:
    MODEL = os.environ.get("KUMA_MODEL", "gemini-3.1-flash")


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
    """加载 ADK 内置的 Google Workspace 工具集

    Returns:
        工具集列表（失败时返回空列表）
    """
    try:
        from .tools.adk_google_workspace import create_all_google_workspace_toolsets
        return create_all_google_workspace_toolsets()
    except ImportError as e:
        logger.warning(f"Google Workspace 工具集不可用：{e}")
        return []
    except Exception as e:
        logger.error(f"加载 Google Workspace 工具集失败：{e}")
        return []


# ============================================
# Skill 工具自动注册
# ============================================

def _load_and_register_skills(tools_list: list) -> int:
    """加载 Skills 并注册工具到 Agent

    Args:
        tools_list: 现有工具列表（会被修改）

    Returns:
        注册的 Skill 工具数量
    """
    try:
        # 尝试从多个可能的位置加载 skill_manager
        skill_manager = None
        
        # 位置 1: skills/kuma-skills-system/scripts/skill_manager.py
        skills_script_path = Path(__file__).parent.parent / "skills" / "kuma-skills-system" / "scripts"
        if (skills_script_path / "skill_manager.py").exists():
            import sys
            if str(skills_script_path) not in sys.path:
                sys.path.insert(0, str(skills_script_path))
            
            try:
                from skill_manager import skill_manager
                logger.info(f"从 {skills_script_path} 加载 skill_manager")
            except ImportError as e:
                logger.warning(f"无法从 skills_script_path 加载 skill_manager: {e}")
        
        # 位置 2: kuma_claw/skills/skill_manager.py
        if skill_manager is None:
            try:
                from .skills.skill_manager import skill_manager
                logger.info("从 kuma_claw.skills 加载 skill_manager")
            except ImportError as e:
                logger.warning(f"无法从 kuma_claw.skills 加载 skill_manager: {e}")
        
        if skill_manager is None:
            logger.warning("无法加载 skill_manager，Skills 工具将不可用")
            return 0
        
        # 注册工具
        registered_count = skill_manager.register_tools_to_agent(type('Agent', (), {'tools': tools_list})())
        
        # 由于 register_tools_to_agent 直接修改了 tools_list，我们返回注册数量
        skill_tools = skill_manager.get_all_tools()
        logger.info(f"加载了 {len(skill_tools)} 个 Skill 工具")
        
        return len(skill_tools)
        
    except Exception as e:
        logger.error(f"加载 Skills 失败：{e}")
        return 0


# ============================================
# 注册工具
# ============================================

# 基础工具
TOOLS = [
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
    TOOLS.extend(google_workspace_toolsets)
    logger.info(f"已加载 {len(google_workspace_toolsets)} 个 Google Workspace 工具集")

# 自动注册 Skills 工具
skills_tools_count = _load_and_register_skills(TOOLS)
if skills_tools_count > 0:
    logger.info(f"已注册 {skills_tools_count} 个 Skill 工具")


# ============================================
# 模型配置
# ============================================

def get_model():
    """获取模型配置"""
    if MODEL.startswith("openai/"):
        from google.adk.models.lite_llm import LiteLlm
        return LiteLlm(model=MODEL)
    elif MODEL.startswith("anthropic/"):
        from google.adk.models.lite_llm import LiteLlm
        return LiteLlm(model=MODEL)
    elif MODEL.startswith("deepseek/"):
        from google.adk.models.lite_llm import LiteLlm
        return LiteLlm(model=MODEL)
    else:
        # 默认 Gemini
        return MODEL


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

    full_prompt = base_prompt + time_prompt + internal_prompt

    # 动态注入格式规范
    full_prompt = inject_format_prompt(full_prompt, channel)

    return full_prompt


def create_agent(channel: str = "telegram") -> LlmAgent:
    """创建 Agent 实例（支持渠道适配）

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
        tools=TOOLS,
    )


# 默认 Agent（向后兼容）
kuma_claw_agent = LlmAgent(
    name="kuma_claw",
    model=get_model(),
    instruction=get_system_instruction("telegram"),
    description="Kuma Claw - 智能办公助手",
    tools=TOOLS,
)


# ============================================
# 导出
# ============================================

root_agent = kuma_claw_agent


if __name__ == "__main__":
    print("Kuma Claw Agent 已定义")
    print(f"基础工具数量：{len(TOOLS) - len(google_workspace_toolsets) - skills_tools_count}")
    print(f"Google Workspace 工具集：{len(google_workspace_toolsets)} 个")
    print(f"Skill 工具：{skills_tools_count} 个")
    print(f"总工具数量：{len(TOOLS)}")
    print("\n支持的渠道：telegram, slack, discord, web, whatsapp, console")
