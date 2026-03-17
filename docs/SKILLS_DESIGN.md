# Kuma Claw Skills 系统设计方案

## 概述

为 kuma-claw 添加类似 OpenClaw 的 Skills 系统，实现模块化、可扩展的能力管理。

## 核心设计原则

1. **原生 Python 实现** - 与 kuma-claw 架构无缝集成
2. **基于 Google ADK FunctionTool** - 复用现有工具系统
3. **轻量级** - 最小依赖，快速加载
4. **社区驱动** - 支持本地 + 远程 skill 安装
5. **按需加载** - 根据触发词动态加载 skill

## 目录结构

```
kuma_claw/
├── skills/
│   ├── skill_manager.py          # Skill 管理器
│   ├── base_skill.py              # Skill 基类
│   ├── weather/                   # 示例 skill
│   │   ├── skill.json             # 元数据
│   │   ├── tools.py               # 工具函数
│   │   ├── prompts.py             # 提示词模板
│   │   └── __init__.py
│   ├── github/
│   │   ├── skill.json
│   │   ├── tools.py
│   │   ├── prompts.py
│   │   └── __init__.py
│   └── browser/
│       ├── skill.json
│       ├── tools.py
│       ├── prompts.py
│       └── __init__.py
├── agent.py                       # 修改：集成 skill_manager
└── cli.py                         # 修改：添加 skill 管理命令
```

## Skill 定义规范

### skill.json（元数据）

```json
{
  "name": "weather",
  "version": "1.0.0",
  "description": "获取天气和预报信息",
  "triggers": ["天气", "weather", "气温", "预报"],
  "author": "kuma-claw-team",
  "dependencies": [],
  "tools": [
    {
      "name": "get_current_weather",
      "description": "获取指定城市的当前天气",
      "parameters": {
        "city": {
          "type": "string",
          "description": "城市名称",
          "required": true
        }
      }
    }
  ],
  "prompts": {
    "system": "你是一个天气助手...",
    "examples": []
  }
}
```

### tools.py（工具实现）

```python
"""天气查询工具"""
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

# 导出工具列表
TOOLS = [
    FunctionTool(func=get_current_weather)
]
```

### prompts.py（提示词模板）

```python
"""天气 Skill 提示词"""

SYSTEM_PROMPT = """
## 天气查询能力

你可以通过 `get_current_weather` 工具获取实时天气信息。

使用场景：
- 用户询问"今天天气怎么样"
- 用户询问某城市的气温
- 用户需要出行前的天气参考

调用示例：
```python
get_current_weather(city="东京")
```

注意事项：
1. 城市名称支持中文和英文
2. 如果用户没有指定城市，询问用户位置
3. 结果包含温度、天气状况等信息
"""

EXAMPLES = [
    {
        "user": "东京今天天气怎么样？",
        "assistant": "让我查一下东京的天气信息。",
        "tool_call": "get_current_weather(city='东京')"
    }
]
```

### __init__.py（导出接口）

```python
"""天气 Skill"""
from .tools import TOOLS
from .prompts import SYSTEM_PROMPT, EXAMPLES

__all__ = ["TOOLS", "SYSTEM_PROMPT", "EXAMPLES"]
```

## Skill Manager 实现

```python
"""
kuma_claw/skills/skill_manager.py
==================================
Skill 管理器 - 加载、注册、管理 skills
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional
from google.adk.tools import FunctionTool

logger = logging.getLogger("kuma_claw")


class Skill:
    """Skill 定义"""
    
    def __init__(self, skill_dir: Path):
        self.dir = skill_dir
        self.metadata = self._load_metadata()
        self.tools = self._load_tools()
        self.prompts = self._load_prompts()
    
    def _load_metadata(self) -> dict:
        """加载 skill.json"""
        metadata_file = self.dir / "skill.json"
        if not metadata_file.exists():
            raise FileNotFoundError(f"skill.json not found in {self.dir}")
        
        with open(metadata_file) as f:
            return json.load(f)
    
    def _load_tools(self) -> List[FunctionTool]:
        """动态加载 tools.py"""
        try:
            import importlib.util
            spec = importlib.util.spec_from_file_location(
                "tools", self.dir / "tools.py"
            )
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            return getattr(module, "TOOLS", [])
        except Exception as e:
            logger.warning(f"Failed to load tools from {self.dir}: {e}")
            return []
    
    def _load_prompts(self) -> dict:
        """动态加载 prompts.py"""
        try:
            import importlib.util
            spec = importlib.util.spec_from_file_location(
                "prompts", self.dir / "prompts.py"
            )
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            return {
                "system": getattr(module, "SYSTEM_PROMPT", ""),
                "examples": getattr(module, "EXAMPLES", [])
            }
        except Exception as e:
            logger.warning(f"Failed to load prompts from {self.dir}: {e}")
            return {}
    
    @property
    def name(self) -> str:
        return self.metadata.get("name", self.dir.name)
    
    @property
    def triggers(self) -> List[str]:
        return self.metadata.get("triggers", [])


class SkillManager:
    """Skill 管理器"""
    
    def __init__(self, skills_dir: Optional[Path] = None):
        self.skills_dir = skills_dir or Path(__file__).parent
        self.skills: Dict[str, Skill] = {}
        self._load_all_skills()
    
    def _load_all_skills(self):
        """加载所有 skills"""
        if not self.skills_dir.exists():
            logger.warning(f"Skills directory not found: {self.skills_dir}")
            return
        
        for skill_dir in self.skills_dir.iterdir():
            if skill_dir.is_dir() and (skill_dir / "skill.json").exists():
                try:
                    skill = Skill(skill_dir)
                    self.skills[skill.name] = skill
                    logger.info(f"Loaded skill: {skill.name}")
                except Exception as e:
                    logger.error(f"Failed to load skill {skill_dir.name}: {e}")
    
    def get_skill_by_trigger(self, text: str) -> Optional[Skill]:
        """根据触发词查找 skill"""
        text_lower = text.lower()
        for skill in self.skills.values():
            for trigger in skill.triggers:
                if trigger.lower() in text_lower:
                    return skill
        return None
    
    def get_all_tools(self) -> List[FunctionTool]:
        """获取所有 skill 的工具"""
        tools = []
        for skill in self.skills.values():
            tools.extend(skill.tools)
        return tools
    
    def get_all_prompts(self) -> str:
        """获取所有 skill 的系统提示词"""
        prompts = []
        for skill in self.skills.values():
            if skill.prompts.get("system"):
                prompts.append(skill.prompts["system"])
        return "\n\n".join(prompts)
    
    def list_skills(self) -> List[dict]:
        """列出所有 skills"""
        return [
            {
                "name": skill.name,
                "description": skill.metadata.get("description", ""),
                "triggers": skill.triggers,
                "tools_count": len(skill.tools)
            }
            for skill in self.skills.values()
        ]


# 全局实例
skill_manager = SkillManager()
```

