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

from ..agent import get_tools  # 导入动态资源获取函数
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
        self.user_sessions: dict[str, str] = {}  # session_key -> session_id

    async def get_or_create_session(self, user_id: str, session_key: str | None = None) -> str:
        """获取或创建会话

        Args:
            user_id: 用户 ID
            session_key: 会话键（可选）
                        - 格式："{user_id}:{channel}:{thread_id}"
                        - 不传则使用 user_id 作为键

        Returns:
            会话 ID
        """
        # 使用 session_key 或 user_id 作为键
        key = session_key or user_id
        if key not in self.user_sessions:
            try:
                # 先尝试从 SQLite 查找已有会话（支持 bot 重启后会话复用）
                sessions_response = await self.session_service.list_sessions(
                    app_name=self.app_name, user_id=user_id
                )
                existing_sessions = sessions_response.sessions if hasattr(sessions_response, 'sessions') else []
                
                if existing_sessions:
                    # 复用最新的会话
                    session = max(existing_sessions, key=lambda s: getattr(s, 'last_update_time', 0))
                    session_id = session.id if hasattr(session, "id") else str(session)
                    self.user_sessions[key] = session_id
                    logger.debug(f"复用已有会话：key={key}, session={session_id}")
                else:
                    # 创建新会话
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
        """清除会话

        Args:
            user_id: 用户 ID
            session_key: 会话键（可选）

        Returns:
            是否成功
        """
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
    """运行 Agent 并返回响应（带重试和降级处理)

    这是 run_agent_with_session 的包装器，在重试失败后返回友好的错误消息。

    Args:
        runner: ADK Runner 实例
        session_manager: 会话管理器
        user_id: 用户 ID
        parts: 消息部分列表
        session_key: 会话键（可选）

    Returns:
        Agent 响应文本或错误消息
    """
    try:
        return await run_agent_with_session(
            runner=runner,
            session_manager=session_manager,
            user_id=user_id,
            parts=full_parts,
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

        # 创建 Runner（使用持久化会话服务)
        self.runner = Runner(
            app_name="kuma-claw",
            agent=agent,
            session_service=self.session_manager.session_service,
        )

        logger.info(f"{channel_name} 渠道已初始化 (使用 SQLite 持久化会话)")

    @abstractmethod
    async def handle_message(self, user_id: str, text: str, **kwargs) -> str:
        """处理消息 (子类实现)

        Args:
            user_id: 用户 ID
            text: 消息文本
            **kwargs: 渠道特定参数

        Returns:
            响应文本
        """
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
        """运行 Agent(公共逻辑)

        Args:
            user_id: 用户 ID
            text: 消息文本
            images: 图片列表，格式为 [(bytes, mime_type), ...]
            session_key: 会话键（可选)
                        - 用于隔离不同会话的上下文
                        - 格式建议："{user_id}:{channel}:{thread_id}"

        Returns:
            Agent 响应
        """
        # --- 动态工具注入逻辑 ---
        try:
            # 根据用户输入检索相关工具
            dynamic_tools = get_tools(text)
            # 更新 Agent 的工具列表
            self.agent.tools = dynamic_tools
            logger.debug(f"已为当前请求注入 {len(dynamic_tools)} 个工具")
        except Exception as e:
            logger.error(f"动态工具注入失败：{e}")
        # -----------------------

        parts = [types.Part(text=text)]

        # 添加图片 (如果有)
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

        # 从 memory.db 加载历史消息（恢复对话上下文）
        history_parts = []
        try:
            from ..memory import memory_manager
            history = memory_manager.get_session_messages(session_id, limit=20)
            if history:
                for msg in history:
                    role = "user" if msg["role"] == "user" else "model"
                    history_parts.append(types.Part(text=f"{role}: {msg['content']}"))
                logger.info(f"加载了 {len(history)} 条历史消息")
        except Exception as e:
            logger.error(f"加载历史消息失败：{e}")

        # --- 记录会话到记忆库 (SQLite) ---
        try:
            from ..memory import memory_manager
            memory_manager.add_session_message(session_id, "user", text)
        except Exception as e:
            logger.error(f"记录用户消息失败：{e}")
        # ------------------------------

        # 构建完整的消息 parts（历史 + 当前）
        full_parts = history_parts + parts

        response = await run_agent_with_session_fallback(
            runner=self.runner,
            session_manager=self.session_manager,
            user_id=user_id,
            parts=full_parts,
            session_key=session_key,
        )

        # --- 记录响应到记忆库 (SQLite) ---
        try:
            from ..memory import memory_manager
            memory_manager.add_session_message(session_id, "assistant", response)
        except Exception as e:
            logger.error(f"记录助手响应失败：{e}")
        # ------------------------------

        # 手动更新 session state（ADK 可能不会自动保存）
        try:
            await self.session_service.update_session(
                app_name="kuma-claw",
                user_id=user_id,
                session_id=session_id,
                state={"last_message": response}
            )
            logger.info(f"手动更新 session state: {session_id}")
        except Exception as e:
            logger.error(f"手动更新 session 失败：{e}")

        return response


    async def cleanup(self):
        """清理资源 (在应用关闭时调用)"""
        await self.session_manager.close()
