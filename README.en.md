# ADK Claw 🦞

[简体中文](./README.md) | [English](./README.en.md) | [日本語](./README.ja.md)

> The first open-source AI Agent platform built on native Google ADK

## Features

- ✅ **Native ADK** - Built with Google Agent Development Kit
- ✅ **Multi-Model Support** - Gemini / GPT / Claude / DeepSeek / Ollama
- ✅ **Multi-Channel** - Slack / Telegram (more coming soon)
- ✅ **Local-First** - Zero cost, data stays local
- ✅ **Interactive Setup** - OpenClaw-style configuration wizard
- ✅ **Web Config UI** - No manual config file editing
- ✅ **OAuth Support** - Google Workspace integration

## Quick Start

### Option 1: pip install (Recommended)

```bash
pip install adk-claw
adk-claw init
```

### Option 2: Install from Source

```bash
git clone https://github.com/tianxiao1430-jpg/kuma-claw.git
cd kuma-claw
pip install -e .
adk-claw init
```

### Setup Wizard

After running `adk-claw init`, you'll enter an interactive configuration:

```
🦞 ADK Claw - Intelligent Agent Platform

📋 Checking environment...
✅ Python 3.12.0

📦 Checking dependencies...
  ✅ google-adk
  ✅ slack-bolt
  ✅ python-telegram-bot
  ✅ fastapi

🔑 API Configuration
Configure at least one API Key

Google API Key [not configured]: ********************************
✅ Google API Key saved

📱 Channel Configuration
Configure at least one channel

Telegram: ❌ Not configured
Configure Telegram? [y/N]: y
Telegram Bot Token: ********************************
✅ Telegram configured

🤖 Model Configuration
 1  gemini-3.1-flash   Google Gemini 3.1 Flash (recommended)
 2  gemini-3.1-pro     Google Gemini 3.1 Pro
 3  gpt-4o             OpenAI GPT-4o
 4  claude-3-5-sonnet  Anthropic Claude 3.5 Sonnet

Select model (current: gemini-3.1-flash) [1]: 1
✅ Model set to gemini-3.1-flash

🎉 Installation successful

✅ Initialization complete!

Next steps:
  adk-claw run --web      Start Web UI
  adk-claw run --telegram Start Telegram Bot
  adk-claw run --all      Start all services
```

## CLI Commands

| Command | Description | Similar to OpenClaw |
|---------|-------------|---------------------|
| `adk-claw init` | Initialize configuration | `openclaw setup` |
| `adk-claw config` | Configuration wizard | `openclaw configure` |
| `adk-claw doctor` | Health check | `openclaw doctor` |
| `adk-claw run` | Start services | `openclaw gateway` |
| `adk-claw version` | Show version | `openclaw --version` |

### Detailed Usage

```bash
# Initialization
adk-claw init                  # Interactive
adk-claw init --non-interactive

# Configuration
adk-claw config                # All settings
adk-claw config --section api  # API only
adk-claw config --section channels  # Channels only
adk-claw config --section model     # Model only

# Health check
adk-claw doctor

# Run
adk-claw run --web             # Web UI (localhost:8080)
adk-claw run --telegram        # Telegram Bot
adk-claw run --slack           # Slack Bot
adk-claw run --all             # All services
adk-claw run --web --port 3000 # Custom port
```

## 📁 Project Structure

```
.
├── adk_claw/              # Core code
│   ├── agent.py           # Agent definition
│   ├── gateway/           # Gateway architecture
│   │   ├── adapters/      # Channel adapters (Telegram, Web)
│   │   └── __init__.py
│   ├── prompts/           # Prompt templates
│   │   ├── identity.py    # Identity definition
│   │   ├── soul.py        # Core personality
│   │   └── user.py        # User configuration
│   ├── cli.py             # CLI entry point
│   ├── config.py          # Configuration management
│   ├── memory.py          # Memory system
│   ├── web_ui.py          # Web configuration UI
│   ├── telegram_handler.py # Telegram integration
│   └── slack_handler.py   # Slack integration
├── tests/                  # Test suite
├── docs/                   # Documentation
└── requirements.txt        # Dependencies
```