## 集成到 agent.py

```python
# kuma_claw/agent.py（修改部分）

from .skills.skill_manager import skill_manager

# 加载基础工具
TOOLS = [
    FunctionTool(func=web_search),
    FunctionTool(func=get_current_time),
    FunctionTool(func=echo_message),
    FunctionTool(func=remember),
    FunctionTool(func=recall),
    FunctionTool(func=forget),
    FunctionTool(func=get_memory_stats),
]

# 添加所有 skill 的工具
skill_tools = skill_manager.get_all_tools()
TOOLS.extend(skill_tools)
logger.info(f"已加载 {len(skill_tools)} 个 skill 工具")

# 修改系统提示词
def get_system_instruction(channel: str = "telegram") -> str:
    """构建系统提示词"""
    base_prompt = build_system_prompt()
    
    # 添加 skill 提示词
    skill_prompts = skill_manager.get_all_prompts()
    
    # 添加工具说明
    tools_prompt = f"""

## 可用工具 (Tools)

### 基础工具
...

### Skills 工具
{skill_prompts}
"""
    
    return base_prompt + tools_prompt
```

## CLI 命令扩展

```python
# kuma_claw/cli.py（新增命令）

@cli.command()
def skills():
    """列出所有已安装的 skills"""
    from .skills.skill_manager import skill_manager
    
    skills_list = skill_manager.list_skills()
    
    if not skills_list:
        click.echo("暂无已安装的 skills")
        return
    
    click.echo("🦞 已安装的 Skills：\n")
    for skill in skills_list:
        click.echo(f"📦 {skill['name']}")
        click.echo(f"   描述: {skill['description']}")
        click.echo(f"   触发词: {', '.join(skill['triggers'])}")
        click.echo(f"   工具数: {skill['tools_count']}")
        click.echo()

@cli.command()
@click.argument('skill_name')
def skill_info(skill_name: str):
    """查看 skill 详细信息"""
    from .skills.skill_manager import skill_manager
    
    skill = skill_manager.skills.get(skill_name)
    if not skill:
        click.echo(f"❌ Skill '{skill_name}' 未找到")
        return
    
    click.echo(f"📦 {skill.name}")
    click.echo(f"版本: {skill.metadata.get('version', 'N/A')}")
    click.echo(f"描述: {skill.metadata.get('description', 'N/A')}")
    click.echo(f"作者: {skill.metadata.get('author', 'N/A')}")
    click.echo(f"\n触发词: {', '.join(skill.triggers)}")
    click.echo(f"\n工具列表:")
    for tool in skill.tools:
        click.echo(f"  - {tool.name}: {tool.description}")
```

## 安装流程

```bash
# 1. 创建 skills 目录
mkdir -p kuma_claw/skills

# 2. 添加示例 skill（weather）
cd kuma_claw/skills
mkdir weather
# 创建 skill.json, tools.py, prompts.py, __init__.py

# 3. 测试
kuma-claw skills  # 列出所有 skills
kuma-claw skill-info weather  # 查看详细信息

# 4. 使用
# 用户发送："东京今天天气怎么样？"
# 自动触发 weather skill，调用 get_current_weather 工具
```

## 与 OpenClaw Skills 的差异

| 特性 | OpenClaw | Kuma Claw |
|------|----------|-----------|
| **语言** | TypeScript | Python |
| **工具系统** | 自定义工具调用 | Google ADK FunctionTool |
| **提示词格式** | SKILL.md (Markdown) | skill.json + prompts.py |
| **加载方式** | 按 description 匹配 | 按触发词匹配 |
| **社区支持** | ClawHub | 可扩展为 PyPI 包 |

## 优势

1. **轻量级** - 最小依赖，快速启动
2. **原生集成** - 与 Google ADK 无缝配合
3. **易于开发** - 标准 Python 模块结构
4. **灵活扩展** - 支持本地 + 远程 skill
5. **社区友好** - 可打包为 PyPI 包分发

## 下一步

1. **实现 skill_manager.py**
2. **创建示例 skills**（weather, github, browser）
3. **修改 agent.py** 集成 skill_manager
4. **扩展 CLI 命令**
5. **编写文档和测试**

## 可选增强

- **Skill Hub**：类似 ClawHub 的在线 skill 市场
- **Hot Reload**：开发模式自动重载 skill
- **Skill Dependencies**：支持 skill 间的依赖管理
- **Sandboxing**：隔离 skill 执行环境（安全）

---

**设计目标：让 kuma-claw 的 skills 系统简单、强大、易扩展。** 🦞
