import json
import logging
from collections.abc import AsyncIterator

import httpx

from src.core.config import Config
from src.core.exceptions import LLMConnectionError, LLMTimeoutError

logger = logging.getLogger("voice_ai.llm")


class OllamaClient:
    def __init__(self, config: Config) -> None:
        self._base_url = config.ollama_base_url
        self._model = config.ollama_model
        self._timeout = config.ollama_timeout
        self._temperature = config.ollama_temperature
        self._num_ctx = config.ollama_num_ctx
        self._num_predict = config.ollama_num_predict

    async def chat_stream(self, messages: list[dict]) -> AsyncIterator[str]:
        try:
            async with httpx.AsyncClient(
                timeout=self._timeout
            ) as client, client.stream(
                "POST",
                f"{self._base_url}/api/chat",
                json={
                    "model": self._model,
                    "messages": messages,
                    "stream": True,
                    "options": {
                        "temperature": self._temperature,
                        "num_ctx": self._num_ctx,
                        "num_predict": self._num_predict,
                    },
                },
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line.strip():
                        continue
                    chunk = json.loads(line)
                    content = chunk.get("message", {}).get("content", "")
                    if content:
                        yield content
                    if chunk.get("done", False):
                        return
        except httpx.ConnectError as e:
            raise LLMConnectionError(
                f"Cannot reach Ollama at {self._base_url}"
            ) from e
        except httpx.TimeoutException as e:
            raise LLMTimeoutError(
                f"Ollama timed out after {self._timeout}s"
            ) from e

    async def chat(self, messages: list[dict]) -> str:
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.post(
                    f"{self._base_url}/api/chat",
                    json={
                        "model": self._model,
                        "messages": messages,
                        "stream": False,
                        "options": {
                            "temperature": self._temperature,
                            "num_ctx": self._num_ctx,
                            "num_predict": self._num_predict,
                        },
                    },
                )
                response.raise_for_status()
                data = response.json()
                return data.get("message", {}).get("content", "")
        except httpx.ConnectError as e:
            raise LLMConnectionError(
                f"Cannot reach Ollama at {self._base_url}"
            ) from e
        except httpx.TimeoutException as e:
            raise LLMTimeoutError(
                f"Ollama timed out after {self._timeout}s"
            ) from e

    async def is_available(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self._base_url}/api/tags")
                return response.status_code == 200
        except (httpx.ConnectError, httpx.TimeoutException):
            return False

    async def list_models(self) -> list[str]:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{self._base_url}/api/tags")
            response.raise_for_status()
            data = response.json()
            return [m["name"] for m in data.get("models", [])]


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
