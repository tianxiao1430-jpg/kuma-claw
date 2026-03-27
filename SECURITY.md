# Kuma Claw Skills 系统安全指南

## 概述

本文档描述 kuma-claw skills 系统的安全架构、防护措施和最佳实践。

---

## 🔒 安全架构

### 1. 多层防护模型

```
┌─────────────────────────────────────────────┐
│           用户输入验证层                      │
│  - 名称格式验证                               │
│  - 路径规范化                                 │
│  - 保留名称检查                               │
└─────────────────┬───────────────────────────┘
                  │
┌─────────────────▼───────────────────────────┐
│           路径安全层                          │
│  - 路径遍历防护                               │
│  - 符号链接检测                               │
│  - 白名单目录验证                             │
└─────────────────┬───────────────────────────┘
                  │
┌─────────────────▼───────────────────────────┐
│           代码静态分析层                      │
│  - 危险函数检测                               │
│  - 危险导入检测                               │
│  - AST 解析验证                              │
└─────────────────┬───────────────────────────┘
                  │
┌─────────────────▼───────────────────────────┐
│           运行时沙箱层                        │
│  - 受限全局命名空间                           │
│  - 白名单模块                                 │
│  - 资源限制                                   │
└─────────────────┬───────────────────────────┘
                  │
┌─────────────────▼───────────────────────────┐
│           签名验证层（可选）                   │
│  - SHA256 哈希验证                           │
│  - 作者身份确认                               │
└─────────────────────────────────────────────┘
```

---

## 🛡️ 已实现的防护措施

### 1. 输入验证

#### Skill 名称验证
```python
# 规则：
- 2-64 字符
- 只允许：小写字母、数字、连字符
- 不能以连字符开头/结尾
- 不能包含连续连字符
- 不能是保留名称
```

**保留名称黑名单：**
```python
RESERVED_NAMES = {
    'test', 'tmp', 'temp', 'skill', 'skills',
    'kuma-claw', 'kuma_claw', '__pycache__',
    'con', 'prn', 'aux', 'nul',  # Windows 保留名
    'admin', 'root', 'system', 'default',
}
```

#### 版本号验证
```python
# 语义化版本：X.Y.Z
validate_version("1.0.0")  # ✅
validate_version("v1.0")   # ❌
```

### 2. 路径安全

#### 路径遍历防护
```python
# 自动检测并阻止：
- "../../../etc/passwd"
- "..\\..\\..\\etc\\passwd"
- "/absolute/path/skill"
```

#### 符号链接检测
```python
# 拒绝所有符号链接
if skill_path.is_symlink():
    raise SecurityError("符号链接不允许")
```

#### 输出目录白名单
```python
# 只允许输出到以下目录：
DEFAULT_ALLOWED_DIRS = [
    Path.cwd(),              # 当前工作目录
    Path.home() / ".kuma-claw",  # 用户配置目录
    Path("/tmp"),            # 临时目录
]
```

### 3. 代码静态分析

#### 危险函数检测
```python
DANGEROUS_FUNCTIONS = {
    'eval', 'exec', 'compile', 'open', 'input',
    '__import__', 'globals', 'locals', 'vars',
    'os.system', 'os.popen', 'os.spawn',
    'subprocess.*', 'shutil.rmtree',
}
```

#### 危险导入检测
```python
# 阻止导入：
- os, sys
- subprocess
- socket
- pickle, marshal
- ctypes
- multiprocessing
```

### 4. 运行时沙箱

#### 受限全局命名空间
```python
safe_builtins = {
    # 只允许安全的内置函数
    'abs', 'all', 'any', 'bool', 'dict', 'list',
    'str', 'int', 'float', 'len', 'range', 'sorted',
    # ... 完整列表见 skill_manager.py
}
```

#### 允许的模块白名单
```python
ALLOWED_MODULES = {
    # 标准库
    'json', 'pathlib', 'typing', 'datetime',
    # Google ADK
    'google.adk.tools', 'google.adk.agents',
    # 常用安全库
    'requests', 'httpx', 'beautifulsoup4',
}
```

### 5. 资源限制

```python
MAX_SKILL_SIZE = 10 * 1024 * 1024  # 10MB
MAX_FILES_COUNT = 100
MAX_FILE_SIZE = 1 * 1024 * 1024   # 1MB
```

### 6. 签名验证（可选）

```python
# 启用方式
skill_manager = SkillManager(verify_signatures=True)

# 生成签名
$ kuma-claw skill sign <skill-name>
```

---

## 🚨 已知威胁与防护

