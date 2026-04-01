# Kuma Claw

[![Deploy to GCP](https://storage.googleapis.com/cloudrun/button.svg)](https://deploy.cloud.run/?git_repo=https://github.com/tianxiao1430-jpg/kuma-claw.git)

[English](./README.md) | [简体中文](./README.zh.md) | [日本語](./README.ja.md)

> 🦞 AI Office Assistant built on Google ADK

---

## 👥 Recruiting Developers

**We're looking for developers to join our open-source AI assistant project!**

### 🎯 Project Vision

Enable every small business and indie developer to deploy an **AI office assistant at zero cost** with one-click deployment to GCP free tier.

### 🔧 Tech Stack

| Area | Technology |
|------|------------|
| **Backend** | Python 3.11+, Google ADK, FastAPI |
| **Deployment** | GCP Cloud Run, Docker, Cloud Build |
| **Channels** | Telegram Bot API, Slack API |
| **AI** | Google Generative AI (Gemini) |
| **Tools** | Git, pytest, GitHub Actions |

### 🙋 Roles We Need

- **Backend Developers** - Python/API development experience
- **Frontend Developers** - Web UI/Admin panel (planned)
- **Skills Developers** - Build new skill modules
- **Documentation/Translation** - Chinese/Japanese/English support
- **Testers** - Unit/Integration testing

### 🎁 What You Get

- 📈 Open-source project experience (great for resume)
- 🤝 Meet talented developers
- 💡 Learn AI Agent/GCP deployment hands-on
- 🌟 GitHub contribution record
- ☕ Online tech sharing sessions

### 📮 How to Join

1. **Fork the repo** and start contributing
2. **Join discussions** - Participate in Issues
3. **Contact us** - tianxiao1430@gmail.com or comment on Issues

**New?** Start with [`good first issue`](https://github.com/tianxiao1430-jpg/kuma-claw/issues?q=is%3Aissue+is%3Aopen+label%3A%22good+first+issue%22) tasks!

---

## 🚀 One-Click Deployment

**Deploy to GCP free tier in 5 minutes!**

- [📖 GCP Deployment Guide](docs/DEPLOYMENT.md) - Detailed steps
- [![Deploy to GCP](https://storage.googleapis.com/cloudrun/button.svg)](https://deploy.cloud.run/?git_repo=https://github.com/tianxiao1430-jpg/kuma-claw.git)

## 📚 Documentation

Full documentation in [`docs/`](docs/) directory:

- **[📦 Deployment Guide](docs/DEPLOYMENT.md)** - GCP one-click deployment (NEW)
- **[Delivery Report](docs/DELIVERY.md)** - Project delivery summary
- **[Quick Reference](docs/QUICK_REFERENCE.md)** - Commands and API cheat sheet
- **[Integration Guide](docs/INTEGRATION_GUIDE.md)** - How to integrate Kuma Claw
- **[Skills System](docs/SKILLS_README.md)** - Skills system documentation
- **[Security Policy](SECURITY.md)** - Security best practices

## 🚀 Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
cp .env.example .env
# Edit .env file with your API keys
```

### 3. Run

```bash
# CLI mode
python -m kuma_claw.main

# Or run as service
python -m kuma_claw.gateway
```

## 🎯 Core Features

- **Multi-Channel**: Telegram, Slack, Web (Discord, WhatsApp planned)
- **Skills System**: Modular skill extension mechanism
- **Memory System**: Long-term memory and context management
- **Google Workspace**: Gmail, Calendar, Sheets, Docs integration
- **Web Search**: DuckDuckGo real-time search

## 📁 Project Structure

```
.
├── kuma_claw/              # Core code
│   ├── agent.py           # Agent definition
│   ├── channels/          # Channel implementations
│   ├── tools/             # Toolset
│   ├── skills/            # Skills system
│   └── prompts/           # Prompt templates
├── tests/                  # Test suite
├── docs/                   # Documentation
├── .github/workflows/     # CI/CD
├── requirements.txt        # Dependencies
└── pytest.ini             # Test configuration
```

## 🧪 Testing

```bash
# Run all tests
pytest

# Run tests with coverage report
pytest --cov=kuma_claw --cov-report=html
```

## 🤝 Contributing

Contributions welcome:
- New Skills
- Bug fixes
- Documentation improvements
- Feature requests

See [CONTRIBUTING.md](CONTRIBUTING.md) for detailed guidelines.

## 📄 License

Apache License 2.0

## 🔗 Links

- [GitHub Repo](https://github.com/tianxiao1430-jpg/kuma-claw)
- [Issue Tracker](https://github.com/tianxiao1430-jpg/kuma-claw/issues)
- [Documentation](docs/)

---

**Version**: v0.1.1
**Status**: 🚀 In Development
