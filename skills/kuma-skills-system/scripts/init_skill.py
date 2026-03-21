#!/usr/bin/env python3
"""
kuma_claw/skills/scripts/init_skill.py
=======================================
初始化新 skill 结构
"""

import argparse
import json
from pathlib import Path


def init_skill(skill_name: str, skills_dir: Path):
    """初始化新 skill"""
    skill_dir = skills_dir / skill_name

    # 创建目录
    skill_dir.mkdir(parents=True, exist_ok=True)

    # 创建 skill.json
    skill_json = {
        "name": skill_name,
        "version": "1.0.0",
        "description": f"{skill_name} skill for kuma-claw",
        "triggers": [skill_name],
        "author": "",
        "dependencies": [],
        "tools": [],
    }

    with open(skill_dir / "skill.json", "w") as f:
        json.dump(skill_json, f, indent=2)

    # 创建 tools.py
    tools_py = f'''"""
{skill_name} - 工具定义
"""

from google.adk.tools import FunctionTool


def example_tool(param: str) -> str:
    """示例工具

    Args:
        param: 参数说明

    Returns:
        结果字符串
    """
    return f"收到: {{param}}"


TOOLS = [
    FunctionTool(func=example_tool)
]
'''

    with open(skill_dir / "tools.py", "w") as f:
        f.write(tools_py)

    # 创建 prompts.py
    prompts_py = f'''"""
{skill_name} - 提示词定义
"""

SYSTEM_PROMPT = """
## {skill_name} 能力

TODO: 添加技能说明
"""

EXAMPLES = [
    {{
        "user": "示例用户输入",
        "assistant": "示例助手回复",
        "tool_call": "example_tool(param='value')"
    }}
]
'''

    with open(skill_dir / "prompts.py", "w") as f:
        f.write(prompts_py)

    # 创建 __init__.py
    with open(skill_dir / "__init__.py", "w") as f:
        f.write(
            f'"""{skill_name} skill"""\nfrom .tools import TOOLS\nfrom .prompts import SYSTEM_PROMPT, EXAMPLES\n'
        )

    print(f"✅ Skill '{skill_name}' 初始化成功")
    print(f"   位置: {skill_dir}")
    print("\n下一步:")
    print("1. 编辑 skill.json 添加触发词和工具定义")
    print("2. 实现 tools.py 中的工具函数")
    print("3. 完善 prompts.py 中的系统提示词")


def main():
    parser = argparse.ArgumentParser(description="初始化新 skill")
    parser.add_argument("skill_name", help="Skill 名称")
    parser.add_argument("--skills-dir", default="kuma_claw/skills", help="Skills 目录路径")

    args = parser.parse_args()
    skills_dir = Path(args.skills_dir)

    init_skill(args.skill_name, skills_dir)


if __name__ == "__main__":
    main()
