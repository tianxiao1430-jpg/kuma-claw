# 贡献指南

欢迎参与 Kuma Claw 项目！🎉

无论你是开发者、设计师、文档写作者，还是仅仅想提个建议，我们都欢迎你的参与。

## 🚀 快速开始

### 1. Fork 仓库

点击右上角的 **Fork** 按钮，将仓库复制到你自己的账号。

### 2. 克隆仓库

```bash
git clone https://github.com/YOUR_USERNAME/kuma-claw.git
cd kuma-claw
```

### 3. 安装依赖

```bash
pip install -r requirements.txt
```

### 4. 创建分支

```bash
git checkout -b feat/your-feature-name
```

### 5. 开发 & 测试

```bash
# 运行测试
pytest

# 运行测试并生成覆盖率报告
pytest --cov=kuma_claw --cov-report=html
```

### 6. 提交代码

```bash
git add .
git commit -m "feat: add your feature description"
git push origin feat/your-feature-name
```

### 7. 创建 Pull Request

在 GitHub 上创建 PR，描述你的改动。

---

## 📋 贡献类型

### 🐛 Bug 修复

1. 在 Issues 中搜索是否已有人报告
2. 如果没有，创建一个新的 Issue 描述 Bug
3. 修复后创建 PR，关联 Issue

### ✨ 新功能

1. 先在 Issue 中讨论你的想法
2. 获得反馈后开始开发
3. 提交 PR 时说明功能用途

### 📖 文档改进

- 错别字修复
- 示例代码补充
- 翻译（中文/英文/日文）
- 部署指南完善

### 🎨 技能（Skills）开发

我们鼓励大家贡献自己的 Skills！参考 [`docs/SKILLS_README.md`](docs/SKILLS_README.md)

---

## 📝 代码规范

### Commit 信息格式

```
<type>: <description>

[optional body]

[optional footer]
```

**Type 类型：**
- `feat`: 新功能
- `fix`: Bug 修复
- `docs`: 文档更新
- `style`: 代码格式（不影响功能）
- `refactor`: 重构
- `test`: 测试相关
- `chore`: 构建/工具配置

**示例：**
```
feat: add Telegram channel support

- Implement Telegram bot handler
- Add message parsing logic
- Add unit tests

Closes #123
```

### 代码风格

- 遵循 PEP 8
- 使用 type hints
- 函数添加 docstring

---

## 🧪 测试要求

所有 PR 必须通过 CI 测试：

- ✅ 单元测试通过
- ✅ 代码覆盖率不下降
- ✅ Lint 检查通过

本地运行测试：

```bash
pytest
pytest --cov=kuma_claw --cov-report=html
```

---

## 🤔 需要帮助？

- 💬 在 Issue 中提问
- 📧 邮件联系：tianxiao1430@gmail.com
- 💭 加入讨论（TODO: 添加 Discord/Slack 链接）

---

## 🎯 当前优先任务

查看 [Issues](https://github.com/tianxiao1430-jpg/kuma-claw/issues) 中标记为：
- 🔴 **高优先级** - 核心功能
- 🟡 **中等优先级** - 改进优化
- 🟢 **低优先级** - 锦上添花

特别适合新贡献者的任务标记为 `good first issue`。

---

## 📜 许可证

Apache License 2.0 - 详见 [LICENSE](LICENSE)

---

感谢你的贡献！🙏
