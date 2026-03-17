#!/usr/bin/env python3
"""
Kuma Claw Skills 系统测试脚本
============================
验证 skills 系统是否正常工作
"""

import sys
from pathlib import Path

# 添加项目路径
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

# 添加 skills 脚本路径（目录名含连字符，需特殊处理）
SKILLS_SCRIPTS_DIR = PROJECT_ROOT / "skills" / "kuma-skills-system" / "scripts"
sys.path.insert(0, str(SKILLS_SCRIPTS_DIR))

from skill_manager import SkillManager


def test_skill_manager():
    """测试 SkillManager 基本功能"""
    print("🧪 测试 SkillManager...")

    # 初始化
    skills_dir = PROJECT_ROOT / "kuma_claw" / "skills"
    manager = SkillManager(skills_dir=skills_dir)

    # 列出 skills
    skills_list = manager.list_skills()
    print(f"\n✅ 已加载 {len(skills_list)} 个 skills:")
    for skill in skills_list:
        print(f"  - {skill['name']}: {skill['description']}")

    # 测试触发词匹配
    print("\n🔍 测试触发词匹配...")
    test_cases = [
        "东京今天天气怎么样？",
        "weather in Tokyo",
        "未来三天上海的天气如何？",
        "北京现在多少度？",
    ]

    for test_msg in test_cases:
        skill = manager.get_skill_by_trigger(test_msg)
        if skill:
            print(f"  ✅ '{test_msg}' → 触发 skill: {skill.name}")
        else:
            print(f"  ❌ '{test_msg}' → 未匹配到 skill")

    # 获取所有工具
    tools = manager.get_all_tools()
    print(f"\n🔧 总共 {len(tools)} 个工具可用")

    # 获取所有提示词
    prompts = manager.get_all_prompts()
    print(f"\n📝 提示词长度：{len(prompts)} 字符")

    return True


def test_weather_skill():
    """测试 weather skill 功能"""
    print("\n\n🧪 测试 Weather Skill...")

    try:
        from kuma_claw.skills.weather.tools import get_current_weather

        # 测试天气查询
        result = get_current_weather("Tokyo")
        print(f"\n✅ 天气查询结果:\n{result}")

        return True
    except Exception as e:
        print(f"\n❌ Weather skill 测试失败：{e}")
        return False


def main():
    """运行所有测试"""
    print("=" * 60)
    print("Kuma Claw Skills 系统测试")
    print("=" * 60)

    results = []

    # 测试 1: SkillManager
    try:
        results.append(("SkillManager", test_skill_manager()))
    except Exception as e:
        print(f"\n❌ SkillManager 测试失败：{e}")
        results.append(("SkillManager", False))

    # 测试 2: Weather Skill
    try:
        results.append(("Weather Skill", test_weather_skill()))
    except Exception as e:
        print(f"\n❌ Weather Skill 测试失败：{e}")
        results.append(("Weather Skill", False))

    # 总结
    print("\n\n" + "=" * 60)
    print("测试总结")
    print("=" * 60)

    for name, passed in results:
        status = "✅ 通过" if passed else "❌ 失败"
        print(f"{name}: {status}")

    all_passed = all(result[1] for result in results)

    if all_passed:
        print("\n🎉 所有测试通过！Skills 系统工作正常。")
        return 0
    else:
        print("\n⚠️ 部分测试失败，请检查配置。")
        return 1


if __name__ == "__main__":
    sys.exit(main())
