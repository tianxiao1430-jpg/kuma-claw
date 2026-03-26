"""
skill-creator - 工具定义（安全增强版）
=====================================
创建和管理 kuma-claw skills 的工具集

安全特性：
- 完整的输入验证
- 路径遍历防护
- 符号链接检测
- 资源限制
"""

import json
import re
import shutil
import tempfile
from pathlib import Path

from google.adk.tools import FunctionTool

# 导入验证函数（如果可用）
try:
    from skills.kuma_skills_system.scripts.skill_manager import (
        RESERVED_NAMES,
        validate_path_safe,
        validate_skill_name,
        validate_version,
    )
except ImportError:
    # 本地定义（fallback）
    RESERVED_NAMES = {
        "test",
        "tmp",
        "temp",
        "skill",
        "skills",
        "kuma-claw",
        "kuma_claw",
        "__pycache__",
        "con",
        "prn",
        "aux",
        "nul",
        "admin",
        "root",
        "system",
        "default",
    }

    def validate_skill_name(skill_name: str) -> tuple[bool, str]:
        if not skill_name:
            return False, "Skill 名称不能为空"
        if len(skill_name) < 2:
            return False, "Skill 名称至少 2 个字符"
        if len(skill_name) > 64:
            return False, "Skill 名称最多 64 字符"
        if not re.match(r"^[a-z0-9-]+$", skill_name):
            return False, "只能包含小写字母、数字和连字符"
        if skill_name.startswith("-") or skill_name.endswith("-"):
            return False, "不能以连字符开头或结尾"
        if skill_name in RESERVED_NAMES:
            return False, f"'{skill_name}' 是保留名称"
        return True, "Valid"

    def validate_version(version: str) -> bool:
        return bool(re.match(r"^\d+\.\d+\.\d+$", version))

    def validate_path_safe(path: Path, allowed_dirs: list[Path]) -> bool:
        try:
            resolved = path.resolve()
            for allowed in allowed_dirs:
                if resolved.is_relative_to(allowed.resolve()):
                    return True
            return False
        except (RuntimeError, ValueError, OSError):
            return False


# ============================================
# 配置
# ============================================

# 允许的输出目录
DEFAULT_ALLOWED_DIRS = [
    Path.cwd(),
    Path.home() / ".kuma-claw",
    Path("/tmp"),
]

# 资源限制
MAX_SKILL_SIZE = 10 * 1024 * 1024  # 10MB
MAX_FILES_COUNT = 100
MAX_FILE_SIZE = 1 * 1024 * 1024  # 1MB


# ============================================
# 工具函数
# ============================================


