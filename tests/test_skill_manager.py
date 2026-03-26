"""
tests/test_skill_manager.py
SkillManager のユニットテスト（Issue #104）

カバー範囲:
- Skill._safe_import() ホワイトリスト制御（Issue #103 修正の検証）
- SkillManager の初期化・スキル検索
- get_skill_by_trigger() トリガーワード検索
- list_skills() 一覧取得
"""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from kuma_claw.skills.skill_manager import (
    SecurityError,
    Skill,
    SkillManager,
    SkillValidationError,
)

# ============================================================
# テスト用スキルディレクトリ作成ヘルパー
# スキル名は小文字英数字とハイフンのみ使用可能
# ============================================================


def create_test_skill_dir(base: Path, name: str, triggers: list, code: str = "") -> Path:
    """テスト用スキルディレクトリを作成する"""
    skill_dir = base / name
    skill_dir.mkdir(parents=True, exist_ok=True)
    metadata = {
        "name": name,
        "version": "1.0.0",
        "description": f"{name} test skill",
        "triggers": triggers,
        "author": "test",
    }
    (skill_dir / "skill.json").write_text(json.dumps(metadata))
    if code:
        (skill_dir / "tools.py").write_text(code)
    return skill_dir


# ============================================================
# Skill._safe_import のテスト（Issue #103 セキュリティ修正の検証）
# ============================================================


class TestSafeImport:
    """Skill._safe_import() ホワイトリスト制御のテスト"""

    @pytest.fixture
    def skill_instance(self, tmp_path):
        """テスト用 Skill インスタンス（最小構成）"""
        # スキル名は小文字英数字とハイフンのみ
        skill_dir = create_test_skill_dir(tmp_path, "test-skill", ["test"])
        return Skill(skill_dir)

    def test_allowed_module_json(self, skill_instance):
        """ホワイトリストのモジュール（json）は正常にインポートできる"""
        mod = skill_instance._safe_import("json")
        assert mod is not None
        assert hasattr(mod, "loads")

    def test_allowed_module_re(self, skill_instance):
        """ホワイトリストのモジュール（re）は正常にインポートできる"""
        mod = skill_instance._safe_import("re")
        assert mod is not None
        assert hasattr(mod, "compile")

    def test_allowed_module_math(self, skill_instance):
        """ホワイトリストのモジュール（math）は正常にインポートできる"""
        mod = skill_instance._safe_import("math")
        assert mod is not None
        assert hasattr(mod, "sqrt")

    def test_allowed_module_datetime(self, skill_instance):
        """ホワイトリストのモジュール（datetime）は正常にインポートできる"""
        mod = skill_instance._safe_import("datetime")
        assert mod is not None

    def test_blocked_os_module(self, skill_instance):
        """os モジュールはブロックされる（サンドボックス逃逸防止）"""
        with pytest.raises(ImportError, match="not allowed"):
            skill_instance._safe_import("os")

    def test_blocked_sys_module(self, skill_instance):
        """sys モジュールはブロックされる"""
        with pytest.raises(ImportError, match="not allowed"):
            skill_instance._safe_import("sys")

    def test_blocked_subprocess(self, skill_instance):
        """subprocess モジュールはブロックされる"""
        with pytest.raises(ImportError, match="not allowed"):
            skill_instance._safe_import("subprocess")

    def test_blocked_shutil(self, skill_instance):
        """shutil モジュールはブロックされる"""
        with pytest.raises(ImportError, match="not allowed"):
            skill_instance._safe_import("shutil")

    def test_blocked_socket(self, skill_instance):
        """socket モジュールはブロックされる"""
        with pytest.raises(ImportError, match="not allowed"):
            skill_instance._safe_import("socket")

    def test_blocked_builtins(self, skill_instance):
        """builtins モジュールはブロックされる"""
        with pytest.raises(ImportError, match="not allowed"):
            skill_instance._safe_import("builtins")

    def test_obfuscated_os_blocked(self, skill_instance):
        """文字列結合によるモジュール名の難読化もブロックされる"""
        with pytest.raises(ImportError, match="not allowed"):
            skill_instance._safe_import("o" + "s")


# ============================================================
# Skill の基本テスト
# ============================================================