| 威胁 | 风险等级 | 防护措施 | 状态 |
|------|---------|---------|------|
| 路径遍历攻击 | 🔴 高 | 路径规范化 + is_relative_to | ✅ 已防护 |
| 符号链接攻击 | 🔴 高 | is_symlink() 检测 | ✅ 已防护 |
| 任意代码执行 | 🔴 高 | 静态分析 + 沙箱 | ✅ 已防护 |
| 资源耗尽攻击 | 🟡 中 | 文件大小/数量限制 | ✅ 已防护 |
| 供应链攻击 | 🟡 中 | 签名验证（可选） | ✅ 已实现 |
| 敏感信息泄露 | 🟡 中 | 危险函数检测 | ✅ 已防护 |
| 名称冲突 | 🟢 低 | 保留名称黑名单 | ✅ 已防护 |
| 版本伪造 | 🟢 低 | semver 验证 | ✅ 已防护 |

---

## 📋 安全检查清单

### 在推送 PR 前，确认以下项目：

#### 必须项（P0）
- [ ] 所有用户输入都经过验证
- [ ] 所有文件操作都检查路径安全
- [ ] 动态代码执行使用沙箱隔离
- [ ] 错误消息不泄露敏感信息
- [ ] 测试覆盖安全相关功能

#### 推荐项（P1）
- [ ] 资源限制已设置
- [ ] 符号链接已检测
- [ ] 危险导入已阻止
- [ ] 日志记录安全事件

#### 可选项（P2）
- [ ] 签名验证已实现
- [ ] 安全审计日志
- [ ] 速率限制

---

## 🔧 配置选项

### 环境变量

```bash
# 启用签名验证
KUMA_SKILL_VERIFY_SIGNATURES=true

# 设置最大 skill 大小（字节）
KUMA_MAX_SKILL_SIZE=10485760

# 设置允许的输出目录（逗号分隔）
KUMA_ALLOWED_DIRS=/tmp,/home/user/.kuma-claw
```

### 代码配置

```python
from kuma_claw.skills.skill_manager import SkillManager

# 严格模式（启用所有安全特性）
manager = SkillManager(
    verify_signatures=True,  # 签名验证
    allowed_output_dirs=[
        Path.home() / ".kuma-claw",
    ]
)
```

---

## 🧪 测试

### 运行安全测试

```bash
# 运行安全相关测试
pytest tests/test_skill_manager.py -v

# 运行全部测试
pytest
```

### 测试覆盖

- ✅ 名称验证
- ✅ 保留名称检测
- ✅ 路径遍历防护
- ✅ 输出目录白名单
- ✅ 符号链接防护
- ✅ 资源限制
- ✅ 危险代码检测

---

## 📖 最佳实践

### 1. Skill 开发者

**✅ 推荐：**
- 使用最小权限原则
- 只导入必需的模块
- 使用类型提示
- 编写清晰的文档
- 遵循命名规范

**❌ 禁止：**
- 使用 `eval()`, `exec()`
- 导入 `os`, `subprocess`
- 读取系统文件
- 发送网络请求到未授权地址

### 2. Skill 使用者

**✅ 推荐：**
- 只安装可信来源的 skill
- 验证 skill 签名
- 定期更新 skill
- 审查 skill 代码

**❌ 禁止：**
- 安装来源不明的 skill
- 禁用安全检查
- 以 root 权限运行

### 3. 系统管理员

**✅ 推荐：**
- 定期审计已安装的 skill
- 监控安全日志
- 保持系统更新
- 限制网络访问

---

## 🆘 事件响应

### 发现安全漏洞时

1. **立即隔离**
   ```bash
   # 卸载可疑 skill
   kuma-claw skill unload <skill-name>
   ```

2. **收集信息**
   ```bash
   # 查看日志
   tail -f ~/.kuma-claw/logs/security.log
   ```

3. **报告漏洞**
   - 发送邮件到: security@kuma-claw.dev
   - 包含: 漏洞描述、复现步骤、影响范围

4. **临时缓解**
   ```bash
   # 禁用所有第三方 skill
   kuma-claw config --set allow_third_party=false
   ```

---

## 📚 参考资料

- [OWASP Path Traversal](https://owasp.org/www-community/attacks/Path_Traversal)
- [Python Sandboxing](https://pypi.org/project/RestrictedPython/)
- [Semantic Versioning](https://semver.org/)
- [Google ADK Security](https://github.com/google/adk-python)

---

## 📝 更新日志

### 2026-03-13
- ✅ 添加路径遍历防护
- ✅ 实现动态代码沙箱
- ✅ 添加符号链接检测
- ✅ 实现签名验证
- ✅ 添加资源限制
- ✅ 创建安全测试套件

---

_安全是每个人的责任。如有疑问，请查阅本文档或联系安全团队。_
