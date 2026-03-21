"""
weather - 工具定义
==================
天气查询工具
"""

import requests
from google.adk.tools import FunctionTool


def get_current_weather(city: str) -> str:
    """获取指定城市的当前天气

    Args:
        city: 城市名称（中文或英文）

    Returns:
        天气信息字符串
    """
    try:
        # 使用 wttr.in（免费 API）
        url = f"http://wttr.in/{city}?format=%l:+%t+%C&lang=zh"
        response = requests.get(url, timeout=5)

        if response.status_code == 200:
            return response.text.strip()
        else:
            return f"❌ 无法获取 {city} 的天气信息"
    except Exception as e:
        return f"❌ 天气查询失败: {str(e)}"


def get_weather_forecast(city: str, days: int = 3) -> str:
    """获取未来几天的天气预报

    Args:
        city: 城市名称
        days: 预报天数（1-7天）

    Returns:
        天气预报字符串
    """
    try:
        url = f"http://wttr.in/{city}?lang=zh&format=j1"
        response = requests.get(url, timeout=5)

        if response.status_code != 200:
            return f"❌ 无法获取 {city} 的天气预报"

        data = response.json()
        forecast_lines = [f"📍 {city} 未来 {days} 天天气预报：\n"]

        for _i, day in enumerate(data["weather"][:days]):
            date = day["date"]
            max_temp = day["maxtempC"]
            min_temp = day["mintempC"]
            avg_temp = day["avgtempC"]
            desc = day["hourly"][0]["lang_zh"][0]["value"]

            forecast_lines.append(
                f"📅 {date}\n" f"   🌡️ {min_temp}°C - {max_temp}°C (平均 {avg_temp}°C)\n" f"   ☁️ {desc}\n"
            )

        return "\n".join(forecast_lines)
    except Exception as e:
        return f"❌ 天气预报查询失败: {str(e)}"


TOOLS = [FunctionTool(func=get_current_weather), FunctionTool(func=get_weather_forecast)]
