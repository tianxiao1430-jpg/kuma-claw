"""
Kuma Claw - 渠道基类
==================

所有渠道的公共逻辑（会话管理、Agent 运行）
支持基于输入动态注入工具
"""

import logging
from abc import ABC, abstractmethod

from google.adk.runners import Runner
from google.genai import types
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from ..agent import get_tools
from ..sessions import SQLiteSessionService

logger = logging.getLogger("kuma_claw.channels")


# ============================================
# 会话管理
# ============================================


class SessionManager:
    """统一的会话管理器（使用 SQLite 持久化）"""

    def __init__(self, app_name: str = "kuma-claw", db_path: str | None = None):
        self.app_name = app_name
        self.session_service = SQLiteSessionService(db_path=db_path)
        self.user_sessions: dict[str, str] = {}

    async def get_or_create_session(self, user_id: str, session_key: str | None = None) -> str:
        """获取或创建会话"""
        key = session_key or user_id
        if key not in self.user_sessions:
            try:
                sessions_response = await self.session_service.list_sessions(
                    app_name=self.app_name, user_id=user_id
                )
                existing_sessions = (
                    sessions_response.sessions if hasattr(sessions_response, "sessions") else []
                )

                if existing_sessions:
                    session = max(
                        existing_sessions, key=lambda s: getattr(s, "last_update_time", 0)
                    )
                    session_id = session.id if hasattr(session, "id") else str(session)
                    self.user_sessions[key] = session_id
                    logger.debug(f"复用已有会话：key={key}, session={session_id}")
                else:
                    session = await self.session_service.create_session(
                        app_name=self.app_name, user_id=user_id, state={}
                    )
                    session_id = session.id if hasattr(session, "id") else str(session)
                    self.user_sessions[key] = session_id
                    logger.debug(f"创建新会话：key={key}, session={session_id}")

            except Exception as e:
                logger.error(f"获取/创建会话失败：{e}")
                raise
        return self.user_sessions[key]

    async def clear_session(self, user_id: str, session_key: str | None = None) -> bool:
        """清除会话"""
        key = session_key or user_id
        if key in self.user_sessions:
            session_id = self.user_sessions[key]
            try:
                await self.session_service.delete_session(
                    app_name=self.app_name, user_id=user_id, session_id=session_id
                )
                del self.user_sessions[key]
                logger.debug(f"清除会话：key={key}")
                return True
            except Exception as e:
                logger.error(f"清除会话失败：{e}")
                return False
        return False

    async def close(self):
        """关闭会话服务"""
        await self.session_service.close()


# ============================================
# Agent 运行器
# ============================================


class LLMAPIError(Exception):
    """LLM API 调用异常"""

    pass


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type((LLMAPIError, TimeoutError)),
    reraise=True,
)
async def run_agent_with_session(
    runner: Runner,
    session_manager: SessionManager,
    user_id: str,
    parts: list[types.Part],
    session_key: str | None = None,
) -> str:
    """运行 Agent 并返回响应（带重试策略）"""
    try:
        session_id = await session_manager.get_or_create_session(
            user_id=user_id, session_key=session_key
        )

        content = types.Content(role="user", parts=parts)

        events = runner.run_async(session_id=session_id, user_id=user_id, new_message=content)

        response_text = ""
        async for event in events:
            if event.content and event.content.parts:
                for part in event.content.parts:
                    if part.text:
                        response_text += part.text
        if not response_text:
            raise LLMAPIError("LLM 返回空响应")
        return response_text
    except Exception as e:
        logger.error(f"运行 Agent 失败：{e}")
        raise LLMAPIError(f"LLM API 调用失败：{str(e)}") from e


async def run_agent_with_session_fallback(
    runner: Runner,
    session_manager: SessionManager,
    user_id: str,
    parts: list[types.Part],
    session_key: str | None = None,
) -> str:
    """运行 Agent 并返回响应（带重试和降级处理)"""
    try:
        return await run_agent_with_session(
            runner=runner,
            session_manager=session_manager,
            user_id=user_id,
            parts=parts,
            session_key=session_key,
        )
    except LLMAPIError as e:
        logger.error(f"LLM API 调用失败（重试耗尽): {e}")
        return "抱歉，服务暂时不可用，请稍后重试。"
    except Exception as e:
        logger.error(f"运行 Agent 失败：{e}")
        return f"处理请求时出错：{str(e)}"


# ============================================
# 渠道基类
# ============================================


class ChannelHandler(ABC):
    """渠道处理器基类"""

    def __init__(self, channel_name: str, agent, db_path: str | None = None):
        self.channel_name = channel_name
        self.agent = agent
        self.session_manager = SessionManager(db_path=db_path)

        self.runner = Runner(
            app_name="kuma-claw",
            agent=agent,
            session_service=self.session_manager.session_service,
        )

        logger.info(f"{channel_name} 渠道已初始化 (使用 SQLite 持久化会话)")

    @abstractmethod
    async def handle_message(self, user_id: str, text: str, **kwargs) -> str:
        """处理消息 (子类实现)"""
        pass

    @abstractmethod
    async def start(self):
        """启动渠道 (子类实现)"""
        pass

    @abstractmethod
    async def stop(self):
        """停止渠道 (子类实现)"""
        pass

    async def run_agent(
        self,
        user_id: str,
        text: str,
        images: list[tuple[bytes, str]] | None = None,
        session_key: str | None = None,
    ) -> str:
        """运行 Agent(公共逻辑)"""
        # 动态工具注入
        try:
            dynamic_tools = get_tools(text)
            self.agent.tools = dynamic_tools
            logger.debug(f"已为当前请求注入 {len(dynamic_tools)} 个工具")
        except Exception as e:
            logger.error(f"动态工具注入失败：{e}")

        parts = [types.Part(text=text)]

        # 添加图片
        if images:
            for img_bytes, mime_type in images:
                if not isinstance(img_bytes, bytes):
                    logger.warning(f"图片数据类型错误：{type(img_bytes)}, 跳过")
                    continue
                parts.append(
                    types.Part(inline_data=types.Blob(mime_type=mime_type, data=img_bytes))
                )

        # 获取 session_id
        session_id = await self.session_manager.get_or_create_session(
            user_id=user_id, session_key=session_key
        )

        # 记录用户消息到 session_messages
        try:
            from ..memory import memory_manager

            memory_manager.add_session_message(session_id, "user", text)
        except Exception as e:
            logger.error(f"记录用户消息失败：{e}")

        # 运行 Agent（ADK 会自动调用 append_event 持久化对话历史）
        response = await run_agent_with_session_fallback(
            runner=self.runner,
            session_manager=self.session_manager,
            user_id=user_id,
            parts=parts,
            session_key=session_key,
        )

        # 记录响应到 session_messages
        try:
            from ..memory import memory_manager

            memory_manager.add_session_message(session_id, "assistant", response)
        except Exception as e:
            logger.error(f"记录助手响应失败：{e}")

        return response

    async def cleanup(self):
        """清理资源 (在应用关闭时调用)"""
        await self.session_manager.close()
