"""
Kuma Claw - Agent 定义
====================
基于 Google ADK 的 AI Agent
支持统一资源检索 (Everything is Context)
"""

import os
import sys
import logging
from pathlib import Path
from typing import Optional, List, Any
from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool

# 强制重置日志级别以观察
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("kuma_claw")

# 懒加载缓存
_model_cache: Optional[Any] = None
_google_workspace_toolsets_cache: Optional[List] = None
_skill_manager_cache: Optional[Any] = None


# ============================================
# 基础配置与模型
# ============================================

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
    
    if model.startswith("openai/") or model.startswith("anthropic/") or model.startswith("deepseek/"):
        from google.adk.models.lite_llm import LiteLlm
        _model_cache = LiteLlm(model=model)
    else:
        _model_cache = model
    return _model_cache


# ============================================
# 核心工具 (Permanent Tools)
# ============================================

def get_current_time() -> str:
    """获取当前日期和时间"""
    from datetime import datetime
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def remember(content: str, source: str = "fact") -> str:
    """记住重要信息、事实或用户偏好"""
    from .memory import memory_manager
    memory_manager.remember(content, source=source)
    return f"✅ 已记住：{content}"

def recall(query: str, limit: int = 5) -> str:
    """回忆之前记住的相关信息或会话历史"""
    from .memory import memory_manager
    results = memory_manager.search(query, limit=limit)
    if not results: return "没有找到相关记忆"
    lines = ["📚 相关记忆："]
    for r in results:
        lines.append(f"- {r.entry.content}")
    return "\n".join(lines)

def web_search(query: str, limit: int = 5) -> str:
    """通过网络搜索获取实时信息"""
    try:
        from ddgs import DDGS
        with DDGS() as ddgs:
            results_raw = ddgs.text(query, max_results=limit)
        results = [f"标题：{r.get('title')}\n内容：{r.get('body')}\n链接：{r.get('href')}" for r in results_raw]
        return "\n\n".join(results) if results else f"没有找到关于 '{query}' 的结果。"
    except Exception as e:
        return f"搜索失败：{str(e)}"

# ============================================
# 技能管理与动态注入 (The "Everything is Context" Logic)
# ============================================

def _get_skill_manager():
    """获取 SkillManager 实例"""
    global _skill_manager_cache
    if _skill_manager_cache is not None:
        return _skill_manager_cache
    
    # 获取项目根目录
    PROJECT_ROOT = Path(__file__).parent.parent
    # 修改：SkillManager 默认从项目的 skills 目录加载
    SKILLS_DIR = PROJECT_ROOT / "skills"
    SKILLS_SCRIPT_PATH = SKILLS_DIR / "kuma-skills-system" / "scripts"
    
    if str(SKILLS_SCRIPT_PATH) not in sys.path:
        sys.path.insert(0, str(SKILLS_SCRIPT_PATH))

    try:
        from skill_manager import SkillManager
        # 注意：这里需要传入 skills_dir
        _skill_manager_cache = SkillManager(skills_dir=SKILLS_DIR)
        logger.debug(f"SkillManager 加载完成，技能数量: {len(_skill_manager_cache.skills)}")
    except Exception as e:
        logger.error(f"无法加载 SkillManager: {e}")
        return None
    return _skill_manager_cache

def get_core_tools() -> List[FunctionTool]:
    """获取核心基础工具"""
    return [
        FunctionTool(func=web_search),
        FunctionTool(func=get_current_time),
        FunctionTool(func=remember),
        FunctionTool(func=recall),
    ]

def get_dynamic_resources(query: str) -> List[FunctionTool]:
    """根据输入动态检索并返回相关的工具/技能 (Everything is Context)"""
    from .memory import memory_manager
    
    tools = get_core_tools()
    
    # 1. 在记忆库中检索相关的 Skill/Tool 注册信息
    search_results = memory_manager.search(query, limit=5)
    
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
            tools.extend(skill.tools)
        else:
            logger.warning(f"技能已索引但加载失败: {skill_name}")
            
    # 3. 如果通过记忆搜索没搜到，尝试触发词兜底
    if not matched_skills:
        skill = sm.get_skill_by_trigger(query)
        if skill:
            logger.info(f"根据触发词注入技能: {skill.name}")
            tools.extend(skill.tools)

    return tools


# ============================================
# Agent 工厂
# ============================================

def get_system_instruction(channel: str = "telegram") -> str:
    """构建系统提示词"""
    from .prompts import build_system_prompt
    from .channels.formats import inject_format_prompt
    
    base_prompt = build_system_prompt()
    internal_prompt = "\n\n## 内部思考\n使用 `<internal>` 标签记录你的推理过程，这不会发送给用户。"
    
    import datetime
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    time_prompt = f"\n\n## 系统信息\n当前时间：{now_str}\n"
    
    full_prompt = base_prompt + time_prompt + internal_prompt
    return inject_format_prompt(full_prompt, channel)

def create_agent(query: str = "", channel: str = "telegram") -> LlmAgent:
    """创建 Agent 实例（支持动态工具注入）"""
    # 如果有 query，则根据 query 动态选择工具
    tools = get_dynamic_resources(query) if query else get_core_tools()
    
    return LlmAgent(
        name="kuma_claw",
        model=get_model(),
        instruction=get_system_instruction(channel),
        description="Kuma Claw - 智能办公助手",
        tools=tools,
    )

def get_agent(channel: str = "telegram") -> LlmAgent:
    """获取默认 Agent (静态)"""
    return create_agent(channel=channel)

# ============================================
# 导出
# ============================================

def __getattr__(name):
    if name in ["kuma_claw_agent", "root_agent"]:
        return get_agent("telegram")
    elif name == "TOOLS":
        return get_core_tools()
    elif name == "MODEL":
        return get_model()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
