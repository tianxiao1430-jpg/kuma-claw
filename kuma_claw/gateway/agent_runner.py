"""
Kuma Claw Gateway - Agent Runner
=================================

Safely runs the ADK agent per-session with concurrency protection,
dynamic tool injection, and retry logic.
"""

import asyncio
import copy
import logging

from google.adk.agents import LlmAgent
from google.adk.runners import Runner
from google.genai import types
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from kuma_claw.agent import get_tools

from .session_manager import SessionKey, UnifiedSessionManager

logger = logging.getLogger("kuma_claw.gateway")


class LLMAPIError(Exception):
    """LLM API call error."""

    pass


class AgentRunner:
    """Runs the ADK agent per-session with locking and retry."""

    def __init__(self, agent: LlmAgent, session_manager: UnifiedSessionManager):
        self.agent = agent
        self.session_manager = session_manager
        self._runner = Runner(
            app_name="kuma-claw",
            agent=agent,
            session_service=session_manager.session_service,
        )
        self._locks: dict[str, asyncio.Lock] = {}

    def _get_lock(self, key: SessionKey) -> asyncio.Lock:
        """Get or create a per-session lock."""
        key_str = str(key)
        if key_str not in self._locks:
            self._locks[key_str] = asyncio.Lock()
        return self._locks[key_str]

    async def run(
        self,
        session_key: SessionKey,
        text: str,
        images: list[tuple[bytes, str]] | None = None,
    ) -> str:
        """Run the agent for a message. Returns the response text.

        Acquires a per-session lock to prevent concurrent runs on the same session.
        On failure (after retries), returns a user-friendly error message.
        """
        lock = self._get_lock(session_key)
        async with lock:
            try:
                return await self._run_with_retry(session_key, text, images)
            except LLMAPIError as e:
                logger.error(f"LLM API call failed (retries exhausted): {e}")
                return "Sorry, the service is temporarily unavailable. Please try again later."
            except (RuntimeError, ValueError, asyncio.CancelledError) as e:
                logger.error(f"Agent run failed: {e}")
                return f"An error occurred while processing your request: {e}"

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((LLMAPIError, TimeoutError)),
        reraise=True,
    )
    async def _run_with_retry(
        self,
        session_key: SessionKey,
        text: str,
        images: list[tuple[bytes, str]] | None = None,
    ) -> str:
        """Core run logic with tenacity retry."""
        try:
            # Dynamic tool injection on a copy of the agent
            agent_copy = copy.copy(self.agent)
            try:
                dynamic_tools = get_tools(text)
                agent_copy.tools = dynamic_tools
                logger.debug(f"Injected {len(dynamic_tools)} tools for request")
            except (RuntimeError, ValueError, asyncio.CancelledError) as e:
                logger.error(f"Dynamic tool injection failed: {e}")

            # Build message parts
            parts = [types.Part(text=text)]
            if images:
                for img_bytes, mime_type in images:
                    if not isinstance(img_bytes, bytes):
                        logger.warning(f"Skipping non-bytes image data: {type(img_bytes)}")
                        continue
                    parts.append(
                        types.Part(inline_data=types.Blob(mime_type=mime_type, data=img_bytes))
                    )

            # Get or create session
            session_id = await self.session_manager.get_or_create(session_key)

            # Run via ADK Runner
            content = types.Content(role="user", parts=parts)
            events = self._runner.run_async(
                session_id=session_id,
                user_id=session_key.user_id,
                new_message=content,
            )

            response_text = ""
            async for event in events:
                if event.content and event.content.parts:
                    for part in event.content.parts:
                        if part.text:
                            response_text += part.text

            if not response_text:
                raise LLMAPIError("LLM returned empty response")

            return response_text

        except LLMAPIError:
            raise
        except TimeoutError:
            raise
        except (RuntimeError, ValueError, OSError) as e:
            logger.error(f"Agent run error: {e}")
            raise LLMAPIError(f"LLM API call failed: {e}") from e