## Channel Configuration

### Telegram

1. Search @BotFather on Telegram
2. Send `/newbot`
3. Follow the prompts to create
4. Copy the Token

```bash
adk-claw config --section channels
# Select Telegram configuration, paste Token
```

### Slack

1. Visit https://api.slack.com/apps
2. Create New App → From scratch
3. **OAuth & Permissions** → Add:
   - `app_mentions:read`
   - `chat:write`
   - `channels:history`
4. **Socket Mode** → Enable → Generate App Token
5. **Event Subscriptions** → `app_mention`
6. Install to Workspace
7. Copy Tokens

```bash
adk-claw config --section channels
# Select Slack configuration, paste Bot Token and App Token
```

## Switch Models

```bash
adk-claw config --section model
```

Or edit `~/.adk-claw/config.json`:

```json
{
  "model": "gemini-3.1-flash"
}
```

Supported models:
- `gemini-3.1-flash` (recommended, free)
- `gemini-3.1-flash-lite-preview` (ultra-low cost)
- `gemini-3.1-pro`
- `gpt-4o`
- `claude-3-5-sonnet`
- `deepseek-chat`
- `ollama/llama3.1` (local)

## Add Tools

Edit `agent.py`:

```python
def my_tool(param: str) -> str:
    """Tool description"""
    return "result"

TOOLS.append(FunctionTool(func=my_tool))
```

## Architecture

```
┌─────────────────────────────────────────────┐
│  CLI (adk-claw init/config/run)             │
└────────────────┬────────────────────────────┘
                 ↓
┌─────────────────────────────────────────────┐
│  Web UI (localhost:8080)                    │
│  - Configure API Keys                       │
│  - OAuth authentication                     │
└────────────────┬────────────────────────────┘
                 ↓
┌─────────────────────────────────────────────┐
│  ADK Claw Core                              │
│  - Google ADK Agent                         │
│  - Multi-channel adapters                   │
└────────────────┬────────────────────┬───────┘
                 ↓                    ↓
    Slack (Socket)      Telegram (Polling)
```

## Comparison with Alternatives

| Aspect | ADK Claw | OpenClaw | PocketPaw |
|--------|----------|----------|-----------|
| Foundation | Native ADK | Anthropic | Multi-backend |
| Multi-model | ✅ 100+ | ❌ Claude only | ✅ |
| Google ecosystem | ✅ Deep integration | ⚠️ Requires config | ⚠️ Fake ADK |
| Local deployment | ✅ Fully local | ✅ | ✅ |
| Installation experience | ✅ Interactive | ✅ Interactive | ⚠️ Manual |
| Open source | ✅ MIT | ✅ | ✅ |

## Roadmap

- [x] MVP - Slack/Telegram support
- [x] Web configuration UI
- [x] Multi-model support
- [x] Memory system (SQLite + FTS)
- [x] CLI setup wizard
- [x] Web search tool (DuckDuckGo)
- [ ] Vector search (embeddings)
- [x] Image understanding (Telegram support)
- [ ] Image understanding (Slack)
- [ ] More tools (Gmail/Calendar/Drive)
- [ ] Cloud Run deployment
- [ ] More channels (Discord/WhatsApp)

## Memory System

ADK Claw has a built-in memory system that can remember and recall information:

```
User: Remember that I like concise replies
Bot: ✅ Remembered: You like concise replies

User: What do I like?
Bot: 📚 Relevant memories:
- You like concise replies
```

### Storage Location

```
~/.adk-claw/
├── config.json      # Configuration
├── secrets.json     # Secrets
└── memory.db        # Memory database
```

## Development

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Code formatting
ruff format .

# Type checking
mypy .
```

## Contributing

Contributions welcome! See [CONTRIBUTING.md](CONTRIBUTING.md)

## License

MIT

---

**ADK Claw** - The first native ADK Agent platform 🦞
