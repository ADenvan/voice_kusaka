import pytest

from src.core.config import Config
from src.llm.prompt_builder import SYSTEM_PROMPT, PromptBuilder
from src.memory.context import ContextManager
from src.memory.database import SQLiteStore


def test_trim_history_no_trim_needed() -> None:
    mgr = ContextManager(max_messages=50)
    msgs = [{"role": "system", "content": "sys"}] + [
        {"role": "user", "content": f"msg{i}"} for i in range(10)
    ]
    assert mgr.trim_history(msgs) == msgs


def test_trim_history_trims_correctly() -> None:
    mgr = ContextManager(max_messages=5)
    msgs = [{"role": "system", "content": "sys"}] + [
        {"role": "user", "content": f"msg{i}"} for i in range(20)
    ]
    result = mgr.trim_history(msgs)
    assert result[0]["role"] == "system"
    assert len(result) == 6
    assert result[1]["content"] == "msg15"


def test_trim_history_no_system_prompt() -> None:
    mgr = ContextManager(max_messages=5)
    msgs = [{"role": "user", "content": f"msg{i}"} for i in range(10)]
    result = mgr.trim_history(msgs)
    assert len(result) == 5
    assert result[0]["content"] == "msg5"


def test_estimate_tokens() -> None:
    assert ContextManager.estimate_tokens("Привет") == 2
    assert ContextManager.estimate_tokens("") == 0
    assert ContextManager.estimate_tokens("a" * 30) == 10


def test_prompt_builder_builds_messages() -> None:
    builder = PromptBuilder()
    history = [
        {"role": "user", "content": "Привет"},
        {"role": "assistant", "content": "Здравствуйте!"},
    ]
    messages = builder.build_messages(history)
    assert len(messages) == 3
    assert messages[0]["role"] == "system"
    assert messages[0]["content"] == SYSTEM_PROMPT
    assert messages[1]["role"] == "user"
    assert messages[2]["role"] == "assistant"


def test_prompt_builder_custom_system_prompt() -> None:
    builder = PromptBuilder(system_prompt="Custom prompt")
    messages = builder.build_messages([])
    assert messages[0]["content"] == "Custom prompt"


def test_prompt_builder_empty_history() -> None:
    builder = PromptBuilder()
    messages = builder.build_messages([])
    assert len(messages) == 1
    assert messages[0]["role"] == "system"


@pytest.fixture
async def store(tmp_path: object) -> SQLiteStore:
    c = Config(_env_file=None, db_path=str(tmp_path / "test.db"))
    s = SQLiteStore(c)
    yield s
    await s.close()


class TestSQLiteStore:
    @pytest.mark.asyncio
    async def test_create_session(self, store: SQLiteStore) -> None:
        session_id = await store.create_session()
        assert session_id
        assert "T" in session_id

    @pytest.mark.asyncio
    async def test_save_and_get_history(self, store: SQLiteStore) -> None:
        session_id = await store.create_session()
        await store.save_message(session_id, "user", "Привет")
        await store.save_message(session_id, "assistant", "Здравствуйте!")
        history = await store.get_history(session_id)
        assert len(history) == 2
        assert history[0]["role"] == "user"
        assert history[0]["content"] == "Привет"
        assert history[1]["role"] == "assistant"

    @pytest.mark.asyncio
    async def test_get_history_limit(self, store: SQLiteStore) -> None:
        session_id = await store.create_session()
        for i in range(10):
            await store.save_message(session_id, "user", f"msg{i}")
        history = await store.get_history(session_id, limit=3)
        assert len(history) == 3

    @pytest.mark.asyncio
    async def test_delete_session(self, store: SQLiteStore) -> None:
        session_id = await store.create_session()
        await store.save_message(session_id, "user", "test")
        await store.delete_session(session_id)
        history = await store.get_history(session_id)
        assert len(history) == 0

    @pytest.mark.asyncio
    async def test_empty_history(self, store: SQLiteStore) -> None:
        session_id = await store.create_session()
        history = await store.get_history(session_id)
        assert history == []
