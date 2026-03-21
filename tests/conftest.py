"""Pytest 配置文件"""
import pytest
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


@pytest.fixture(scope="session")
def project_dir():
    """项目根目录"""
    return project_root


@pytest.fixture
def sample_text():
    """示例文本"""
    return "这是一个测试消息"


@pytest.fixture
def sample_user_id():
    """示例用户 ID"""
    return "test_user_123"


@pytest.fixture(autouse=True)
def reset_agent_cache():
    """自动重置 Agent 缓存（测试隔离）"""
    from kuma_claw.agent import reset_cache
    reset_cache()
    yield
    reset_cache()


@pytest.fixture(autouse=True)
def reset_config():
    """自动重置配置（测试隔离）"""
    from kuma_claw import config as config_module
    original_config = config_module.config
    yield
    config_module.config = original_config
