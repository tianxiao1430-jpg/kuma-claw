# Kuma Claw Skills System 🦞

> 模块化、可扩展的技能系统，为 kuma-claw 添加无限可能

## 📦 安装

### 方法 1：使用打包文件

```bash
# 将 kuma-skills-system.skill 放到 kuma-claw/skills/ 目录
mkdir -p kuma_claw/skills
cp kuma-skills-system.skill kuma_claw/skills/
cd kuma_claw/skills
unzip kuma-skills-system.skill
```

### 方法 2：直接使用源码

```bash
# 复制整个 skills 目录到项目中
cp -r skills/kuma-skills-system kuma_claw/skills/
```

## 🚀 快速开始

### 1. 列出已安装的 Skills

```bash
kuma-claw skills
```

### 2. 查看详细信息

```bash
kuma-claw skill-info kuma-skills-system
```

### 3. 创建新 Skill

```bash
# 使用提供的脚本
python3 kuma_claw/skills/kuma-skills-system/scripts/init_skill.py my-skill

# 或手动创建
mkdir -p kuma_claw/skills/my-skill
# 创建 skill.json, tools.py, prompts.py, __init__.py
```

## 📚 目录结构

```
kuma_claw/skills/
├── kuma-skills-system/          # Skills 系统本身
│   ├── SKILL.md                 # 使用指南
│   ├── scripts/
│   │   ├── skill_manager.py     # 核心管理器
│   │   └── init_skill.py        # 初始化脚本
│   └── references/
│       ├── example_weather_skill/  # 完整示例
│       └── skill_schema.md      # Schema 文档
└── weather/                     # 示例：天气 skill
    ├── skill.json
    ├── tools.py
    ├── prompts.py
    └── __init__.py
```

## 🎯 核心功能

### 1. 自动发现和加载

Skills 系统会自动扫描 `kuma_claw/skills/` 目录，加载所有符合规范的 skill。

### 2. 触发词匹配

根据用户消息自动匹配对应的 skill：

```
用户："东京今天天气怎么样？"
→ 匹配 weather skill
→ 调用 get_current_weather(city="东京")
```

### 3. 工具集成

基于 Google ADK FunctionTool，无缝集成到 agent 工具链：

```python
from google.adk.tools import FunctionTool

def get_current_weather(city: str) -> str:
    """获取天气信息"""
    # 实现
    pass

TOOLS = [FunctionTool(func=get_current_weather)]
```

### 4. 提示词注入

Skill 的系统提示词会自动注入到 agent 的系统指令中：

```python
# 在 skill 的 prompts.py 中定义
SYSTEM_PROMPT = """
## 天气查询能力
你可以通过 get_current_weather 工具获取实时天气...
"""
```

## 🔧 开发新 Skill

### 步骤 1：初始化

```bash
python3 scripts/init_skill.py my-skill
```

### 步骤 2：定义元数据

编辑 `skill.json`:

```json
{
  "name": "my-skill",
  "version": "1.0.0",
  "description": "我的自定义 skill",
  "triggers": ["关键词1", "关键词2"],
  "dependencies": []
}
```

### 步骤 3：实现工具

编辑 `tools.py`:

```python
from google.adk.tools import FunctionTool

def my_tool(param: str) -> str:
    """工具描述"""
    # 实现逻辑
    return "结果"

TOOLS = [FunctionTool(func=my_tool)]
```

### 步骤 4：添加提示词

编辑 `prompts.py`:

```python
SYSTEM_PROMPT = """
## 我的能力
说明如何使用这个 skill...
"""

EXAMPLES = [
    {
        "user": "示例输入",
        "assistant": "示例回复",
        "tool_call": "my_tool(param='value')"
    }
]
```

### 步骤 5：测试

```bash
# 重新加载 skills
kuma-claw skills-reload

# 测试触发
kuma-claw test "包含触发词的消息"
```

## 📖 API 参考

### SkillManager

```python
from kuma_claw.skills import SkillManager

# 初始化
manager = SkillManager(skills_dir="kuma_claw/skills")

# 列出 skills
skills = manager.list_skills()

# 根据触发词查找
skill = manager.get_skill_by_trigger("天气怎么样")

# 获取所有工具
tools = manager.get_all_tools()

# 获取所有提示词
prompts = manager.get_all_prompts()

# 重新加载 skill
manager.reload_skill("weather")
```

### Skill 类

```python
from kuma_claw.skills import Skill
from pathlib import Path

# 加载 skill
skill = Skill(Path("kuma_claw/skills/weather"))

# 访问属性
print(skill.name)        # "weather"
print(skill.triggers)    # ["天气", "weather", ...]
print(skill.tools)       # [FunctionTool, ...]
print(skill.prompts)     # {"system": "...", "examples": [...]}
```

## 🌟 最佳实践

### 工具设计
- ✅ 单一职责：每个工具只做一件事
- ✅ 清晰描述：帮助 agent 理解何时使用
- ✅ 错误处理：返回用户友好的错误信息
- ✅ 类型提示：使用 Python type hints

### 提示词设计
- ✅ 具体示例：展示如何使用工具
- ✅ 上下文说明：何时/为什么使用
- ✅ 简洁明了：只包含关键信息

### 触发词设计
- ✅ 覆盖变体：包含同义词和常见短语
- ✅ 避免重叠：不同 skill 的触发词不应重复
- ✅ 测试覆盖：验证触发词匹配用户语言模式

## 🐛 故障排除

### Skill 未加载

```bash
# 检查 skill 结构
ls -la kuma_claw/skills/my-skill/

# 查看日志
kuma-claw logs --skills
```

### 工具未调用

- 验证触发词是否匹配用户消息
- 检查工具描述是否清晰
- 确认 skill 在 `kuma_claw/skills/` 目录中

### 导入错误

```bash
# 安装依赖
pip install -r kuma_claw/skills/my-skill/requirements.txt
```

## 📦 示例 Skills

### Weather Skill
完整的天气查询 skill，包含：
- 当前天气查询
- 天气预报
- 中英文支持

查看：`references/example_weather_skill/`

### 创建你自己的
参考 `skill_schema.md` 和示例 skill，创建符合你需求的自定义 skill！

## 🤝 贡献

欢迎贡献新的 skill 或改进现有系统！

1. Fork 项目
2. 创建 feature branch
3. 提交 pull request

## 📄 许可证

Apache License 2.0 - 详见 [LICENSE](LICENSE)

---

**Kuma Claw Skills System** - 让 AI Agent 拥有无限可能 🦞
