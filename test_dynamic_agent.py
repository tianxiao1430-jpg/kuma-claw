"""
测试 Kuma Claw 动态工具注入
"""

import logging
from unittest.mock import patch

import pytest

logging.basicConfig(level=logging.INFO)


def test_dynamic_injection_creates_agent():
    """测试 create_agent 能正常创建 agent"""
    from kuma_claw.agent import create_agent

    agent = create_agent(query="")
    assert agent is not None
    assert agent.name == "kuma_claw"
    assert len(agent.tools) > 0


def test_dynamic_injection_includes_core_tools():
    """测试 agent 包含核心工具"""
    from kuma_claw.agent import get_core_tools

    tools = get_core_tools()
    tool_names = [t.func.__name__ for t in tools]
    assert "web_search" in tool_names
    assert "get_current_time" in tool_names
    assert "remember" in tool_names
    assert "recall" in tool_names


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