def init_skill(skill_name: str, skills_dir: str = "kuma_claw/skills") -> str:
    """初始化新 skill 的目录结构和文件

    Args:
        skill_name: Skill 名称（小写字母、数字、连字符，2-64字符）
        skills_dir: Skills 目录路径（默认 kuma_claw/skills）

    Returns:
        成功/失败消息

    Security:
        - 验证名称格式
        - 防止路径遍历
        - 检查符号链接
    """
    try:
        # 1. 验证 skill 名称
        is_valid, error_msg = validate_skill_name(skill_name)
        if not is_valid:
            return f"❌ 名称验证失败：{error_msg}"

        # 2. 验证并规范化路径
        skills_path = Path(skills_dir).resolve()
        skill_dir = skills_path / skill_name

        # 3. 检查路径遍历
        if not skill_dir.is_relative_to(skills_path):
            return "❌ 安全错误：路径遍历检测"

        # 4. 检查是否已存在
        if skill_dir.exists():
            return f"❌ Skill '{skill_name}' 已存在"

        # 5. 检查父目录是否可写
        if not skills_path.exists():
            return f"❌ Skills 目录不存在：{skills_path}"

        # 6. 创建目录（使用安全模式）
        skill_dir.mkdir(parents=False, exist_ok=False)

        # 7. 创建 skill.json
        skill_json = {
            "name": skill_name,
            "version": "1.0.0",
            "description": f"{skill_name} skill for kuma-claw",
            "triggers": [skill_name],
            "author": "",
            "dependencies": [],
            "tools": [],
        }

        skill_json_path = skill_dir / "skill.json"
        with open(skill_json_path, "w", encoding="utf-8") as f:
            json.dump(skill_json, f, indent=2, ensure_ascii=False)

        # 8. 创建 tools.py
        tools_py = f'''"""
{skill_name} - 工具定义
"""

from google.adk.tools import FunctionTool


def example_tool(param: str) -> str:
    """示例工具

    Args:
        param: 参数说明

    Returns:
        结果字符串
    """
    return f"收到: {{param}}"


TOOLS = [
    FunctionTool(func=example_tool)
]
'''

        tools_path = skill_dir / "tools.py"
        with open(tools_path, "w", encoding="utf-8") as f:
            f.write(tools_py)

        # 9. 创建 prompts.py
        prompts_py = f'''"""
{skill_name} - 提示词定义
"""

SYSTEM_PROMPT = """
## {skill_name} 能力

TODO: 添加技能说明和使用场景

### 可用工具
- **example_tool**: 示例工具说明

### 使用示例
```python
example_tool(param="value")
```
"""

EXAMPLES = [
    {{
        "user": "示例用户输入",
        "assistant": "示例助手回复",
        "tool_call": "example_tool(param='value')"
    }}
]
'''

        prompts_path = skill_dir / "prompts.py"
        with open(prompts_path, "w", encoding="utf-8") as f:
            f.write(prompts_py)

        # 10. 创建 __init__.py
        init_path = skill_dir / "__init__.py"
        with open(init_path, "w", encoding="utf-8") as f:
            f.write(
                f'"""{skill_name} skill"""\n'
                f"from .tools import TOOLS\n"
                f"from .prompts import SYSTEM_PROMPT, EXAMPLES\n"
            )

        return f"""✅ Skill '{skill_name}' 初始化成功

📁 位置: {skill_dir}

📝 已创建文件：
- skill.json    (元数据)
- tools.py      (工具定义)
- prompts.py    (提示词)
- __init__.py   (导出接口)

🎯 下一步：
1. 编辑 skill.json 添加触发词和工具定义
2. 实现 tools.py 中的工具函数
3. 完善 prompts.py 中的系统提示词
4. 使用 validate_skill() 验证结构
5. 使用 package_skill() 打包分发"""

    except PermissionError as e:
        return f"❌ 权限错误：{str(e)}"
    except OSError as e:
        return f"❌ 系统错误：{str(e)}"
    except (RuntimeError, ValueError, OSError) as e:
        return f"❌ 初始化失败：{str(e)}"


