# Kuma Claw 记忆系统

## 架构

```
┌─────────────────────────────────────────────────┐
│  MemoryManager（管理器）                         │
│  - remember() / forget() / recall()             │
│  - 会话管理                                      │
│  - 文件加载                                      │
└────────────────────┬────────────────────────────┘
                     ↓
┌─────────────────────────────────────────────────┐
│  MemoryStore（存储层）                           │
│  - SQLite（元数据）                              │
│  - FTS5（全文搜索）                              │
│  - 向量索引（嵌入向量）                          │
└─────────────────────────────────────────────────┘
```

## 参考

设计参考了 OpenClaw 的记忆系统：

| 功能 | OpenClaw | Kuma Claw |
|------|----------|----------|
| 存储 | SQLite + 向量 | SQLite + FTS5 |
| 搜索 | 混合（向量+FTS） | FTS（向量可选） |
| 分块 | Markdown chunking | 整体存储 |
| 会话 | JSONL + 预热 | SQLite |
| 同步 | 增量 + Watch | 手动 |

## 使用

```python
from memory import memory_manager

# 记住
memory_manager.remember("用户喜欢简洁", source="preference")

# 搜索
results = memory_manager.search("用户喜欢")
for r in results:
    print(r.entry.content, r.score)

# 会话
memory_manager.add_session_message("session-123", "user", "你好")
history = memory_manager.get_session_history("session-123")
```

## 工具

Agent 可用的记忆工具：

- `remember(content, source)` - 记住
- `recall(query, limit)` - 回忆
- `forget(content_pattern)` - 忘记
- `get_memory_stats()` - 统计

## 向量搜索（可选）

启用向量搜索：

```python
from memory import memory_manager, GeminiEmbeddingProvider

provider = GeminiEmbeddingProvider(api_key="...")
memory_manager.set_embedding_provider(provider)
```

## 存储

```
~/.kuma-claw/
├── config.json      # 配置
├── secrets.json     # 密钥
└── memory.db        # 记忆数据库
```
