import json
from pathlib import Path

from rich.console import Console
from rich.prompt import Prompt

console = Console()

TRANSLATIONS = {
    "en": {
        "banner_title": "Kuma Claw - Agent Platform",
        "banner_desc": "Based on Google ADK | Multi-model | Local Deployment",
        "env_check": "📋 Checking environment...",
        "dep_check": "📦 Checking dependencies...",
        "missing_dep": "Missing dependencies",
        "run_cmd": "Run",
        "install_missing": "Do you want to install missing dependencies?",
        "installing": "Installing dependencies...",
        "init_done": "✅ Initialization complete!",
        "next_step": "Next steps:",
        "start_web": "Start Web UI",
        "start_tg": "Start Telegram Bot",
        "success": "🎉 Success",
        "python_req": "❌ Python 3.10+ required",
        "not_installed": "Not installed",
    },
    "zh": {
        "banner_title": "Kuma Claw - 智能 Agent 平台",
        "banner_desc": "基于 Google ADK | 多模型支持 | 本地部署",
        "env_check": "📋 检查环境...",
        "dep_check": "📦 检查依赖...",
        "missing_dep": "缺少依赖",
        "run_cmd": "运行",
        "install_missing": "是否安装缺失的依赖？",
        "installing": "安装依赖中...",
        "init_done": "✅ 初始化完成！",
        "next_step": "下一步：",
        "start_web": "启动 Web UI",
        "start_tg": "启动 Telegram Bot",
        "success": "🎉 安装成功",
        "python_req": "❌ 需要 Python 3.10+",
        "not_installed": "未安装",
    },
    "ja": {
        "banner_title": "Kuma Claw - エージェントプラットフォーム",
        "banner_desc": "Google ADK ベース | マルチモデル | ローカルデプロイ",
        "env_check": "📋 環境を確認中...",
        "dep_check": "📦 依存関係を確認中...",
        "missing_dep": "不足している依存関係",
        "run_cmd": "実行",
        "install_missing": "不足している依存関係をインストールしますか？",
        "installing": "依存関係をインストール中...",
        "init_done": "✅ 初期化が完了しました！",
        "next_step": "次のステップ：",
        "start_web": "Web UI を起動",
        "start_tg": "Telegram Bot を起動",
        "success": "🎉 インストール成功",
        "python_req": "❌ Python 3.10+ が必要です",
        "not_installed": "未インストール",
    },
}


class I18nManager:
    def __init__(self):
        self.lang = "zh"
        self.config_dir = Path.home() / ".kuma-claw"
        self.lang_file = self.config_dir / "lang.json"
        self._load_lang()

    def _load_lang(self):
        if self.lang_file.exists():
            try:
                with open(self.lang_file, encoding="utf-8") as f:
                    self.lang = json.load(f).get("lang", "zh")
            except (json.JSONDecodeError, OSError, KeyError):
                pass

    def save_lang(self, lang):
        self.lang = lang
        self.config_dir.mkdir(parents=True, exist_ok=True)
        with open(self.lang_file, "w", encoding="utf-8") as f:
            json.dump({"lang": lang}, f)

    def prompt_language(self):
        console.print("[cyan]1[/cyan]. English")
        console.print("[cyan]2[/cyan]. 中文")
        console.print("[cyan]3[/cyan]. 日本語")
        choice = Prompt.ask(
            "🌐 Select Language / 选择语言 / 言語を選択", choices=["1", "2", "3"], default="2"
        )
        lang_map = {"1": "en", "2": "zh", "3": "ja"}
        self.save_lang(lang_map[choice])
        console.print()

    def t(self, key, default=None):
        return TRANSLATIONS.get(self.lang, TRANSLATIONS["zh"]).get(key, default or key)


i18n = I18nManager()
_ = i18n.t
