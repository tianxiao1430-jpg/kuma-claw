# Kuma Claw

[![Deploy to GCP](https://storage.googleapis.com/cloudrun/button.svg)](https://deploy.cloud.run/?git_repo=https://github.com/tianxiao1430-jpg/kuma-claw.git)

[English](./README.md) | [简体中文](./README.zh.md) | [日本語](./README.ja.md)

> 🦞 基于 Google ADK 的智能办公助手

---

## 👥 招募开发者

**我们正在寻找志同道合的开发者一起打造开源 AI 助手！**

### 🎯 项目愿景

让每个小微企业/个人开发者都能拥有**零成本部署**的 AI 办公助手，一键部署到 GCP 免费额度。

### 🔧 技术栈

| 领域 | 技术 |
|------|------|
| **后端** | Python 3.11+, Google ADK, FastAPI |
| **部署** | GCP Cloud Run, Docker, Cloud Build |
| **渠道** | Telegram Bot API, Slack API |
| **AI** | Google Generative AI (Gemini) |
| **工具** | Git, pytest, GitHub Actions |

### 🙋 需要的角色

- **后端开发** - Python/API 开发经验
- **前端开发** - Web UI/管理面板（计划中）
- **Skills 开发者** - 编写新技能模块
- **文档/翻译** - 中/日/英多语言支持
- **测试** - 单元测试/集成测试

### 🎁 你能获得什么

- 📈 开源项目经验（可写进简历）
- 🤝 认识优秀的开发者
- 💡 学习 AI Agent/GCP 部署实战
- 🌟 GitHub 贡献记录
- ☕ 线上技术分享会

### 📮 如何加入

1. **Fork 仓库** 开始贡献代码
2. **加入讨论** - 在 Issues 中参与讨论
3. **联系我们** - tianxiao1430@gmail.com 或直接在 Issue 留言

**新手？** 查看标记为 [`good first issue`](https://github.com/tianxiao1430-jpg/kuma-claw/issues?q=is%3Aissue+is%3Aopen+label%3A%22good+first+issue%22) 的任务开始！

---

## 🚀 一键部署

**5 分钟部署到 GCP 免费额度！**

- [📖 GCP 部署指南](docs/DEPLOYMENT.md) - 详细部署步骤
- [![Deploy to GCP](https://storage.googleapis.com/cloudrun/button.svg)](https://deploy.cloud.run/?git_repo=https://github.com/tianxiao1430-jpg/kuma-claw.git)

## 📚 文档

详细文档已移至 [`docs/`](docs/) 目录：

- **[📦 部署指南](docs/DEPLOYMENT.md)** - GCP 一键部署（新增）
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

- **多渠道支持**: Telegram, Slack, Web (Discord, WhatsApp 计划中)
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

查看 [CONTRIBUTING.md](CONTRIBUTING.md) 了解详细的贡献指南。

## 📄 许可证

Apache License 2.0

## 🔗 相关链接

- [GitHub 仓库](https://github.com/tianxiao1430-jpg/kuma-claw)
- [Issue 追踪](https://github.com/tianxiao1430-jpg/kuma-claw/issues)
- [文档中心](docs/)

---

**版本**: v0.1.1
**状态**: 🚀 开发中
