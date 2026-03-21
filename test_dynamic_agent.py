"""
测试 Kuma Claw 动态工具注入
"""
import logging
from pathlib import Path
from kuma_claw.agent import create_agent

# 启用日志查看注入过程
logging.basicConfig(level=logging.INFO)

def test_dynamic_injection(query: str):
    print(f"\n🔍 测试查询: '{query}'")
    agent = create_agent(query=query)
    
    print(f"🛠️  已注入工具列表:")
    tool_names = []
    for tool in agent.tools:
        name = getattr(tool, 'name', None) or tool.func.__name__
        tool_names.append(name)
        print(f"  - {name}")
        
    if "get_weather" in tool_names:
        print("✅ 成功匹配并注入天气技能！")
    else:
        print("ℹ️  未注入天气技能（不相关或逻辑有误）。")

if __name__ == "__main__":
    # 尝试一个非常明确的触发词
    test_dynamic_injection("weather")
