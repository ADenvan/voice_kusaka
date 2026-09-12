
import pytest

from src.core.config import Config
from src.core.exceptions import LLMConnectionError
from src.llm.lmstudio_client import LMStudioClient, check_lmstudio_health
from src.llm.ollama_client import OllamaClient, check_ollama_health
from src.llm.prompt_builder import SYSTEM_PROMPT, PromptBuilder


@pytest.fixture
def config() -> Config:
    return Config(
        _env_file=None,
        db_path=":memory:",
        ollama_base_url="http://localhost:99999",
        ollama_timeout=3,
    )


@pytest.fixture
def lmstudio_config() -> Config:
    return Config(
        _env_file=None,
        db_path=":memory:",
        lmstudio_base_url="http://localhost:99998/v1",
        lmstudio_timeout=3,
    )


def test_prompt_builder_default() -> None:
    builder = PromptBuilder()
    messages = builder.build_messages([{"role": "user", "content": "Привет"}])
    assert messages[0]["role"] == "system"
    assert messages[0]["content"] == SYSTEM_PROMPT
    assert messages[1]["role"] == "user"


def test_prompt_builder_custom_system() -> None:
    builder = PromptBuilder(system_prompt="Custom")
    messages = builder.build_messages([])
    assert messages[0]["content"] == "Custom"


@pytest.mark.asyncio
async def test_is_available_unreachable(config: Config) -> None:
    client = OllamaClient(config)
    assert not await client.is_available()


@pytest.mark.asyncio
async def test_chat_connection_error(config: Config) -> None:
    client = OllamaClient(config)
    with pytest.raises(LLMConnectionError):
        await client.chat([{"role": "user", "content": "test"}])


@pytest.mark.asyncio
async def test_chat_stream_connection_error(config: Config) -> None:
    client = OllamaClient(config)
    with pytest.raises(LLMConnectionError):
        tokens = []
        async for token in client.chat_stream([{"role": "user", "content": "test"}]):
            tokens.append(token)


@pytest.mark.asyncio
async def test_check_ollama_health_raises(config: Config) -> None:
    with pytest.raises(LLMConnectionError):
        await check_ollama_health(config)


@pytest.mark.asyncio
async def test_lmstudio_is_available_unreachable(lmstudio_config: Config) -> None:
    client = LMStudioClient(lmstudio_config)
    assert not await client.is_available()


@pytest.mark.asyncio
async def test_lmstudio_chat_connection_error(lmstudio_config: Config) -> None:
    client = LMStudioClient(lmstudio_config)
    with pytest.raises(LLMConnectionError):
        await client.chat([{"role": "user", "content": "test"}])


@pytest.mark.asyncio
async def test_lmstudio_chat_stream_connection_error(lmstudio_config: Config) -> None:
    client = LMStudioClient(lmstudio_config)
    with pytest.raises(LLMConnectionError):
        tokens = []
        async for token in client.chat_stream([{"role": "user", "content": "test"}]):
            tokens.append(token)


@pytest.mark.asyncio
async def test_check_lmstudio_health_raises(lmstudio_config: Config) -> None:
    with pytest.raises(LLMConnectionError):
        await check_lmstudio_health(lmstudio_config)


@pytest.mark.asyncio
async def test_lmstudio_list_models_empty(lmstudio_config: Config) -> None:
    client = LMStudioClient(lmstudio_config)
    models = await client.list_models()
    assert models == []
