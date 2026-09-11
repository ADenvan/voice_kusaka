import logging
from collections.abc import AsyncIterator
from typing import Any

import httpx
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_ollama import ChatOllama

from voice_ai.core.config import Config
from voice_ai.core.exceptions import LLMConnectionError, LLMTimeoutError

logger = logging.getLogger("voice_ai.llm")


class OllamaClient:
    def __init__(self, config: Config) -> None:
        self._base_url = config.ollama_base_url
        self._model = config.ollama_model
        self._timeout = config.ollama_timeout

        self._llm = ChatOllama(
            model=config.ollama_model,
            base_url=config.ollama_base_url,
            temperature=config.ollama_temperature,
            num_ctx=config.ollama_num_ctx,
            num_predict=config.ollama_num_predict,
        )

    async def chat_stream(self, messages: list[dict[str, str]]) -> AsyncIterator[str]:
        try:
            langchain_messages = self._convert_messages(messages)
            async for chunk in self._llm.astream(langchain_messages):
                content = chunk.content
                if isinstance(content, str) and content:
                    yield content
        except httpx.ConnectError as e:
            raise LLMConnectionError(f"Cannot reach Ollama at {self._base_url}") from e
        except httpx.TimeoutException as e:
            raise LLMTimeoutError(f"Ollama timed out after {self._timeout}s") from e
        except Exception as e:
            error_str = str(e).lower()
            if "connection" in error_str or "connect" in error_str:
                raise LLMConnectionError(f"Cannot reach Ollama at {self._base_url}") from e
            if "timeout" in error_str:
                raise LLMTimeoutError(f"Ollama timed out after {self._timeout}s") from e
            raise LLMConnectionError(f"Ollama error: {e}") from e

    async def chat(self, messages: list[dict[str, str]]) -> str:
        try:
            langchain_messages = self._convert_messages(messages)
            response = await self._llm.ainvoke(langchain_messages)
            content = response.content
            return content if isinstance(content, str) else ""
        except httpx.ConnectError as e:
            raise LLMConnectionError(f"Cannot reach Ollama at {self._base_url}") from e
        except httpx.TimeoutException as e:
            raise LLMTimeoutError(f"Ollama timed out after {self._timeout}s") from e
        except Exception as e:
            error_str = str(e).lower()
            if "connection" in error_str or "connect" in error_str:
                raise LLMConnectionError(f"Cannot reach Ollama at {self._base_url}") from e
            if "timeout" in error_str:
                raise LLMTimeoutError(f"Ollama timed out after {self._timeout}s") from e
            raise LLMConnectionError(f"Ollama error: {e}") from e

    async def is_available(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self._base_url}/api/tags")
                return response.status_code == 200
        except (httpx.ConnectError, httpx.TimeoutException):
            return False

    async def list_models(self) -> list[str]:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self._base_url}/api/tags")
                response.raise_for_status()
                data: dict[str, Any] = response.json()
                return [m["name"] for m in data.get("models", [])]
        except Exception:
            return []

    def _convert_messages(
        self, messages: list[dict[str, str]]
    ) -> list[SystemMessage | HumanMessage]:
        result: list[SystemMessage | HumanMessage] = []
        for msg in messages:
            role = msg.get("role", "")
            content = msg.get("content", "")
            if role == "system":
                result.append(SystemMessage(content=content))
            else:
                result.append(HumanMessage(content=content))
        return result


async def check_ollama_health(config: Config) -> None:
    client = OllamaClient(config)
    if not await client.is_available():
        raise LLMConnectionError(
            "Ollama не запущен. Запустите: ollama serve"
        )
    models = await client.list_models()
    if config.ollama_model not in models:
        raise LLMConnectionError(
            f"Модель '{config.ollama_model}' не установлена. "
            f"Скачайте: ollama pull {config.ollama_model}"
        )
