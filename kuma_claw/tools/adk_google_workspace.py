"""
Kuma Claw - Google Workspace 工具集
==================================

使用 ADK 内置的 GoogleApiToolset。
"""

import logging
import os

from google.adk.tools.base_toolset import BaseToolset

# 配置日志
logger = logging.getLogger("kuma_claw.google_workspace")

try:
    from google.adk.tools.google_api_tool import (
        BigQueryToolset,
        CalendarToolset,
        DocsToolset,
        GmailToolset,
        SheetsToolset,
        YoutubeToolset,
    )

    ADK_TOOLSETS_AVAILABLE = True
except ImportError as e:
    logger.warning(f"ADK GoogleApiToolset 不可用: {e}")
    ADK_TOOLSETS_AVAILABLE = False

try:
    from ..config import config
except ImportError:
    config = None


def get_oauth_credentials() -> tuple[str | None, str | None]:
    """获取 OAuth 凭证

    Returns:
        (client_id, client_secret) 元组
    """
    client_id = None
    client_secret = None

    # 从配置获取
    if config:
        client_id = config.get_google_oauth_client_id()
        client_secret = config.get_google_oauth_client_secret()

    # 环境变量后备
    if not client_id:
        client_id = os.environ.get("GOOGLE_OAUTH_CLIENT_ID")
    if not client_secret:
        client_secret = os.environ.get("GOOGLE_OAUTH_CLIENT_SECRET")

    return client_id, client_secret


def _create_toolset(
    toolset_class,
    tool_name: str,
    tool_filter: list[str] | None = None,
    tool_name_prefix: str = None,
) -> BaseToolset | None:
    """创建工具集的通用工厂函数

    Args:
        toolset_class: 工具集类（如 GmailToolset）
        tool_name: 工具集名称（用于日志）
        tool_filter: 工具过滤器
        tool_name_prefix: 工具名称前缀

    Returns:
        工具集实例或 None
    """
    if not ADK_TOOLSETS_AVAILABLE:
        logger.debug(f"{tool_name} 工具集不可用：ADK 未安装")
        return None

    client_id, client_secret = get_oauth_credentials()

    if not client_id or not client_secret:
        logger.debug(f"{tool_name} 工具集未配置：缺少 OAuth 凭证")
        return None

    try:
        toolset = toolset_class(
            client_id=client_id,
            client_secret=client_secret,
            tool_filter=tool_filter,
            tool_name_prefix=tool_name_prefix or tool_name.lower(),
        )
        logger.info(f"{tool_name} 工具集已加载")
        return toolset
    except Exception as e:
        logger.error(f"创建 {tool_name} 工具集失败: {e}")
        return None


def create_gmail_toolset(
    tool_filter: list[str] | None = None, tool_name_prefix: str = "gmail"
) -> BaseToolset | None:
    """创建 Gmail 工具集

    Args:
        tool_filter: 工具过滤器（如 ["messages_send", "messages_list"]）
        tool_name_prefix: 工具名称前缀

    Returns:
        GmailToolset 或 None
    """
    return _create_toolset(
        GmailToolset,
        "Gmail",
        tool_filter=tool_filter,
        tool_name_prefix=tool_name_prefix,
    )


def create_calendar_toolset(
    tool_filter: list[str] | None = None, tool_name_prefix: str = "calendar"
) -> BaseToolset | None:
    """创建 Calendar 工具集"""
    return _create_toolset(
        CalendarToolset,
        "Calendar",
        tool_filter=tool_filter,
        tool_name_prefix=tool_name_prefix,
    )


def create_sheets_toolset(
    tool_filter: list[str] | None = None, tool_name_prefix: str = "sheets"
) -> BaseToolset | None:
    """创建 Sheets 工具集"""
    return _create_toolset(
        SheetsToolset,
        "Sheets",
        tool_filter=tool_filter,
        tool_name_prefix=tool_name_prefix,
    )


def create_docs_toolset(
    tool_filter: list[str] | None = None, tool_name_prefix: str = "docs"
) -> BaseToolset | None:
    """创建 Docs 工具集"""
    return _create_toolset(
        DocsToolset,
        "Docs",
        tool_filter=tool_filter,
        tool_name_prefix=tool_name_prefix,
    )


def create_all_google_workspace_toolsets() -> list[BaseToolset]:
    """创建所有 Google Workspace 工具集

    Returns:
        工具集列表
    """
    toolsets = []

    # Gmail - 常用工具
    gmail = create_gmail_toolset(
        tool_filter=[
            "messages_send",
            "messages_list",
            "messages_get",
            "drafts_create",
            "labels_list",
        ]
    )
    if gmail:
        toolsets.append(gmail)

    # Calendar - 常用工具
    calendar = create_calendar_toolset(
        tool_filter=[
            "events_list",
            "events_get",
            "events_insert",
            "events_update",
            "events_delete",
            "calendar_list_list",
        ]
    )
    if calendar:
        toolsets.append(calendar)

    # Sheets - 常用工具
    sheets = create_sheets_toolset(
        tool_filter=[
            "spreadsheets_get",
            "spreadsheets_create",
            "values_get",
            "values_update",
            "values_append",
            "values_clear",
        ]
    )
    if sheets:
        toolsets.append(sheets)

    # Docs - 常用工具
    docs = create_docs_toolset(
        tool_filter=[
            "documents_get",
            "documents_create",
        ]
    )
    if docs:
        toolsets.append(docs)

    return toolsets


def check_google_workspace_status() -> str:
    """检查 Google Workspace 工具集状态

    Returns:
        状态信息字符串
    """
    if not ADK_TOOLSETS_AVAILABLE:
        return "❌ ADK GoogleApiToolset 不可用\n\n需要安装: pip install google-adk>=0.1.0"

    client_id, client_secret = get_oauth_credentials()

    if not client_id or not client_secret:
        return """❌ Google OAuth 未配置

配置步骤:
1. 前往 Google Cloud Console (https://console.cloud.google.com)
2. 创建 OAuth 2.0 客户端 ID（Desktop app 类型）
3. 配置凭证:
   - 运行: kuma-claw config --section oauth
   - 或设置环境变量:
     GOOGLE_OAUTH_CLIENT_ID=your_client_id
     GOOGLE_OAUTH_CLIENT_SECRET=your_client_secret
"""

    return "✅ Google Workspace 工具集可用\n\n可用服务: Gmail, Calendar, Sheets, Docs"