def validate_skill(skill_name: str, skills_dir: str = "kuma_claw/skills") -> str:
    """验证 skill 结构和配置是否正确

    Args:
        skill_name: 要验证的 skill 名称
        skills_dir: Skills 目录路径

    Returns:
        验证结果

    Security:
        - 路径遍历检查
        - 符号链接检测
        - 文件大小限制
    """
    try:
        # 1. 验证名称
        is_valid, error_msg = validate_skill_name(skill_name)
        if not is_valid:
            return f"❌ 名称验证失败：{error_msg}"

        # 2. 验证路径
        skills_path = Path(skills_dir).resolve()
        skill_path = skills_path / skill_name

        # 3. 检查路径遍历
        if not skill_path.is_relative_to(skills_path):
            return "❌ 安全错误：路径遍历检测"

        # 4. 检查是否存在
        if not skill_path.exists():
            return f"❌ Skill '{skill_name}' 不存在"

        # 5. 检查符号链接
        if skill_path.is_symlink():
            return "❌ 安全错误：不允许符号链接"

        errors = []
        warnings = []

        # 6. 检查必需文件
        required_files = ["skill.json", "tools.py", "prompts.py", "__init__.py"]
        for file_name in required_files:
            file_path = skill_path / file_name

            if not file_path.exists():
                errors.append(f"缺少必需文件: {file_name}")
                continue

            # 检查符号链接
            if file_path.is_symlink():
                errors.append(f"安全错误：{file_name} 是符号链接")
                continue

            # 检查文件大小
            if file_path.stat().st_size > MAX_FILE_SIZE:
                errors.append(f"文件过大：{file_name} 超过 {MAX_FILE_SIZE // 1024 // 1024}MB")

        # 7. 验证 skill.json
        if not any("skill.json" in e for e in errors):
            try:
                skill_json_path = skill_path / "skill.json"

                with open(skill_json_path, encoding="utf-8") as f:
                    skill_json = json.load(f)

                # 检查必需字段
                required_fields = ["name", "version", "description", "triggers"]
                for field in required_fields:
                    if field not in skill_json:
                        errors.append(f"skill.json 缺少必需字段: {field}")

                # 验证触发词
                if "triggers" in skill_json:
                    triggers = skill_json["triggers"]
                    if not isinstance(triggers, list) or len(triggers) == 0:
                        errors.append("triggers 必须是非空数组")

                # 验证版本格式
                if "version" in skill_json:
                    if not validate_version(skill_json["version"]):
                        warnings.append(f"版本格式不符合 semver: {skill_json['version']}")

                # 验证名称一致性
                if "name" in skill_json:
                    if skill_json["name"] != skill_name:
                        errors.append(
                            f"名称不一致：目录名 '{skill_name}' vs "
                            f"skill.json 中的 '{skill_json['name']}'"
                        )

            except json.JSONDecodeError as e:
                errors.append(f"skill.json 格式错误: {e}")
            except (RuntimeError, ValueError, OSError) as e:
                errors.append(f"读取 skill.json 失败: {str(e)}")

        # 8. 检查 tools.py
        if not any("tools.py" in e for e in errors):
            try:
                tools_path = skill_path / "tools.py"
                with open(tools_path, encoding="utf-8") as f:
                    content = f.read()
                    if "TOOLS" not in content:
                        warnings.append("tools.py 中未找到 TOOLS 列表")
                    if "FunctionTool" not in content:
                        warnings.append("tools.py 中未使用 FunctionTool")
            except (RuntimeError, ValueError, OSError) as e:
                errors.append(f"读取 tools.py 失败: {str(e)}")

        # 9. 检查 prompts.py
        if not any("prompts.py" in e for e in errors):
            try:
                prompts_path = skill_path / "prompts.py"
                with open(prompts_path, encoding="utf-8") as f:
                    content = f.read()
                    if "SYSTEM_PROMPT" not in content:
                        warnings.append("prompts.py 中未找到 SYSTEM_PROMPT")
            except (RuntimeError, ValueError, OSError) as e:
                errors.append(f"读取 prompts.py 失败: {str(e)}")

        # 10. 检查总文件数和大小
        try:
            total_size = sum(f.stat().st_size for f in skill_path.rglob("*") if f.is_file())
            file_count = sum(1 for f in skill_path.rglob("*") if f.is_file())

            if total_size > MAX_SKILL_SIZE:
                warnings.append(
                    f"Skill 总大小 {total_size // 1024 // 1024}MB 超过建议值 {MAX_SKILL_SIZE // 1024 // 1024}MB"
                )

            if file_count > MAX_FILES_COUNT:
                warnings.append(f"文件数量 {file_count} 超过建议值 {MAX_FILES_COUNT}")
        except (RuntimeError, ValueError, OSError):
            pass

        # 11. 生成结果
        result_lines = [f"🔍 Skill '{skill_name}' 验证结果:\n"]

        if errors:
            result_lines.append("❌ 错误:")
            for error in errors:
                result_lines.append(f"  - {error}")

        if warnings:
            result_lines.append("\n⚠️  警告:")
            for warning in warnings:
                result_lines.append(f"  - {warning}")

        if not errors and not warnings:
            result_lines.append("✅ 所有检查通过！Skill 结构正确。")
        elif not errors:
            result_lines.append("\n💡 Skill 可以使用，但建议修复警告项。")

        return "\n".join(result_lines)

    except PermissionError as e:
        return f"❌ 权限错误：{str(e)}"
    except (RuntimeError, ValueError, OSError) as e:
        return f"❌ 验证失败：{str(e)}"


