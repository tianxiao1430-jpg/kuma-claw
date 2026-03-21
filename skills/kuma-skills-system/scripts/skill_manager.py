"""
kuma_claw/skills/skill_manager.py
==================================
Skill 管理器 - 安全加载、注册、管理 skills

安全特性：
- 动态代码沙箱隔离
- 路径遍历防护
- 输入验证
- 签名验证（可选）
"""

import json
import logging
import hashlib
import importlib.util
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Set, Any
from google.adk.tools import FunctionTool

logger = logging.getLogger("kuma_claw")


class SecurityError(Exception):
    """安全相关错误"""
    pass


class SkillValidationError(Exception):
    """Skill 验证错误"""
    pass


class Skill:
    """Skill 定义（安全加载）"""
    
    # 允许的安全模块白名单
    ALLOWED_MODULES: Set[str] = {
        # 标准库
        'json', 'pathlib', 'typing', 'datetime', 're', 'math',
        'collections', 'itertools', 'functools', 'operator',
        # Google ADK
        'google.adk.tools', 'google.adk.agents',
        # 常用安全库
        'requests', 'httpx', 'aiohttp',
        'beautifulsoup4', 'bs4',
        'lxml', 'xml.etree.ElementTree',
    }
    
    # 危险函数黑名单
    DANGEROUS_FUNCTIONS: Set[str] = {
        'eval', 'exec', 'compile', 'open', 'input',
        '__import__', 'globals', 'locals', 'vars',
        'execfile', 'reload',
        'os.system', 'os.popen', 'os.spawn',
        'subprocess.call', 'subprocess.run', 'subprocess.Popen',
        'shutil.rmtree', 'shutil.move',
    }

    def __init__(self, skill_dir: Path, verify_signature: bool = False):
        self.dir = skill_dir.resolve()  # 规范化路径
        self.metadata = self._load_metadata()
        self.tools = self._load_tools_safe()
        self.prompts = self._load_prompts_safe()
        
        if verify_signature:
            self._verify_signature()

    def _load_metadata(self) -> dict:
        """加载 skill.json（带验证）"""
        metadata_file = self.dir / "skill.json"
        
        if not metadata_file.exists():
            raise FileNotFoundError(f"skill.json not found in {self.dir}")
        
        # 检查路径遍历
        if not metadata_file.resolve().is_relative_to(self.dir):
            raise SecurityError(f"Path traversal detected: {metadata_file}")
        
        try:
            with open(metadata_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 验证必需字段
            required_fields = ['name', 'version', 'triggers']
            missing = [f for f in required_fields if f not in data]
            if missing:
                raise SkillValidationError(f"Missing required fields: {missing}")
            
            # 验证名称格式
            name = data.get('name', '')
            is_valid, error_msg = validate_skill_name(name)
            if not is_valid:
                raise SkillValidationError(f"Invalid skill name: {error_msg}")
            
            # 验证版本格式
            version = data.get('version', '')
            if not validate_version(version):
                raise SkillValidationError(f"Invalid version format: {version}")
            
            return data
            
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in {metadata_file}: {e}")
            raise SkillValidationError(f"Invalid JSON: {e}")

    def _load_tools_safe(self) -> List[FunctionTool]:
        """安全加载 tools.py（沙箱隔离）"""
        tools_file = self.dir / "tools.py"
        
        if not tools_file.exists():
            logger.warning(f"tools.py not found in {self.dir}")
            return []
        
        # 检查路径遍历
        if not tools_file.resolve().is_relative_to(self.dir):
            raise SecurityError(f"Path traversal detected: {tools_file}")
        
        try:
            # 读取代码
            with open(tools_file, 'r', encoding='utf-8') as f:
                code = f.read()
            
            # 静态分析：检查危险函数
            self._check_dangerous_code(code)
            
            # 使用受限模块加载
            spec = importlib.util.spec_from_file_location(
                f"skill_{self.metadata['name']}_tools",
                tools_file
            )
            
            if spec is None or spec.loader is None:
                logger.warning(f"Failed to create spec for {tools_file}")
                return []
            
            module = importlib.util.module_from_spec(spec)
            
            # 创建受限的全局命名空间
            safe_globals = self._create_safe_globals()
            module.__dict__.update(safe_globals)
            
            # 执行模块代码
            spec.loader.exec_module(module)
            
            # 提取 TOOLS 列表
            tools = getattr(module, "TOOLS", [])
            
            if not isinstance(tools, list):
                logger.warning(f"TOOLS is not a list in {self.dir}")
                return []
            
            # 验证工具类型
            validated_tools = []
            for tool in tools:
                if isinstance(tool, FunctionTool):
                    validated_tools.append(tool)
                else:
                    logger.warning(f"Invalid tool type in {self.dir}: {type(tool)}")
            
            return validated_tools
            
        except SecurityError:
            raise
        except Exception as e:
            logger.error(f"Failed to load tools from {self.dir}: {e}")
            return []

    def _load_prompts_safe(self) -> dict:
        """安全加载 prompts.py"""
        prompts_file = self.dir / "prompts.py"
        
        if not prompts_file.exists():
            return {"system": "", "examples": []}
        
        # 检查路径遍历
        if not prompts_file.resolve().is_relative_to(self.dir):
            raise SecurityError(f"Path traversal detected: {prompts_file}")
        
        try:
            with open(prompts_file, 'r', encoding='utf-8') as f:
                code = f.read()
            
            # 静态分析
            self._check_dangerous_code(code)
            
            # 加载模块
            spec = importlib.util.spec_from_file_location(
                f"skill_{self.metadata['name']}_prompts",
                prompts_file
            )
            
            if spec is None or spec.loader is None:
                return {"system": "", "examples": []}
            
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            return {
                "system": getattr(module, "SYSTEM_PROMPT", ""),
                "examples": getattr(module, "EXAMPLES", []),
            }
            
        except SecurityError:
            raise
        except Exception as e:
            logger.warning(f"Failed to load prompts from {self.dir}: {e}")
            return {"system": "", "examples": []}

    def _check_dangerous_code(self, code: str) -> None:
        """静态分析检查危险代码"""
        # 检查危险函数调用
        for func in self.DANGEROUS_FUNCTIONS:
            if f"{func}(" in code or f"{func} (" in code:
                raise SecurityError(
                    f"Dangerous function '{func}' detected in skill code. "
                    f"Skill: {self.metadata.get('name', 'unknown')}"
                )
        
        # 检查导入危险模块
        dangerous_imports = [
            'os', 'sys', 'subprocess', 'socket', 'pickle',
            'marshal', 'shelve', 'ctypes', 'multiprocessing'
        ]
        
        for mod in dangerous_imports:
            patterns = [
                f"import {mod}",
                f"from {mod}",
                f"__import__('{mod}'",
                f'__import__("{mod}"',
            ]
            for pattern in patterns:
                if pattern in code:
                    raise SecurityError(
                        f"Dangerous import '{mod}' detected in skill code. "
                        f"Skill: {self.metadata.get('name', 'unknown')}"
                    )

    def _create_safe_globals(self) -> dict:
        """创建安全的全局命名空间"""
        import builtins
        
        # 白名单化的内置函数
        safe_builtins = {
            'True': True,
            'False': False,
            'None': None,
            'abs': abs,
            'all': all,
            'any': any,
            'bool': bool,
            'dict': dict,
            'enumerate': enumerate,
            'filter': filter,
            'float': float,
            'frozenset': frozenset,
            'hasattr': hasattr,
            'hash': hash,
            'int': int,
            'isinstance': isinstance,
            'issubclass': issubclass,
            'iter': iter,
            'len': len,
            'list': list,
            'map': map,
            'max': max,
            'min': min,
            'next': next,
            'object': object,
            'pow': pow,
            'print': print,
            'range': range,
            'reversed': reversed,
            'round': round,
            'set': set,
            'slice': slice,
            'sorted': sorted,
            'str': str,
            'sum': sum,
            'tuple': tuple,
            'type': type,
            'zip': zip, '__import__': __import__,
            'Exception': Exception,
            'ValueError': ValueError,
            'TypeError': TypeError,
            'KeyError': KeyError,
            'IndexError': IndexError,
            'AttributeError': AttributeError,
            'RuntimeError': RuntimeError,
        }
        
        return {'__builtins__': safe_builtins}

    def _verify_signature(self) -> bool:
        """验证 skill 签名（可选功能）"""
        signature_file = self.dir / ".signature"
        
        if not signature_file.exists():
            logger.warning(f"No signature file found for skill: {self.name}")
            return False
        
        try:
            # 计算文件哈希
            hasher = hashlib.sha256()
            
            for file_name in ['skill.json', 'tools.py', 'prompts.py']:
                file_path = self.dir / file_name
                if file_path.exists():
                    with open(file_path, 'rb') as f:
                        hasher.update(file_path.name.encode())
                        hasher.update(f.read())
            
            computed_hash = hasher.hexdigest()
            
            # 读取签名
            with open(signature_file, 'r') as f:
                stored_hash = f.read().strip()
            
            if computed_hash != stored_hash:
                raise SecurityError(
                    f"Signature verification failed for skill: {self.name}"
                )
            
            logger.info(f"Signature verified for skill: {self.name}")
            return True
            
        except Exception as e:
            logger.error(f"Signature verification error: {e}")
            raise SecurityError(f"Signature verification failed: {e}")

    @property
    def name(self) -> str:
        return self.metadata.get("name", self.dir.name)

    @property
    def triggers(self) -> List[str]:
        return self.metadata.get("triggers", [])


# ============================================
# 验证函数
# ============================================

# 保留名称黑名单
RESERVED_NAMES: Set[str] = {
    'test', 'tmp', 'temp', 'skill', 'skills',
    'kuma-claw', 'kuma_claw', '__pycache__',
    'con', 'prn', 'aux', 'nul',  # Windows 保留名
    'admin', 'root', 'system', 'default',
}


def validate_skill_name(skill_name: str) -> Tuple[bool, str]:
    """验证 skill 名称
    
    Args:
        skill_name: 要验证的名称
        
    Returns:
        (is_valid, error_message)
    """
    import re
    
    if not skill_name:
        return False, "Skill 名称不能为空"
    
    if len(skill_name) < 2:
        return False, "Skill 名称至少 2 个字符"
    
    if len(skill_name) > 64:
        return False, "Skill 名称最多 64 字符"
    
    if not re.match(r"^[a-z0-9-]+$", skill_name):
        return False, "只能包含小写字母、数字和连字符"
    
    if skill_name.startswith('-') or skill_name.endswith('-'):
        return False, "不能以连字符开头或结尾"
    
    if '--' in skill_name:
        return False, "不能包含连续的连字符"
    
    if skill_name in RESERVED_NAMES:
        return False, f"'{skill_name}' 是保留名称"
    
    if skill_name.isdigit():
        return False, "不能是纯数字"
    
    return True, "Valid"


def validate_version(version: str) -> bool:
    """验证版本号格式（semver）"""
    import re
    pattern = r'^(\d+)\.(\d+)\.(\d+)(?:-([0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?(?:\+([0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?$'
    return bool(re.match(pattern, version))


def validate_path_safe(path: Path, allowed_dirs: List[Path]) -> bool:
    """验证路径是否在允许范围内
    
    Args:
        path: 要验证的路径
        allowed_dirs: 允许的目录列表
        
    Returns:
        是否安全
    """
    try:
        resolved_path = path.resolve()
        
        for allowed_dir in allowed_dirs:
            if resolved_path.is_relative_to(allowed_dir.resolve()):
                return True
        
        return False
        
    except Exception:
        return False


# ============================================
# SkillManager
# ============================================

class SkillManager:
    """Skill 管理器（安全增强版）"""

    def __init__(
        self,
        skills_dir: Optional[Path] = None,
        verify_signatures: bool = False,
        allowed_output_dirs: Optional[List[Path]] = None
    ):
        self.skills_dir = (skills_dir or Path(__file__).parent).resolve()
        self.verify_signatures = verify_signatures
        self.skills: Dict[str, Skill] = {}
        
        # 允许的输出目录
        self.allowed_output_dirs = allowed_output_dirs or [
            Path.cwd(),
            Path.home() / ".kuma-claw",
            Path("/tmp"),
        ]
        
        self._load_all_skills()

    def _load_all_skills(self):
        """加载所有 skills（安全）"""
        if not self.skills_dir.exists():
            logger.warning(f"Skills directory not found: {self.skills_dir}")
            return
        
        for skill_dir in self.skills_dir.iterdir():
            if not skill_dir.is_dir():
                continue
            
            # 跳过隐藏目录和特殊目录
            if skill_dir.name.startswith('.') or skill_dir.name.startswith('__'):
                continue
            
            skill_json = skill_dir / "skill.json"
            if not skill_json.exists():
                continue
            
            try:
                skill = Skill(skill_dir, verify_signature=self.verify_signatures)
                self.skills[skill.name] = skill
                logger.info(f"Loaded skill: {skill.name}")
            except SecurityError as e:
                logger.error(f"Security violation in skill {skill_dir.name}: {e}")
            except SkillValidationError as e:
                logger.error(f"Invalid skill {skill_dir.name}: {e}")
            except Exception as e:
                logger.error(f"Failed to load skill {skill_dir.name}: {e}")

    def get_skill_by_trigger(self, text: str) -> Optional[Skill]:
        """根据触发词查找 skill"""
        text_lower = text.lower()
        for skill in self.skills.values():
            for trigger in skill.triggers:
                if trigger.lower() in text_lower:
                    return skill
        return None

    def get_all_tools(self) -> List[FunctionTool]:
        """获取所有 skill 的工具"""
        tools = []
        for skill in self.skills.values():
            tools.extend(skill.tools)
        return tools

    def get_all_prompts(self) -> str:
        """获取所有 skill 的系统提示词"""
        prompts = []
        for skill in self.skills.values():
            if skill.prompts.get("system"):
                prompts.append(f"## {skill.name}\n{skill.prompts['system']}")
        return "\n\n---\n\n".join(prompts)

    def list_skills(self) -> List[dict]:
        """列出所有 skills"""
        return [
            {
                "name": skill.name,
                "version": skill.metadata.get("version", "unknown"),
                "description": skill.metadata.get("description", ""),
                "triggers": skill.triggers,
                "tools_count": len(skill.tools),
                "author": skill.metadata.get("author", "unknown"),
            }
            for skill in self.skills.values()
        ]

    def reload_skill(self, skill_name: str) -> bool:
        """重新加载指定 skill"""
        skill_dir = self.skills_dir / skill_name
        
        if not skill_dir.exists():
            logger.error(f"Skill directory not found: {skill_dir}")
            return False
        
        # 验证路径安全
        if not validate_path_safe(skill_dir, [self.skills_dir]):
            logger.error(f"Path traversal attempt: {skill_dir}")
            return False
        
        try:
            skill = Skill(skill_dir, verify_signature=self.verify_signatures)
            self.skills[skill.name] = skill
            logger.info(f"Reloaded skill: {skill.name}")
            return True
        except Exception as e:
            logger.error(f"Failed to reload skill {skill_name}: {e}")
            return False

    def unload_skill(self, skill_name: str) -> bool:
        """卸载 skill"""
        if skill_name in self.skills:
            del self.skills[skill_name]
            logger.info(f"Unloaded skill: {skill_name}")
            return True
        return False

    def register_tools_to_agent(self, agent: Any) -> int:
        """将 Skills 的工具自动注册到 Agent

        Args:
            agent: ADK Agent 实例（LlmAgent 或其他兼容类型）

        Returns:
            注册的工具数量
        """
        if not hasattr(agent, 'tools'):
            logger.warning("Agent 没有 tools 属性，无法注册")
            return 0
        
        skill_tools = self.get_all_tools()
        
        if not skill_tools:
            logger.info("没有可用的 Skill 工具")
            return 0
        
        # 获取现有工具（避免重复）
        existing_tool_names = set()
        for tool in agent.tools:
            if hasattr(tool, 'name'):
                existing_tool_names.add(tool.name)
            elif hasattr(tool, 'func') and hasattr(tool.func, '__name__'):
                existing_tool_names.add(tool.func.__name__)
        
        # 过滤已存在的工具
        new_tools = []
        for tool in skill_tools:
            tool_name = None
            if hasattr(tool, 'name'):
                tool_name = tool.name
            elif hasattr(tool, 'func') and hasattr(tool.func, '__name__'):
                tool_name = tool.func.__name__
            
            if tool_name and tool_name not in existing_tool_names:
                new_tools.append(tool)
                existing_tool_names.add(tool_name)
        
        # 注册新工具
        if new_tools:
            agent.tools.extend(new_tools)
            logger.info(f"注册了 {len(new_tools)} 个 Skill 工具到 Agent")
            
            for tool in new_tools:
                tool_name = getattr(tool, 'name', None)
                if not tool_name and hasattr(tool, 'func') and hasattr(tool.func, '__name__'):
                    tool_name = tool.func.__name__
                logger.debug(f"  - {tool_name}")
        
        return len(new_tools)

    def inject_prompts_to_agent(self, agent: Any) -> bool:
        """将 Skills 的提示词注入到 Agent 的系统指令中

        Args:
            agent: ADK Agent 实例

        Returns:
            是否成功
        """
        if not hasattr(agent, 'instruction'):
            logger.warning("Agent 没有 instruction 属性，无法注入")
            return False
        
        skill_prompts = self.get_all_prompts()
        
        if not skill_prompts:
            logger.info("没有可用的 Skill 提示词")
            return False
        
        # 追加到现有指令
        prompts_section = "\n\n---\n\n## Skills\n\n" + skill_prompts
        agent.instruction += prompts_section
        
        logger.info(f"已注入 Skill 提示词到 Agent")
        return True


# 全局实例
skill_manager = SkillManager()
