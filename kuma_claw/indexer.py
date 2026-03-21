"""
Kuma Claw - 统一资源索引器 (Skill & Tool Indexer)
==============================================
实现 "Everything is Context" 逻辑：
将 Skills 和 Tools 的元数据索引到 SQLite 记忆库中。
"""

import logging
from pathlib import Path

from kuma_claw.memory import memory_manager
from kuma_claw.skills.skill_manager import SkillManager

logger = logging.getLogger("kuma_claw.indexer")


def index_all_resources(skills_dir: Path):
    """索引所有 Skills 和 Tools 到记忆库"""
    manager = SkillManager(skills_dir=skills_dir)
    skills = manager.list_skills()

    indexed_count = 0

    for s in skills:
        # 构建索引内容
        content = f"[Skill Registry] Name: {s['name']}\n"
        content += f"Description: {s['description']}\n"
        content += f"Triggers: {', '.join(s['triggers'])}\n"
        content += f"Version: {s['version']}"

        # 存入记忆库
        memory_manager.remember(
            content=content,
            source="registry:skill",
            metadata={"skill_name": s["name"], "type": "skill", "version": s["version"]},
        )
        indexed_count += 1
        logger.info(f"Indexed skill: {s['name']}")

    # 索引基础工具
    from kuma_claw.agent import get_core_tools

    base_tools = get_core_tools()
    for t in base_tools:
        name = getattr(t, "name", "unknown")
        doc = getattr(t.func, "__doc__", "") or ""

        if name == "unknown" and hasattr(t.func, "__name__"):
            name = t.func.__name__

        content = f"[Tool Registry] Name: {name}\nDescription: {doc.strip()}"

        memory_manager.remember(
            content=content, source="registry:tool", metadata={"tool_name": name, "type": "tool"}
        )
        indexed_count += 1
        logger.info(f"Indexed base tool: {name}")

    return indexed_count


if __name__ == "__main__":
    # 配置日志
    logging.basicConfig(level=logging.INFO)

    PROJECT_ROOT = Path(__file__).parent.parent
    # 索引路径：指向 skills 根目录
    skills_path = PROJECT_ROOT / "skills"

    count = index_all_resources(skills_path)
    print(f"✅ 成功索引 {count} 个资源到记忆库。")
