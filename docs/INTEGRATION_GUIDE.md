# Kuma Claw Skills 系统集成指南

## 概述

本指南说明如何将 Skills 系统集成到现有的 kuma-claw 项目中。

## 步骤 1：复制 Skills 系统

```bash
# 将 skills 系统复制到项目中
cp -r /tmp/kuma-claw/skills/kuma-skills-system kuma_claw/skills/

# 或者使用打包文件
mkdir -p kuma_claw/skills
cp kuma-skills-system.skill kuma_claw/skills/
cd kuma_claw/skills && unzip kuma-skills-system.skill
```

## 步骤 2：修改 agent.py

### 2.1 导入 SkillManager

在 `kuma_claw/agent.py` 顶部添加：

```python
from .skills.kuma-skills-system.scripts.skill_manager import skill_manager
```

### 2.2 加载 Skill 工具

在 `TOOLS` 列表定义后添加：

```python
# 现有基础工具
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
```

### 2.3 修改系统提示词

修改 `get_system_instruction()` 函数：

```python
def get_system_instruction(channel: str = "telegram") -> str:
    """构建系统提示词（支持动态格式注入）"""
    from .prompts import build_system_prompt
    from .channels.formats import get_format_prompt, inject_format_prompt

    base_prompt = build_system_prompt()

    # 获取所有 skill 的提示词
    skill_prompts = skill_manager.get_all_prompts()

    # 添加工具说明
    tools_prompt = f"""

## 可用工具 (Tools)

### 基础工具
- **get_current_time**: 获取当前时间
- **web_search**: 通过 DuckDuckGo 搜索网络获取实时信息
- **remember/recall/forget**: 记忆管理工具

### Google Workspace 工具
...

### Skills 工具
{skill_prompts}

## 工具使用原则
...
"""

    # 组合提示词
    import datetime
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    time_prompt = f"\n\n## 系统信息\n当前时间：{now_str}\n"

    full_prompt = base_prompt + time_prompt + tools_prompt

    # 动态注入格式规范
    full_prompt = inject_format_prompt(full_prompt, channel)

    return full_prompt
```

## 步骤 3：扩展 CLI 命令

在 `kuma_claw/cli.py` 中添加新命令：

```python
@cli.command()
def skills():
    """列出所有已安装的 skills"""
    from .skills.kuma-skills-system.scripts.skill_manager import skill_manager

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
@click.argument("skill_name")
def skill_info(skill_name: str):
    """查看 skill 详细信息"""
    from .skills.kuma-skills-system.scripts.skill_manager import skill_manager

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


@cli.command()
@click.argument("skill_name")
def skill_reload(skill_name: str):
    """重新加载指定 skill"""
    from .skills.kuma-skills-system.scripts.skill_manager import skill_manager

    if skill_manager.reload_skill(skill_name):
        click.echo(f"✅ Skill '{skill_name}' 已重新加载")
    else:
        click.echo(f"❌ 重新加载失败")


@cli.command()
@click.argument("skill_name")
def skill_init(skill_name: str):
    """初始化新 skill"""
    import subprocess
    from pathlib import Path

    script_path = (
        Path(__file__).parent
        / "skills/kuma-skills-system/scripts/init_skill.py"
    )
    skills_dir = Path(__file__).parent / "skills"

    subprocess.run(["python3", str(script_path), skill_name, "--skills-dir", str(skills_dir)])
```

## 步骤 4：测试集成

### 4.1 创建测试 Skill

```bash
# 使用初始化脚本
python3 kuma_claw/skills/kuma-skills-system/scripts/init_skill.py test-skill
```

### 4.2 验证加载

```bash
# 列出 skills
kuma-claw skills

# 应该看到：
# 📦 test-skill
#    描述: test-skill skill for kuma-claw
#    触发词: test-skill
#    工具数: 1
```

### 4.3 测试触发

```bash
# 启动 kuma-claw
kuma-claw run --telegram

# 发送测试消息
# "test-skill 示例"
# 应该触发 test-skill，调用 example_tool
```

## 步骤 5：添加示例 Skills

### 5.1 复制天气 Skill

```bash
# 复制示例 weather skill
cp -r kuma_claw/skills/kuma-skills-system/references/example_weather_skill kuma_claw/skills/weather
```

### 5.2 安装依赖

```bash
pip install requests
```

### 5.3 测试天气查询

```bash
# 发送消息
"东京今天天气怎么样？"

# 应该返回：
# "📍 东京: +15°C Partly cloudy"
```

## 目录结构（集成后）

```
kuma_claw/
├── agent.py                  # ✏️ 已修改：集成 skill_manager
├── cli.py                    # ✏️ 已修改：添加 skill 命令
├── skills/                   # 🆕 新增目录
│   ├── kuma-skills-system/   # Skills 系统核心
│   │   ├── SKILL.md
│   │   ├── scripts/
│   │   │   ├── skill_manager.py
│   │   │   └── init_skill.py
│   │   └── references/
│   ├── weather/              # 示例 skill
│   │   ├── skill.json
│   │   ├── tools.py
│   │   ├── prompts.py
│   │   └── __init__.py
│   └── your-custom-skill/    # 你的自定义 skill
└── ...
```

## 验证清单

- [ ] 复制 skills 系统到 `kuma_claw/skills/`
- [ ] 修改 `agent.py` 导入 skill_manager
- [ ] 修改 `agent.py` 加载 skill 工具
- [ ] 修改 `get_system_instruction()` 注入 skill 提示词
- [ ] 在 `cli.py` 添加 skill 管理命令
- [ ] 测试 skill 列表命令：`kuma-claw skills`
- [ ] 测试 skill 触发：发送包含触发词的消息
- [ ] 安装示例 weather skill 并测试

## 高级配置

### 自定义 Skills 目录

```python
# 在 agent.py 中
from pathlib import Path

custom_skills_dir = Path("/path/to/custom/skills")
skill_manager = SkillManager(skills_dir=custom_skills_dir)
```

### 条件加载 Skills

```python
# 只加载特定 skill
skill_manager = SkillManager()
skill_manager.skills = {
    name: skill
    for name, skill in skill_manager.skills.items()
    if name in ["weather", "github"]
}
```

### 动态重载

```python
# 在运行时重新加载所有 skills
skill_manager._load_all_skills()
```

## 故障排除

### 导入错误

```python
# 确保相对导入正确
from .skills.kuma-skills-system.scripts.skill_manager import skill_manager
# 不是：
# from kuma_claw.skills.kuma-skills-system.scripts.skill_manager import skill_manager
```

### 工具未加载

```python
# 检查日志
import logging
logging.basicConfig(level=logging.DEBUG)

# 查看加载的 tools
print(f"Loaded {len(TOOLS)} tools")
print(f"Skill tools: {len(skill_tools)}")
```

### 触发词不工作

```python
# 手动测试触发
from kuma_claw.skills.kuma-skills-system.scripts.skill_manager import skill_manager

test_message = "东京今天天气怎么样？"
skill = skill_manager.get_skill_by_trigger(test_message)
print(f"Matched skill: {skill.name if skill else 'None'}")
```

## 下一步

1. **创建自定义 skills** - 根据你的需求开发新的 skill
2. **优化提示词** - 调整 skill prompts 以提高准确性
3. **分享 skills** - 打包并分享给社区

---

集成完成后，kuma-claw 将拥有强大的模块化技能系统！🦞
