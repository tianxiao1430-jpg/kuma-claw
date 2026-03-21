"""
Kuma Claw - 动态格式注入
=======================

根据渠道类型自动注入相应的消息格式规范。
"""

# ============================================
# 渠道格式规范
# ============================================

CHANNEL_FORMATS: dict[str, str] = {
    "telegram": """
## Telegram 消息格式规范

Telegram 支持 MarkdownV2 和 HTML，但我们推荐使用简化的 Markdown：

### 文本格式
- *bold* - 粗体（单个星号）
- _italic_ - 斜体（下划线）
- `code` - 行内代码（反引号）
- ```code block``` - 代码块（三个反引号）
- [link](url) - 链接

### 注意事项
- **不要**使用 ## 标题（Telegram 不渲染）
- **不要**使用 **双星号**（用单星号）
- 支持表情符号 🦞
- 支持列表（• 或数字）

### 示例
```
*重要通知*
会议时间改为 _下午 3 点_

• 议题 1
• 议题 2

代码示例：
`print("hello")`
```
""",
    "slack": """
## Slack 消息格式规范

Slack 使用 mrkdwn（类 Markdown）格式：

### 文本格式
- *bold* - 粗体（单个星号）
- _italic_ - 斜体（下划线）
- `code` - 行内代码（反引号）
- ```code block``` - 代码块（三个反引号）
- <@U123> - 用户 mention
- <#C123|channel> - 频道链接
- <http://url|text> - 链接

### 注意事项
- **不要**使用 ## 标题（Slack 不渲染）
- **不要**使用 **双星号**（用单星号）
- 支持 emoji :thumbsup:
- 支持列表（• 或数字）

### 示例
```
*重要更新*

Hi <@U123>, 请查看 <#C456|general>

• 新功能
• Bug 修复
```
""",
    "discord": """
## Discord 消息格式规范

Discord 支持 Markdown：

### 文本格式
- **bold** - 粗体（双星号）
- *italic* - 斜体（单星号）
- `code` - 行内代码（反引号）
- ```code block``` - 代码块（三个反引号）
- ~~strikethrough~~ - 删除线
- <@123456789> - 用户 mention
- <#123456789> - 频道链接

### 注意事项
- **可以**使用 ## 标题
- **使用双星号**加粗
- 支持 emoji 🦞
- 支持引用（> 前缀）

### 示例
```
## 重要通知

**用户们好！**

> 这是一个引用

• 项目 1
• 项目 2
```
""",
    "web": """
## Web UI 消息格式规范

Web UI 支持完整 Markdown：

### 文本格式
- **bold** - 粗体（双星号）
- *italic* - 斜体（单星号）
- ~~strikethrough~~ - 删除线
- `code` - 行内代码
- ```code block``` - 代码块
- [link](url) - 链接

### 结构化元素
- # ## ### 标题
- > 引用
- - 无序列表
- 1. 有序列表
- | 表格 |

### 注意事项
- **使用双星号**加粗
- **可以**使用多级标题
- 支持复杂的 Markdown 语法

### 示例
```
## 项目报告

**日期**: 2024-01-15

### 进展

1. 完成功能 A
2. 修复 Bug B

[查看详情](http://example.com)
```
""",
    "whatsapp": """
## WhatsApp 消息格式规范

WhatsApp 使用简化的格式：

### 文本格式
- *bold* - 粗体（单个星号）
- _italic_ - 斜体（下划线）
- ~strikethrough~ - 删除线
- ```code``` - 代码（三个反引号）

### 注意事项
- **不要**使用 ## 标题
- **不要**使用 **双星号**
- **不要**使用 [link](url) 格式（直接贴 URL）
- 支持表情符号 🦞

### 示例
```
*重要通知*

会议改为 _明天 10 点_

• 议题 1
• 议题 2

链接：https://example.com
```
""",
    "console": """
## 控制台输出格式规范

控制台支持 ANSI 颜色和基本格式：

### 文本格式
- 使用换行分隔内容
- 使用缩进表示层级
- 使用符号增强可读性（✅ ❌ ⚠️ 💡）

### 注意事项
- **不要**使用 Markdown
- **不要**使用 ## 标题
- 使用表格对齐数据
- 保持简洁

### 示例
```
✅ 任务完成

结果：
  • 文件 1
  • 文件 2

耗时: 2.5s
```
""",
}


