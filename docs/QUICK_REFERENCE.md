# Kuma Claw Skills - 快速参考卡

## 🚀 一键开始

```bash
# 安装
cp kuma-skills-system.skill kuma_claw/skills/ && cd kuma_claw/skills && unzip kuma-skills-system.skill

# 集成（参考 INTEGRATION_GUIDE.md）

# 测试
python3 test_skills.py
```

## 📦 Skill 结构

```
my-skill/
├── skill.json      # 元数据（触发词、依赖）
├── tools.py        # 工具实现（FunctionTool）
├── prompts.py      # 系统提示词
└── __init__.py     # 导出接口
```

## 🎯 第一个 Skill: skill-creator

### 触发词
```
创建skill, 新建skill, skill创建, create skill,
skill-creator, 初始化skill, 开发skill, 编写skill,
验证skill, 打包skill, skill开发, skill设计
```

### 使用示例

```python
# 创建新 skill
init_skill(skill_name="github-analyzer")

# 验证 skill
validate_skill(skill_name="github-analyzer")

# 打包 skill
package_skill(skill_name="github-analyzer", output_dir="dist")
```

### 自然语言触发

```
用户: "创建一个分析GitHub的skill"
→ 匹配 skill-creator
→ 调用 init_skill(skill_name="github-analyzer")
→ 返回: ✅ Skill 'github-analyzer' 初始化成功
```

## 📝 skill.json 模板

```json
{
  "name": "my-skill",
  "version": "1.0.0",
  "description": "功能描述",
  "triggers": ["触发词1", "触发词2"],
  "author": "your-name",
  "dependencies": [],
  "tools": [
    {
      "name": "tool_name",
      "description": "工具描述",
      "parameters": {
        "param": {
          "type": "string",
          "description": "参数说明",
          "required": true
        }
      }
    }
  ]
}
```

## 🔧 tools.py 模板

```python
from google.adk.tools import FunctionTool

def my_tool(param: str) -> str:
    """工具描述

    Args:
        param: 参数说明

    Returns:
        结果字符串
    """
    # 实现
    return "结果"

TOOLS = [FunctionTool(func=my_tool)]
```

## 💬 prompts.py 模板

```python
SYSTEM_PROMPT = """
## 我的能力

说明如何使用这个 skill...

### 可用工具
- **my_tool**: 工具说明

### 使用示例
```python
my_tool(param="value")
```
"""

EXAMPLES = [
    {
        "user": "示例输入",
        "assistant": "示例回复",
        "tool_call": "my_tool(param='value')"
    }
]
```

## 🎯 触发词设计规则

### ✅ 好的触发词
```json
{
  "triggers": [
    "天气", "weather", "气温", "预报", "温度",
    "查天气", "今天天气", "weather forecast"
  ]
}
```

### ❌ 不好的触发词
```json
{
  "triggers": [
    "信息", "数据", "帮助", "查询"
  ]
}
```

**原因**: 过于宽泛，容易误触发

## 🛠️ 常用命令

```bash
# 列出 skills
kuma-claw skills

# 查看详情
kuma-claw skill-info skill-creator

# 创建新 skill（通过 CLI）
kuma-claw skill-init my-skill

# 测试触发
kuma-claw test "创建一个skill"
```

## 🐛 常见问题

### Skill 未加载
```bash
# 检查结构
ls -la kuma_claw/skills/my-skill/
# 必须有: skill.json, tools.py, prompts.py, __init__.py
```

### 工具未调用
- ✅ 检查触发词是否匹配用户消息
- ✅ 检查工具描述是否清晰
- ✅ 验证 SYSTEM_PROMPT 中的使用说明

### 导入错误
```bash
# 安装依赖
pip install -r kuma_claw/skills/my-skill/requirements.txt
```

### 验证失败
```python
# 使用 validate_skill 检查
from kuma_claw.skills.skill_creator.tools import validate_skill
result = validate_skill(skill_name="my-skill")
print(result)
```

## 📚 文档导航

| 文档 | 用途 | 大小 |
|------|------|------|
| **QUICK_REFERENCE.md** | 本文档（快速参考） | 2.4KB |
| **SKILLS_README.md** | 完整文档和 API | 4.2KB |
| **INTEGRATION_GUIDE.md** | 集成步骤 | 6.8KB |
| **skill_schema.md** | Schema 参考 | 3.5KB |
| **SUMMARY.md** | 完成总结 | 4.5KB |

## 🔗 API 快速参考

```python
from kuma_claw.skills import SkillManager

# 初始化
manager = SkillManager()

# 列出 skills
skills = manager.list_skills()

# 查找 skill
skill = manager.get_skill_by_trigger("创建skill")

# 获取工具
tools = manager.get_all_tools()

# 获取提示词
prompts = manager.get_all_prompts()

# 重新加载
manager.reload_skill("skill-creator")
```

## 💡 最佳实践

### 工具设计
- ✅ 单一职责：每个工具只做一件事
- ✅ 清晰描述：帮助 agent 理解何时使用
- ✅ 类型提示：使用 Python type hints
- ✅ 错误处理：返回用户友好的错误消息

### 提示词设计
- ✅ 具体示例：展示如何使用工具
- ✅ 上下文说明：何时/为什么使用
- ✅ 简洁明了：只包含关键信息

### 触发词设计
- ✅ 覆盖变体：包含同义词和常见短语
- ✅ 避免重叠：不同 skill 的触发词不应重复
- ✅ 测试覆盖：验证触发词匹配用户语言模式

## 🎉 示例：创建 GitHub 分析 Skill

```python
# 1. 初始化
init_skill(skill_name="github-analyzer")
# → 创建目录和文件

# 2. 编辑 skill.json
{
  "triggers": ["GitHub", "分析仓库", "repo analysis"],
  "tools": [
    {
      "name": "analyze_repo",
      "description": "分析 GitHub 仓库"
    }
  ]
}

# 3. 实现 tools.py
def analyze_repo(repo_url: str) -> str:
    """分析 GitHub 仓库"""
    # 实现逻辑
    return "分析结果"

TOOLS = [FunctionTool(func=analyze_repo)]

# 4. 编写 prompts.py
SYSTEM_PROMPT = """
## GitHub 分析能力

你可以通过 analyze_repo 工具深度分析 GitHub 仓库。
"""

# 5. 验证和打包
validate_skill(skill_name="github-analyzer")
package_skill(skill_name="github-analyzer")
```

## 🚀 下一步

1. **测试 skill-creator** - 发送 "创建一个skill" 消息
2. **创建你的第一个 skill** - 使用 init_skill() 初始化
3. **实现工具** - 编写具体的工具函数
4. **完善提示词** - 编写清晰的 SYSTEM_PROMPT
5. **打包分发** - 使用 package_skill() 分享

---

**快速参考 v1.1** | 第一个 Skill: skill-creator | 更多细节见完整文档