class TestSkill:
    """Skill クラスの基本テスト"""

    def test_skill_loads_metadata(self, tmp_path):
        """skill.json のメタデータが正しく読み込まれる"""
        skill_dir = create_test_skill_dir(tmp_path, "my-skill", ["hello"])
        skill = Skill(skill_dir)
        assert skill.name == "my-skill"
        assert "hello" in skill.triggers

    def test_skill_description(self, tmp_path):
        """スキルの説明が metadata に読み込まれる"""
        skill_dir = create_test_skill_dir(tmp_path, "desc-skill", [])
        skill = Skill(skill_dir)
        assert skill.metadata.get("description") is not None

    def test_skill_tools_default_empty(self, tmp_path):
        """tools.py がない場合、tools は空リスト"""
        skill_dir = create_test_skill_dir(tmp_path, "no-tools-skill", [])
        skill = Skill(skill_dir)
        assert skill.tools == []

    def test_skill_invalid_name_raises_error(self, tmp_path):
        """スキル名にアンダースコアや大文字が含まれる場合はエラー"""
        skill_dir = tmp_path / "InvalidSkill"
        skill_dir.mkdir()
        metadata = {
            "name": "InvalidSkill",
            "version": "1.0.0",
            "description": "invalid",
            "triggers": [],
        }
        (skill_dir / "skill.json").write_text(json.dumps(metadata))
        with pytest.raises(SkillValidationError):
            Skill(skill_dir)

    def test_skill_dangerous_code_raises_security_error(self, tmp_path):
        """危険なコード（eval）を含む tools.py はロード時にエラーになる"""
        dangerous_code = """
def hack():
    eval("__import__('os').system('id')")
"""
        skill_dir = create_test_skill_dir(tmp_path, "dangerous-skill", [], code=dangerous_code)
        with pytest.raises((SecurityError, SkillValidationError, Exception)):
            Skill(skill_dir)


# ============================================================
# SkillManager のテスト
# ============================================================


class TestSkillManager:
    """SkillManager の基本テスト"""

    @pytest.fixture
    def empty_skills_dir(self, tmp_path):
        """スキルが存在しない空ディレクトリ"""
        d = tmp_path / "skills"
        d.mkdir()
        return d

    @pytest.fixture
    def manager_empty(self, empty_skills_dir):
        """スキルなし SkillManager"""
        return SkillManager(skills_dir=empty_skills_dir)

    @pytest.fixture
    def manager_with_skills(self, tmp_path):
        """スキルあり SkillManager"""
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()
        create_test_skill_dir(skills_dir, "weather-skill", ["weather", "forecast"])
        create_test_skill_dir(skills_dir, "search-skill", ["search", "find", "lookup"])
        create_test_skill_dir(skills_dir, "calc-skill", ["calculate", "compute"])
        return SkillManager(skills_dir=skills_dir)

    def test_empty_manager_has_no_skills(self, manager_empty):
        """空ディレクトリでは skills が空"""
        assert len(manager_empty.skills) == 0

    def test_manager_loads_skills(self, manager_with_skills):
        """スキルが正しく読み込まれる"""
        assert len(manager_with_skills.skills) == 3
        assert "weather-skill" in manager_with_skills.skills
        assert "search-skill" in manager_with_skills.skills

    def test_get_skill_by_trigger_match(self, manager_with_skills):
        """トリガーワードでスキルを検索できる"""
        result = manager_with_skills.get_skill_by_trigger("what is the weather today")
        assert result is not None
        assert result.name == "weather-skill"

    def test_get_skill_by_trigger_english(self, manager_with_skills):
        """英語トリガーで検索できる"""
        result = manager_with_skills.get_skill_by_trigger("search for python tutorials")
        assert result is not None
        assert result.name == "search-skill"

    def test_get_skill_by_trigger_no_match(self, manager_with_skills):
        """マッチしない場合は None を返す"""
        result = manager_with_skills.get_skill_by_trigger("completely unrelated input xyz123")
        assert result is None

    def test_get_skill_by_trigger_case_insensitive(self, manager_with_skills):
        """英語トリガーは大文字小文字を区別しない"""
        result = manager_with_skills.get_skill_by_trigger("SEARCH this topic")
        assert result is not None

    def test_list_skills_returns_list(self, manager_with_skills):
        """list_skills() がリストを返す"""
        skills = manager_with_skills.list_skills()
        assert isinstance(skills, list)
        assert len(skills) == 3

    def test_list_skills_contains_name(self, manager_with_skills):
        """list_skills() の各要素に name が含まれる"""
        skills = manager_with_skills.list_skills()
        names = [s.get("name") for s in skills]
        assert "weather-skill" in names

    def test_get_all_tools_returns_list(self, manager_with_skills):
        """get_all_tools() がリストを返す"""
        tools = manager_with_skills.get_all_tools()
        assert isinstance(tools, list)

    def test_nonexistent_skills_dir(self, tmp_path):
        """存在しないディレクトリでも例外が発生しない"""
        nonexistent = tmp_path / "nonexistent"
        manager = SkillManager(skills_dir=nonexistent)
        assert len(manager.skills) == 0

    def test_get_all_prompts_returns_string(self, manager_with_skills):
        """get_all_prompts() が文字列を返す"""
        prompts = manager_with_skills.get_all_prompts()
        assert isinstance(prompts, str)
