
import pytest

from src.core.config import Config
from src.core.exceptions import LLMConnectionError
from src.llm.prompt_builder import SYSTEM_PROMPT, PromptBuilder
from src.llm.unified_client import UnifiedLLMClient, check_llm_health


@pytest.fixture
def ollama_config() -> Config:
    return Config(
        _env_file=None,
        db_path=":memory:",
        llm_provider="ollama",
        llm_base_url="http://localhost:11434",
        llm_model="qwen2.5:7b",
        llm_api_key="ollama",
        llm_timeout=3,
    )


@pytest.fixture
def lmstudio_config() -> Config:
    return Config(
        _env_file=None,
        db_path=":memory:",
        llm_provider="lmstudio",
        llm_base_url="http://localhost:1234/v1",
        llm_model="qwen2.5-coder-7b-instruct",
        llm_api_key="lm-studio",
        llm_timeout=3,
    )


@pytest.fixture
def ollama_unreachable_config() -> Config:
    return Config(
        _env_file=None,
        db_path=":memory:",
        llm_provider="ollama",
        llm_base_url="http://localhost:59999",
        llm_model="qwen2.5:7b",
        llm_api_key="ollama",
        llm_timeout=3,
    )


@pytest.fixture
def lmstudio_unreachable_config() -> Config:
    return Config(
        _env_file=None,
        db_path=":memory:",
        llm_provider="lmstudio",
        llm_base_url="http://localhost:59998/v1",
        llm_model="qwen2.5-coder-7b-instruct",
        llm_api_key="lm-studio",
        llm_timeout=3,
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
async def test_ollama_is_available_unreachable(ollama_unreachable_config: Config) -> None:
    client = UnifiedLLMClient(ollama_unreachable_config)
    assert not await client.is_available()


@pytest.mark.asyncio
async def test_ollama_chat_connection_error(ollama_unreachable_config: Config) -> None:
    client = UnifiedLLMClient(ollama_unreachable_config)
    with pytest.raises(LLMConnectionError):
        await client.chat([{"role": "user", "content": "test"}])


@pytest.mark.asyncio
async def test_ollama_chat_stream_connection_error(ollama_unreachable_config: Config) -> None:
    client = UnifiedLLMClient(ollama_unreachable_config)
    with pytest.raises(LLMConnectionError):
        tokens = []
        async for token in client.chat_stream([{"role": "user", "content": "test"}]):
            tokens.append(token)


@pytest.mark.asyncio
async def test_check_llm_health_raises_ollama(ollama_unreachable_config: Config) -> None:
    with pytest.raises(LLMConnectionError):
        await check_llm_health(ollama_unreachable_config)


@pytest.mark.asyncio
async def test_lmstudio_is_available_unreachable(lmstudio_unreachable_config: Config) -> None:
    client = UnifiedLLMClient(lmstudio_unreachable_config)
    assert not await client.is_available()


@pytest.mark.asyncio
async def test_lmstudio_chat_connection_error(lmstudio_unreachable_config: Config) -> None:
    client = UnifiedLLMClient(lmstudio_unreachable_config)
    with pytest.raises(LLMConnectionError):
        await client.chat([{"role": "user", "content": "test"}])


@pytest.mark.asyncio
async def test_lmstudio_chat_stream_connection_error(lmstudio_unreachable_config: Config) -> None:
    client = UnifiedLLMClient(lmstudio_unreachable_config)
    with pytest.raises(LLMConnectionError):
        tokens = []
        async for token in client.chat_stream([{"role": "user", "content": "test"}]):
            tokens.append(token)


@pytest.mark.asyncio
async def test_check_llm_health_raises_lmstudio(lmstudio_unreachable_config: Config) -> None:
    with pytest.raises(LLMConnectionError):
        await check_llm_health(lmstudio_unreachable_config)


@pytest.mark.asyncio
async def test_lmstudio_list_models_empty(lmstudio_unreachable_config: Config) -> None:
    client = UnifiedLLMClient(lmstudio_unreachable_config)
    models = await client.list_models()
    assert models == []


def test_ollama_base_url_normalization() -> None:
    config = Config(
        _env_file=None,
        db_path=":memory:",
        llm_provider="ollama",
        llm_base_url="http://localhost:11434",
        llm_model="qwen2.5:7b",
        llm_api_key="ollama",
    )
    client = UnifiedLLMClient(config)
    assert client._base_url == "http://localhost:11434/v1"


def test_ollama_base_url_already_has_v1() -> None:
    config = Config(
        _env_file=None,
        db_path=":memory:",
        llm_provider="ollama",
        llm_base_url="http://localhost:11434/v1",
        llm_model="qwen2.5:7b",
        llm_api_key="ollama",
    )
    client = UnifiedLLMClient(config)
    assert client._base_url == "http://localhost:11434/v1"


def test_lmstudio_base_url_unchanged() -> None:
    config = Config(
        _env_file=None,
        db_path=":memory:",
        llm_provider="lmstudio",
        llm_base_url="http://localhost:1234/v1",
        llm_model="qwen2.5-coder-7b-instruct",
        llm_api_key="lm-studio",
    )
    client = UnifiedLLMClient(config)
    assert client._base_url == "http://localhost:1234/v1"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_ollama_is_available_integration(ollama_config: Config) -> None:
    client = UnifiedLLMClient(ollama_config)
    result = await client.is_available()
    assert isinstance(result, bool)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_lmstudio_is_available_integration(lmstudio_config: Config) -> None:
    client = UnifiedLLMClient(lmstudio_config)
    result = await client.is_available()
    assert isinstance(result, bool)
