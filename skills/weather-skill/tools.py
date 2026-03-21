from google.adk.tools import FunctionTool

def get_weather(city: str) -> str:
    """获取指定城市的天气信息"""
    return f"{city} 今天晴，25°C"

TOOLS = [
    FunctionTool(func=get_weather)
]