# ============================================
# 获取格式规范
# ============================================


def get_format_prompt(channel: str) -> str:
    """获取指定渠道的格式规范

    Args:
        channel: 渠道名称（telegram, slack, discord, web, whatsapp, console）

    Returns:
        格式规范文本
    """
    channel_lower = channel.lower().strip()

    # 直接匹配
    if channel_lower in CHANNEL_FORMATS:
        return CHANNEL_FORMATS[channel_lower]

    # 别名匹配
    aliases = {
        "tg": "telegram",
        "tele": "telegram",
        "slack": "slack",
        "discord": "discord",
        "web": "web",
        "http": "web",
        "whatsapp": "whatsapp",
        "wa": "whatsapp",
        "console": "console",
        "terminal": "console",
        "cli": "console",
    }

    normalized = aliases.get(channel_lower, "console")
    return CHANNEL_FORMATS.get(normalized, CHANNEL_FORMATS["console"])


def get_supported_channels() -> list[str]:
    """获取支持的渠道列表"""
    return list(CHANNEL_FORMATS.keys())


# ============================================
# 格式转换工具（可选）
# ============================================


def convert_markdown_to_channel(text: str, target_channel: str) -> str:
    """将标准 Markdown 转换为目标渠道格式

    这是一个简单的转换，主要用于兜底。
    主要转换：
    - **双星号** → *单星号* (Telegram/Slack/WhatsApp)
    - ## 标题 → 粗体文本

    Args:
        text: 原始 Markdown 文本
        target_channel: 目标渠道

    Returns:
        转换后的文本
    """
    import re

    # 需要单星号的渠道
    single_star_channels = ["telegram", "slack", "whatsapp"]

    if target_channel in single_star_channels:
        # **bold** → *bold*
        text = re.sub(r"\*\*(.+?)\*\*", r"*\1*", text)

        # ## 标题 → *标题*
        text = re.sub(r"^## (.+)$", r"*\1*", text, flags=re.MULTILINE)
        text = re.sub(r"^### (.+)$", r"*\1*", text, flags=re.MULTILINE)

        # [link](url) → url (WhatsApp)
        if target_channel == "whatsapp":
            text = re.sub(r"\[(.+?)\]\((.+?)\)", r"\2", text)

    return text


def strip_internal_tags(text: str) -> str:
    """移除 <internal> 标签（用于发送给用户前）

    Args:
        text: 原始文本（可能包含 <internal> 标签）

    Returns:
        清理后的文本
    """
    import re

    # 移除 <internal>...</internal> 块
    return re.sub(r"<internal>.*?</internal>", "", text, flags=re.DOTALL).strip()


def extract_internal_content(text: str) -> tuple[str, str]:
    """提取 <internal> 内容和用户可见内容

    Args:
        text: 原始文本

    Returns:
        (internal_content, visible_content)
    """
    import re

    # 提取 internal 内容
    internal_match = re.search(r"<internal>(.*?)</internal>", text, flags=re.DOTALL)
    internal = internal_match.group(1).strip() if internal_match else ""

    # 提取可见内容
    visible = strip_internal_tags(text)

    # 防止返回完全为空导致渠道（如 Telegram）发送失败
    if not visible.strip():
        visible = "（处理完毕，本次 AI 仅执行了内部思考或未输出可见文本）"

    return internal, visible


# ============================================
# 便捷函数
# ============================================


def inject_format_prompt(base_prompt: str, channel: str) -> str:
    """将格式规范注入到基础提示词中

    Args:
        base_prompt: 基础系统提示词
        channel: 渠道名称

    Returns:
        完整的系统提示词
    """
    format_prompt = get_format_prompt(channel)
    return f"{base_prompt}\n\n{format_prompt}"


if __name__ == "__main__":
    # 测试
    print("支持的渠道:", get_supported_channels())
    print("\n" + "=" * 60)
    print("Telegram 格式规范:")
    print("=" * 60)
    print(get_format_prompt("telegram"))

    # 测试 internal 标签
    test_text = """
<internal>
用户要查询订单，我需要调用 API
</internal>

您的订单已发货！
"""

    internal, visible = extract_internal_content(test_text)
    print("\n" + "=" * 60)
    print("Internal 内容:", internal)
    print("Visible 内容:", visible)
