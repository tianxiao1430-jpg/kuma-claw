# ADK Claw 🦞

[简体中文](./README.md) | [English](./README.en.md) | [日本語](./README.ja.md)

> ネイティブ Google ADK で構築された最初のオープンソース AI Agent プラットフォーム

## 特徴

- ✅ **ネイティブ ADK** - Google Agent Development Kit を使用
- ✅ **マルチモデル対応** - Gemini / GPT / Claude / DeepSeek / Ollama
- ✅ **マルチチャネル** - Slack / Telegram（さらに追加予定）
- ✅ **ローカルファースト** - ゼロコスト、データはローカルに保持
- ✅ **対話型セットアップ** - OpenClaw スタイルの設定ウィザード
- ✅ **Web 設定 UI** - 手動での設定ファイル編集不要
- ✅ **OAuth 対応** - Google Workspace 統合

## クイックスタート

### 方法 1: pip インストール（推奨）

```bash
pip install adk-claw
adk-claw init
```

### 方法 2: ソースからインストール

```bash
git clone https://github.com/tianxiao1430-jpg/kuma-claw.git
cd kuma-claw
pip install -e .
adk-claw init
```

### セットアップウィザード

`adk-claw init` を実行すると、対話型設定が開始されます：

```
🦞 ADK Claw - インテリジェント Agent プラットフォーム

📋 環境をチェック中...
✅ Python 3.12.0

📦 依存関係をチェック中...
  ✅ google-adk
  ✅ slack-bolt
  ✅ python-telegram-bot
  ✅ fastapi

🔑 API 設定
少なくとも 1 つの API Key を設定してください

Google API Key [未設定]: ********************************
✅ Google API Key が保存されました

📱 チャネル設定
少なくとも 1 つのチャネルを設定してください

Telegram: ❌ 未設定
Telegram を設定しますか？ [y/N]: y
Telegram Bot Token: ********************************
✅ Telegram が設定されました

🤖 モデル設定
 1  gemini-3.1-flash   Google Gemini 3.1 Flash (推奨)
 2  gemini-3.1-pro     Google Gemini 3.1 Pro
 3  gpt-4o             OpenAI GPT-4o
 4  claude-3-5-sonnet  Anthropic Claude 3.5 Sonnet

モデルを選択 (現在: gemini-3.1-flash) [1]: 1
✅ モデルが gemini-3.1-flash に設定されました

🎉 インストール成功

✅ 初期化完了！

次のステップ:
  adk-claw run --web      Web UI を起動
  adk-claw run --telegram Telegram Bot を起動
  adk-claw run --all      すべてのサービスを起動
```

## CLI コマンド

| コマンド | 説明 | OpenClaw と同様 |
|----------|------|-----------------|
| `adk-claw init` | 設定を初期化 | `openclaw setup` |
| `adk-claw config` | 設定ウィザード | `openclaw configure` |
| `adk-claw doctor` | ヘルスチェック | `openclaw doctor` |
| `adk-claw run` | サービス起動 | `openclaw gateway` |
| `adk-claw version` | バージョン表示 | `openclaw --version` |

### 詳細な使用方法

```bash
# 初期化
adk-claw init                  # 対話型
adk-claw init --non-interactive

# 設定
adk-claw config                # すべての設定
adk-claw config --section api  # API のみ
adk-claw config --section channels  # チャネルのみ
adk-claw config --section model     # モデルのみ

# ヘルスチェック
adk-claw doctor

# 実行
adk-claw run --web             # Web UI (localhost:8080)
adk-claw run --telegram        # Telegram Bot
adk-claw run --slack           # Slack Bot
adk-claw run --all             # すべてのサービス
adk-claw run --web --port 3000 # カスタムポート
```

## 📁 プロジェクト構造

```
.
├── adk_claw/              # コアコード
│   ├── agent.py           # Agent 定義
│   ├── gateway/           # Gateway アーキテクチャ
│   │   ├── adapters/      # チャネルアダプター (Telegram, Web)
│   │   └── __init__.py
│   ├── prompts/           # プロンプトテンプレート
│   │   ├── identity.py    # アイデンティティ定義
│   │   ├── soul.py        # コアパーソナリティ
│   │   └── user.py        # ユーザー設定
│   ├── cli.py             # CLI エントリーポイント
│   ├── config.py          # 設定管理
│   ├── memory.py          # メモリシステム
│   ├── web_ui.py          # Web 設定 UI
│   ├── telegram_handler.py # Telegram 統合
│   └── slack_handler.py   # Slack 統合
├── tests/                  # テストスイート
├── docs/                   # ドキュメント
└── requirements.txt        # 依存関係
```

