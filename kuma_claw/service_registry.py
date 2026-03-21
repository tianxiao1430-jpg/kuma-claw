"""
Kuma Claw - 服务状态注册表
========================
用于在 Web UI 和各渠道服务之间共享运行状态，
支持 /api/status 接口的实时状态查询。
"""

import time
from typing import Literal

ServiceStatus = Literal["connected", "error", "disabled", "starting"]

_registry: dict[str, dict] = {}


def set_status(service: str, status: ServiceStatus, message: str = ""):
    """设置服务状态"""
    _registry[service] = {
        "status": status,
        "message": message,
        "updated_at": time.time(),
    }


def get_status(service: str) -> ServiceStatus:
    """获取服务状态"""
    return _registry.get(service, {}).get("status", "disabled")


def get_all() -> dict[str, str]:
    """获取所有服务状态（返回简化的 {service: status} 字典）"""
    return {k: v["status"] for k, v in _registry.items()}
