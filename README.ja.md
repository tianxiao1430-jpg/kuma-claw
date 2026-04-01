# Kuma Claw

[![Deploy to GCP](https://storage.googleapis.com/cloudrun/button.svg)](https://deploy.cloud.run/?git_repo=https://github.com/tianxiao1430-jpg/kuma-claw.git)

[简体中文](./README.md) | [English](./README.en.md) | [日本語](./README.ja.md)

> 🦞 Google ADK をベースにした AI オフィスアシスタント

---

## 👥 開発者募集

**オープンソース AI アシスタントプロジェクトで一緒に開発してくれる仲間を募集中！**

### 🎯 プロジェクトのビジョン

**「ゼロコストでワンクリックデプロイ」**を実現する、小規模企業・個人開発者向け AI オフィスアシスタント。GCP 無料枠にデプロイ可能。

### 🔧 技術スタック

| 分野 | 技術 |
|------|------|
| **バックエンド** | Python 3.11+, Google ADK, FastAPI |
| **デプロイ** | GCP Cloud Run, Docker, Cloud Build |
| **チャネル** | Telegram Bot API, Slack API |
| **AI** | Google Generative AI (Gemini) |
| **ツール** | Git, pytest, GitHub Actions |

### 🙋 募集役割

- **バックエンド開発** - Python/API 開発経験者
- **フロントエンド開発** - Web UI/管理画面（計画中）
- **Skills 開発** - 新しいスキルモジュール作成
- **ドキュメント/翻訳** - 中/日/英マルチ言語対応
- **テスター** - 単体テスト/結合テスト

### 🎁 得られるもの

- 📈 オープンソースプロジェクト経験（履歴書に書ける）
- 🤝 優秀な開発者とのネットワーク
- 💡 AI エージェント/GCP デプロイの实战経験
- 🌟 GitHub 貢献記録
- ☕ オンライン技術共有セッション

### 📮 参加方法

1. **リポジトリを Fork** して貢献開始
2. **議論に参加** - Issues でディスカッション
3. **お問い合わせ** - tianxiao1430@gmail.com または Issue でコメント

**初心者？** [`good first issue`](https://github.com/tianxiao1430-jpg/kuma-claw/issues?q=is%3Aissue+is%3Aopen+label%3A%22good+first+issue%22) のタスクから始めよう！

---

## 🚀 ワンクリックデプロイ

**GCP 無料枠で 5 分デプロイ！**

- [📖 GCP デプロイガイド](docs/DEPLOYMENT.md) - 詳細手順
- [![Deploy to GCP](https://storage.googleapis.com/cloudrun/button.svg)](https://deploy.cloud.run/?git_repo=https://github.com/tianxiao1430-jpg/kuma-claw.git)

## 📚 ドキュメント

詳細ドキュメントは [`docs/`](docs/) ディレクトリにあります：

- **[📦 デプロイガイド](docs/DEPLOYMENT.md)** - GCP ワンクリックデプロイ（新設）
- **[デリバリーレポート](docs/DELIVERY.md)** - プロジェクト納品まとめ
- **[クイックリファレンス](docs/QUICK_REFERENCE.md)** - コマンド・API チートシート
- **[統合ガイド](docs/INTEGRATION_GUIDE.md)** - Kuma Claw の統合方法
- **[スキルシステム](docs/SKILLS_README.md)** - Skills システム使用说明
- **[セキュリティポリシー](SECURITY.md)** - セキュリティベストプラクティス

## 🚀 クイックスタート

### 1. 依存関係インストール

```bash
pip install -r requirements.txt
```

### 2. 環境設定

```bash
cp .env.example .env
# .env ファイルを編集して API キーを設定
```

### 3. 実行

```bash
# CLI モード
python -m kuma_claw.main

# またはサービスとして実行
python -m kuma_claw.gateway
```

## 🎯 主要機能

- **マルチチャネル**: Telegram, Slack, Web (Discord, WhatsApp 計画中)
- **Skills システム**: モジュール式スキル拡張メカニズム
- **メモリシステム**: 長期記憶とコンテキスト管理
- **Google Workspace**: Gmail, Calendar, Sheets, Docs 統合
- **Web 検索**: DuckDuckGo リアルタイム検索

## 📁 プロジェクト構造

```
.
├── kuma_claw/              # コアコード
│   ├── agent.py           # Agent 定義
│   ├── channels/          # チャネル実装
│   ├── tools/             # ツールセット
│   ├── skills/            # Skills システム
│   └── prompts/           # プロンプトテンプレート
├── tests/                  # テストスイート
├── docs/                   # ドキュメント
├── .github/workflows/     # CI/CD
├── requirements.txt        # 依存関係
└── pytest.ini             # テスト設定
```

## 🧪 テスト

```bash
# すべてのテストを実行
pytest

# カバレッジレポート付きで実行
pytest --cov=kuma_claw --cov-report=html
```

## 🤝 貢献

歓迎する貢献：
- 新しい Skills
- バグ修正
- ドキュメント改善
- 機能リクエスト

詳細は [CONTRIBUTING.md](CONTRIBUTING.md) をご覧ください。

## 📄 ライセンス

Apache License 2.0

## 🔗 リンク

- [GitHub リポジトリ](https://github.com/tianxiao1430-jpg/kuma-claw)
- [Issue トラッカー](https://github.com/tianxiao1430-jpg/kuma-claw/issues)
- [ドキュメント](docs/)

---

**バージョン**: v0.1.1
**ステータス**: 🚀 開発中
