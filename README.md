# Kuma Claw

> 🦞 基于 Google ADK 的智能办公助手

## 📚 文档

详细文档已移至 [`docs/`](docs/) 目录：

- **[交付文档](docs/DELIVERY.md)** - 项目交付总结
- **[快速参考](docs/QUICK_REFERENCE.md)** - 常用命令和 API 速查
- **[集成指南](docs/INTEGRATION_GUIDE.md)** - 如何集成 Kuma Claw
- **[技能系统](docs/SKILLS_README.md)** - Skills 系统使用说明
- **[安全策略](SECURITY.md)** - 安全最佳实践

## 🚀 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env 文件，填入必要的 API 密钥
```

### 3. 运行

```bash
# 命令行模式
python -m kuma_claw.main

# 或作为服务运行
python -m kuma_claw.gateway
```

## 🎯 核心功能

- **多渠支持**: Telegram, Slack, Discord, Web, WhatsApp
- **Skills 系统**: 模块化技能扩展机制
- **记忆系统**: 长期记忆和上下文管理
- **Google Workspace**: Gmail, Calendar, Sheets, Docs 集成
- **网络搜索**: DuckDuckGo 实时信息检索

## 📁 项目结构

```
.
├── kuma_claw/              # 核心代码
│   ├── agent.py           # Agent 定义
│   ├── channels/          # 渠道实现
│   ├── tools/             # 工具集
│   ├── skills/            # Skills 系统
│   └── prompts/           # 提示词模板
├── tests/                  # 测试套件
├── docs/                   # 文档
├── .github/workflows/     # CI/CD
├── requirements.txt        # 依赖
└── pytest.ini             # 测试配置
```

## 🧪 测试

```bash
# 运行所有测试
pytest

# 运行测试并生成覆盖率报告
pytest --cov=kuma_claw --cov-report=html
```

## 🤝 贡献

欢迎贡献：
- 新的 Skills
- Bug 修复
- 文档改进
- 功能建议

## 📄 许可证

Apache License 2.0

## 🔗 相关链接

- [GitHub 仓库](https://github.com/tianxiao1430-jpg/kuma-claw)
- [Issue 追踪](https://github.com/tianxiao1430-jpg/kuma-claw/issues)
- [文档中心](docs/)

---

**版本**: v1.0
**状态**: 🚀 开发中