def package_skill(
    skill_name: str,
    output_dir: str = ".",
    skills_dir: str = "kuma_claw/skills",
    allowed_dirs: list[str] | None = None,
) -> str:
    """打包 skill 为 .skill 文件

    Args:
        skill_name: 要打包的 skill 名称
        output_dir: 输出目录（默认当前目录）
        skills_dir: Skills 目录路径
        allowed_dirs: 允许的输出目录列表（可选）

    Returns:
        打包结果

    Security:
        - 路径遍历防护
        - 输出目录白名单
        - 符号链接检测
        - 资源限制
    """
    try:
        # 1. 验证名称
        is_valid, error_msg = validate_skill_name(skill_name)
        if not is_valid:
            return f"❌ 名称验证失败：{error_msg}"

        # 2. 验证输入路径
        skills_path = Path(skills_dir).resolve()
        skill_path = skills_path / skill_name

        # 3. 检查路径遍历
        if not skill_path.is_relative_to(skills_path):
            return "❌ 安全错误：路径遍历检测（输入）"

        # 4. 检查是否存在
        if not skill_path.exists():
            return f"❌ Skill '{skill_name}' 不存在"

        # 5. 检查符号链接
        if skill_path.is_symlink():
            return "❌ 安全错误：不允许符号链接"

        # 6. 先验证 skill
        validation = validate_skill(skill_name, skills_dir)
        if "❌ 错误:" in validation:
            return f"❌ 验证失败，无法打包:\n{validation}"

        # 7. 验证输出路径
        output_path = Path(output_dir).resolve()
        output_file = output_path / f"{skill_name}.skill"

        # 8. 确定允许的目录
        allowed_paths = [Path(p).resolve() for p in (allowed_dirs or [])]
        if not allowed_paths:
            allowed_paths = [Path.cwd(), Path.home() / ".kuma-claw", Path("/tmp")]

        # 9. 检查输出路径是否在允许范围内
        if not validate_path_safe(output_file, allowed_paths):
            allowed_str = ", ".join(str(p) for p in allowed_paths)
            return f"❌ 安全错误：输出路径不在允许范围内\n允许的目录: {allowed_str}"

        # 10. 检查输出目录是否存在
        if not output_path.exists():
            return f"❌ 输出目录不存在：{output_path}"

        # 11. 检查是否可写
        if not output_path.is_dir():
            return f"❌ 输出路径不是目录：{output_path}"

        # 12. 检查 skill 总大小
        total_size = sum(f.stat().st_size for f in skill_path.rglob("*") if f.is_file())
        if total_size > MAX_SKILL_SIZE:
            return f"❌ Skill 大小 {total_size // 1024 // 1024}MB 超过限制 {MAX_SKILL_SIZE // 1024 // 1024}MB"

        # 13. 创建临时目录并复制文件
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_skill_dir = Path(tmpdir) / skill_name

            # 安全复制（检查每个文件）
            for item in skill_path.rglob("*"):
                if item.is_symlink():
                    continue  # 跳过符号链接

                rel_path = item.relative_to(skill_path)
                target = tmp_skill_dir / rel_path

                if item.is_dir():
                    target.mkdir(parents=True, exist_ok=True)
                elif item.is_file():
                    # 检查文件大小
                    if item.stat().st_size > MAX_FILE_SIZE:
                        return f"❌ 文件过大：{rel_path}"

                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(item, target)

            # 14. 删除已存在的文件
            if output_file.exists():
                output_file.unlink()

            # 15. 打包
            shutil.make_archive(str(output_file.with_suffix("")), "zip", tmpdir, skill_name)

            # 16. 重命名为 .skill
            zip_path = output_file.with_suffix(".zip")
            zip_path.rename(output_file)

            # 17. 获取文件大小
            size = output_file.stat().st_size
            size_str = f"{size / 1024:.1f}KB" if size > 1024 else f"{size}B"

            return f"""✅ Skill '{skill_name}' 打包成功

📦 文件: {output_file}
📊 大小: {size_str}

📋 包含内容:
- skill.json
- tools.py
- prompts.py
- __init__.py

🚀 可以分发此文件，其他人解压后即可使用"""

    except PermissionError as e:
        return f"❌ 权限错误：{str(e)}"
    except OSError as e:
        return f"❌ 系统错误：{str(e)}"
    except (RuntimeError, ValueError, OSError) as e:
        return f"❌ 打包失败：{str(e)}"


# ============================================
# 导出工具列表
# ============================================

TOOLS = [
    FunctionTool(func=init_skill),
    FunctionTool(func=validate_skill),
    FunctionTool(func=package_skill),
]
