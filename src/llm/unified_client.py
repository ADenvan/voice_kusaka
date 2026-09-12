from collections.abc import AsyncIterator
from typing import Any

import httpx
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from pydantic import SecretStr

from src.core.config import Config
from src.core.exceptions import LLMConnectionError, LLMTimeoutError


class UnifiedLLMClient:
    """Unified LLM client for Ollama and LM Studio using langchain-openai."""

    def __init__(self, config: Config) -> None:
        self._provider = config.llm_provider
        self._base_url = self._normalize_base_url(config.llm_base_url, config.llm_provider)
        self._model = config.llm_model
        self._api_key = config.llm_api_key
        self._temperature = config.llm_temperature
        self._max_tokens = config.llm_max_tokens
        self._timeout = config.llm_timeout

        self._llm = ChatOpenAI(
            base_url=self._base_url,
            openai_api_key=SecretStr(self._api_key),
            model=self._model,
            temperature=self._temperature,
            max_tokens=self._max_tokens,
            request_timeout=self._timeout,
        )

    def _normalize_base_url(self, base_url: str, provider: str) -> str:
        """Normalize base URL - add /v1 for Ollama if missing."""
        if provider == "ollama" and not base_url.rstrip("/").endswith("/v1"):
            return base_url.rstrip("/") + "/v1"
        return base_url

    async def chat_stream(self, messages: list[dict[str, str]]) -> AsyncIterator[str]:
        """Stream chat response token by token."""
        try:
            langchain_messages = self._convert_messages(messages)
            async for chunk in self._llm.astream(langchain_messages):
                content = chunk.content
                if isinstance(content, str) and content:
                    yield content
        except Exception as e:
            self._handle_error(e)

    async def chat(self, messages: list[dict[str, str]]) -> str:
        """Get complete chat response."""
        try:
            langchain_messages = self._convert_messages(messages)
            response = await self._llm.ainvoke(langchain_messages)
            content = response.content
            return content if isinstance(content, str) else ""
        except Exception as e:
            self._handle_error(e)
            return ""

    async def is_available(self) -> bool:
        """Check if LLM server is reachable."""
        try:
            health_url = self._get_health_endpoint()
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(health_url)
                return response.status_code == 200
        except (httpx.ConnectError, httpx.TimeoutException):
            return False

    async def list_models(self) -> list[str]:
        """List available models from LLM server."""
        try:
            models_url = self._get_models_endpoint()
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(models_url)
                response.raise_for_status()
                data: dict[str, Any] = response.json()
                return self._extract_model_names(data)
        except Exception:
            return []

    def _get_health_endpoint(self) -> str:
        """Get health check endpoint based on provider."""
        if self._provider == "ollama":
            base = self._base_url.replace("/v1", "")
            return f"{base}/api/tags"
        return f"{self._base_url}/models"

    def _get_models_endpoint(self) -> str:
        """Get models list endpoint based on provider."""
        if self._provider == "ollama":
            base = self._base_url.replace("/v1", "")
            return f"{base}/api/tags"
        return f"{self._base_url}/models"

    def _extract_model_names(self, data: dict[str, Any]) -> list[str]:
        """Extract model names from API response."""
        if self._provider == "ollama":
            return [m["name"] for m in data.get("models", [])]
        return [m["id"] for m in data.get("data", [])]

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

    def _handle_error(self, error: Exception) -> None:
        """Handle and convert exceptions to domain errors."""
        error_str = str(error).lower()
        if "connection" in error_str or "connect" in error_str:
            raise LLMConnectionError(
                f"Cannot reach {self._provider} at {self._base_url}"
            ) from error
        if "timeout" in error_str:
            raise LLMTimeoutError(
                f"{self._provider} timed out after {self._timeout}s"
            ) from error
        raise LLMConnectionError(f"{self._provider} error: {error}") from error


async def check_llm_health(config: Config) -> None:
    """Verify LLM server is running and model is available."""
    client = UnifiedLLMClient(config)
    if not await client.is_available():
        provider_name = "Ollama" if config.llm_provider == "ollama" else "LM Studio"
        start_cmd = (
            "ollama serve" if config.llm_provider == "ollama" else "сервер в LM Studio"
        )
        raise LLMConnectionError(
            f"{provider_name} не запущен. Запустите: {start_cmd}"
        )
    models = await client.list_models()
    if config.llm_model not in models:
        provider_name = "Ollama" if config.llm_provider == "ollama" else "LM Studio"
        if config.llm_provider == "ollama":
            install_cmd = f"Скачайте: ollama pull {config.llm_model}"
        else:
            install_cmd = "Загрузите модель через интерфейс LM Studio"
        raise LLMConnectionError(
            f"Модель '{config.llm_model}' не установлена в {provider_name}. {install_cmd}"
        )
