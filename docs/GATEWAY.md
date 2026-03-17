# Kuma Claw Gateway 设计

## 架构概览

```
┌─────────────────────────────────────────────────────────────┐
│                     外部渠道                                 │
│  Telegram | Slack | Discord | WhatsApp | Web UI            │
└────────────┬────────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────────┐
│                    Gateway (核心)                           │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │ Channel     │  │ Session     │  │ Agent       │         │
│  │ Manager     │  │ Manager     │  │ Router      │         │
│  └─────────────┘  └─────────────┘  └─────────────┘         │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │ Auth        │  │ Memory      │  │ Tool        │         │
│  │ Manager     │  │ Manager     │  │ Registry    │         │
│  └─────────────┘  └─────────────┘  └─────────────┘         │
└────────────┬────────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────────┐
│                    Agent Pool                               │
│  Agent A (Gemini) | Agent B (GPT-4) | Agent C (Claude)     │
└─────────────────────────────────────────────────────────────┘
```

## 核心组件

### 1. Channel Manager（渠道管理器）

负责与各平台通信，统一消息格式。

```python
# 统一消息格式
class Message:
    id: str
    channel: str           # telegram, slack, discord, web
    user_id: str
    chat_id: str
    content: str
    timestamp: datetime
    reply_to: Optional[str]
    metadata: dict         # 渠道特有信息
```

### 2. Session Manager（会话管理器）

管理用户会话，支持跨渠道连续对话。

```python
class Session:
    id: str
    user_id: str
    channel: str
    chat_id: str
    agent_id: str          # 当前绑定的 agent
    context: dict          # 会话上下文
    created_at: datetime
    updated_at: datetime
```

### 3. Agent Router（Agent 路由器）

根据规则选择合适的 Agent 处理请求。

```python
# 路由规则
routing_rules = [
    {"channel": "telegram", "agent": "default"},
    {"channel": "slack", "workspace": ".*-dev", "agent": "dev-agent"},
    {"mention": "@analyst", "agent": "analyst"},
    {"keyword": "代码", "agent": "code-agent"},
    {"default": True, "agent": "default"},
]
```

### 4. Memory Manager（记忆管理器）

统一的记忆接口，所有 Agent 共享。

### 5. Tool Registry（工具注册中心）

动态注册和管理工具，供 Agent 调用。

## 数据流

```
1. 用户发送消息（Telegram）
   │
   ▼
2. Telegram Adapter 接收
   → 转换为统一 Message 格式
   │
   ▼
3. Gateway 接收
   → Session Manager 查找/创建会话
   → Auth Manager 验证用户
   │
   ▼
4. Agent Router 选择 Agent
   → 根据路由规则匹配
   → 加载 Agent 配置
   │
   ▼
5. Memory Manager 注入上下文
   → 搜索相关记忆
   → 加载会话历史
   │
   ▼
6. Agent 处理
   → 调用 LLM
   → 执行工具
   → 生成回复
   │
   ▼
7. Gateway 返回
   → 保存会话
   → 记忆存储
   │
   ▼
8. Telegram Adapter 发送回复
```

## API 设计

### WebSocket API（实时通信）

```javascript
// 连接
ws://localhost:19001/gateway

// 发送消息
{
  "type": "message",
  "channel": "telegram",
  "chat_id": "123456",
  "content": "你好"
}

// 接收回复
{
  "type": "reply",
  "message_id": "xxx",
  "content": "你好！有什么可以帮你的？",
  "agent": "default"
}
```

### REST API（管理接口）

```
GET  /health              # 健康检查
GET  /agents              # 列出所有 agents
POST /agents/:id/message  # 直接发送消息给指定 agent
GET  /sessions            # 列出会话
GET  /sessions/:id        # 会话详情
GET  /memory/search       # 搜索记忆
```

## 配置文件

```json
{
  "gateway": {
    "host": "0.0.0.0",
    "port": 19001,
    "secret": "your-secret-key"
  },
  "channels": {
    "telegram": {
      "enabled": true,
      "adapter": "TelegramAdapter",
      "token": "${TELEGRAM_BOT_TOKEN}"
    },
    "slack": {
      "enabled": true,
      "adapter": "SlackAdapter",
      "bot_token": "${SLACK_BOT_TOKEN}",
      "app_token": "${SLACK_APP_TOKEN}"
    },
    "web": {
      "enabled": true,
      "adapter": "WebAdapter",
      "port": 8080
    }
  },
  "agents": {
    "default": {
      "model": "gemini-3.1-flash",
      "system_prompt": "你是一个有用的助手",
      "tools": ["remember", "recall", "web_search"]
    },
    "analyst": {
      "model": "gpt-4o",
      "system_prompt": "你是一个数据分析师",
      "tools": ["remember", "recall", "code_execute"]
    }
  },
  "routing": [
    {"channel": "slack", "agent": "default"},
    {"mention": "@analyst", "agent": "analyst"},
    {"default": true, "agent": "default"}
  ]
}
```

## 启动方式

```bash
# 启动网关
kuma-claw gateway

# 后台运行
kuma-claw gateway --daemon

# 指定配置
kuma-claw gateway --config /path/to/config.json

# 开发模式（热重载）
kuma-claw gateway --dev
```

## 目录结构

```
kuma-claw/
├── gateway/
│   ├── __init__.py
│   ├── server.py          # WebSocket 服务器
│   ├── channel_manager.py # 渠道管理
│   ├── session_manager.py # 会话管理
│   ├── agent_router.py    # Agent 路由
│   ├── auth_manager.py    # 认证管理
│   └── adapters/
│       ├── base.py        # Adapter 基类
│       ├── telegram.py    # Telegram 适配器
│       ├── slack.py       # Slack 适配器
│       └── web.py         # Web 适配器
├── agents/
│   ├── base.py            # Agent 基类
│   └── default.py         # 默认 Agent
└── tools/
    ├── registry.py        # 工具注册中心
    └── builtins.py        # 内置工具
```

## 对比 OpenClaw

| 功能 | Kuma Claw Gateway | OpenClaw Gateway |
|------|------------------|------------------|
| 基础技术 | Python + WebSocket | Node.js + WebSocket |
| Agent 框架 | Google ADK | Anthropic SDK |
| 多渠道 | Telegram/Slack/Web | 15+ 渠道 |
| 配置方式 | JSON + CLI | JSON + CLI |
| 部署 | 本地 / Docker | 本地 / Docker / Cloud |

## 路线图

- [ ] Phase 1: 核心网关框架
  - [ ] WebSocket 服务器
  - [ ] 消息格式定义
  - [ ] 基础路由

- [ ] Phase 2: 渠道适配器
  - [ ] Telegram Adapter
  - [ ] Slack Adapter
  - [ ] Web Adapter

- [ ] Phase 3: Agent 系统
  - [ ] Agent 基类
  - [ ] 动态加载
  - [ ] 工具注册

- [ ] Phase 4: 高级功能
  - [ ] 多 Agent 协作
  - [ ] 会话持久化
  - [ ] 监控面板

---

_设计版本: 0.1.0 | 更新: 2026-03-08_