## チャネル設定

### Telegram

1. Telegram で @BotFather を検索
2. `/newbot` を送信
3. 指示に従って作成
4. トークンをコピー

```bash
adk-claw config --section channels
# Telegram 設定を選択し、トークンを貼り付け
```

### Slack

1. https://api.slack.com/apps にアクセス
2. Create New App → From scratch
3. **OAuth & Permissions** → 追加:
   - `app_mentions:read`
   - `chat:write`
   - `channels:history`
4. **Socket Mode** → Enable → App Token を生成
5. **Event Subscriptions** → `app_mention`
6. Install to Workspace
7. トークンをコピー

```bash
adk-claw config --section channels
# Slack 設定を選択し、Bot Token と App Token を貼り付け
```

## モデルの切り替え

```bash
adk-claw config --section model
```

または `~/.adk-claw/config.json` を編集:

```json
{
  "model": "gemini-3.1-flash"
}
```

対応モデル:
- `gemini-3.1-flash`（推奨、無料）
- `gemini-3.1-flash-lite-preview`（超低コスト）
- `gemini-3.1-pro`
- `gpt-4o`
- `claude-3-5-sonnet`
- `deepseek-chat`
- `ollama/llama3.1`（ローカル）

## ツールの追加

`agent.py` を編集:

```python
def my_tool(param: str) -> str:
    """ツールの説明"""
    return "結果"

TOOLS.append(FunctionTool(func=my_tool))
```

## アーキテクチャ

```
┌─────────────────────────────────────────────┐
│  CLI (adk-claw init/config/run)             │
└────────────────┬────────────────────────────┘
                 ↓
┌─────────────────────────────────────────────┐
│  Web UI (localhost:8080)                    │
│  - API Keys の設定                          │
│  - OAuth 認証                               │
└────────────────┬────────────────────────────┘
                 ↓
┌─────────────────────────────────────────────┐
│  ADK Claw Core                              │
│  - Google ADK Agent                         │
│  - マルチチャネルアダプター                   │
└────────────────┬────────────────────┬───────┘
                 ↓                    ↓
    Slack (Socket)      Telegram (Polling)
```

## 他のソリューションとの比較

| 側面 | ADK Claw | OpenClaw | PocketPaw |
|------|----------|----------|-----------|
| 基盤技術 | ネイティブ ADK | Anthropic | マルチバックエンド |
| マルチモデル | ✅ 100+ | ❌ Claude のみ | ✅ |
| Google エコシステム | ✅ 深い統合 | ⚠️ 設定必要 | ⚠️ 偽 ADK |
| ローカルデプロイ | ✅ 完全ローカル | ✅ | ✅ |
| インストール体験 | ✅ 対話型 | ✅ 対話型 | ⚠️ 手動 |
| オープンソース | ✅ MIT | ✅ | ✅ |

## ロードマップ

- [x] MVP - Slack/Telegram サポート
- [x] Web 設定 UI
- [x] マルチモデルサポート
- [x] メモリシステム（SQLite + FTS）
- [x] CLI セットアップウィザード
- [x] Web 検索ツール (DuckDuckGo)
- [ ] ベクトル検索（埋め込み）
- [x] 画像理解（Telegram サポート）
- [ ] 画像理解（Slack）
- [ ] その他のツール（Gmail/Calendar/Drive）
- [ ] Cloud Run デプロイ
- [ ] その他のチャネル（Discord/WhatsApp）

## メモリシステム

ADK Claw には組み込みのメモリシステムがあり、情報を記憶して呼び出すことができます：

```
ユーザー: 私は簡潔な返信が好きだと覚えておいて
Bot: ✅ 記憶しました: あなたは簡潔な返信が好きです

ユーザー: 私は何が好きですか？
Bot: 📚 関連する記憶:
- あなたは簡潔な返信が好きです
```

### 保存場所

```
~/.adk-claw/
├── config.json      # 設定
├── secrets.json     # シークレット
└── memory.db        # メモリデータベース
```

## 開発

```bash
# 開発依存関係をインストール
pip install -e ".[dev]"

# テストを実行
pytest

# コードフォーマット
ruff format .

# 型チェック
mypy .
```

## 貢献

貢献を歓迎します！[CONTRIBUTING.md](CONTRIBUTING.md) をご覧ください

## ライセンス

MIT

---

**ADK Claw** - 最初のネイティブ ADK Agent プラットフォーム 🦞
