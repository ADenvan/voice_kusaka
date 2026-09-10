import logging
from collections.abc import AsyncIterator
from typing import Any

import httpx
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from pydantic import SecretStr

from src.core.config import Config
from src.core.exceptions import LLMConnectionError, LLMTimeoutError

logger = logging.getLogger("voice_ai.lmstudio")


class LMStudioClient:
    """LM Studio client using langchain_openai."""

    def __init__(self, config: Config) -> None:
        self._base_url = config.lmstudio_base_url
        self._model = config.lmstudio_model
        self._api_key = config.lmstudio_api_key
        self._temperature = config.lmstudio_temperature
        self._max_tokens = config.lmstudio_max_tokens
        self._timeout = config.lmstudio_timeout

        self._llm = ChatOpenAI(
            base_url=self._base_url,
            openai_api_key=SecretStr(self._api_key),
            model=self._model,
            temperature=self._temperature,
            max_tokens=self._max_tokens,  # type: ignore[call-arg]
            request_timeout=self._timeout,
        )

    async def chat_stream(self, messages: list[dict[str, str]]) -> AsyncIterator[str]:
        """Stream chat response token by token."""
        try:
            langchain_messages = self._convert_messages(messages)
            async for chunk in self._llm.astream(langchain_messages):
                content = chunk.content
                if isinstance(content, str) and content:
                    yield content
        except Exception as e:
            error_str = str(e).lower()
            if "connection" in error_str or "connect" in error_str:
                raise LLMConnectionError(f"Cannot reach LM Studio at {self._base_url}") from e
            if "timeout" in error_str:
                raise LLMTimeoutError(f"LM Studio timed out after {self._timeout}s") from e
            raise LLMConnectionError(f"LM Studio error: {e}") from e

    async def chat(self, messages: list[dict[str, str]]) -> str:
        """Get complete chat response."""
        try:
            langchain_messages = self._convert_messages(messages)
            response = await self._llm.ainvoke(langchain_messages)
            content = response.content
            return content if isinstance(content, str) else ""
        except Exception as e:
            error_str = str(e).lower()
            if "connection" in error_str or "connect" in error_str:
                raise LLMConnectionError(f"Cannot reach LM Studio at {self._base_url}") from e
            if "timeout" in error_str:
                raise LLMTimeoutError(f"LM Studio timed out after {self._timeout}s") from e
            raise LLMConnectionError(f"LM Studio error: {e}") from e

    async def is_available(self) -> bool:
        """Check if LM Studio server is reachable."""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self._base_url}/models")
                return response.status_code == 200
        except (httpx.ConnectError, httpx.TimeoutException):
            return False

    async def list_models(self) -> list[str]:
        """List available models from LM Studio."""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self._base_url}/models")
                response.raise_for_status()
                data: dict[str, Any] = response.json()
                return [m["id"] for m in data.get("data", [])]
        except Exception:
            return []

    def _convert_messages(
        self, messages: list[dict[str, str]]
    ) -> list[SystemMessage | HumanMessage]:
        """Convert dict messages to langchain message objects."""
        result: list[SystemMessage | HumanMessage] = []
        for msg in messages:
            role = msg.get("role", "")
            content = msg.get("content", "")
            if role == "system":
                result.append(SystemMessage(content=content))
            else:
                result.append(HumanMessage(content=content))
        return result


async def check_lmstudio_health(config: Config) -> None:
    """Verify LM Studio is running and model is available."""
    client = LMStudioClient(config)
    if not await client.is_available():
        raise LLMConnectionError("LM Studio не запущен. Запустите сервер в LM Studio.")
    models = await client.list_models()
    if config.lmstudio_model not in models:
        raise LLMConnectionError(
            f"Модель '{config.lmstudio_model}' не загружена в LM Studio. "
            f"Загрузите модель через интерфейс LM Studio."
        )
