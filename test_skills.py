#!/usr/bin/env python3
"""
Kuma Claw Skills 系统测试
========================
"""

import sys
import pytest
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent


@pytest.fixture(scope="session")
def skills_dir():
    """Skills 目录（动态查找）"""
    # 位置 1: kuma_claw/skills/
    internal = PROJECT_ROOT / "kuma_claw" / "skills"
    if internal.exists():
        return internal
    
    # 位置 2: skills/kuma-skills-system/
    external = PROJECT_ROOT / "skills" / "kuma-skills-system"
    if external.exists():
        return external
    
    pytest.skip("Skills directory not found")
    return None


def test_skill_manager(skills_dir):
    """测试 SkillManager"""
    try:
        from kuma_claw.skills.skill_manager import SkillManager
    except ImportError:
        pytest.skip("SkillManager not available")
    
    manager = SkillManager(skills_dir=skills_dir)
    skills_list = manager.list_skills()
    
    assert isinstance(skills_list, list)
    print(f"✅ 已加载 {len(skills_list)} 个 skills")


def test_weather_skill():
    """测试 Weather Skill"""
    try:
        from kuma_claw.skills.weather.tools import get_current_weather
    except ImportError:
        pytest.skip("Weather skill not available")
    
    result = get_current_weather("Tokyo")
    assert isinstance(result, str)
    print(f"✅ 天气查询成功")


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
