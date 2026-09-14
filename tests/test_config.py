from pydantic_core._pydantic_core import ValidationError

from src.core.config import Config


def test_config_defaults() -> None:
    c = Config(
        _env_file=None,
        db_path=":memory:",
    )
    assert c.sample_rate == 16000
    assert c.whisper_model == "large-v3"
    assert c.llm_model == "qwen2.5-coder-7b-instruct"
    assert c.silero_language == "ru"
    assert c.silero_speaker == "v5_ru"
    assert c.silero_voice == "baya"
    assert c.history_limit == 50


def test_config_custom_values(tmp_path: object) -> None:
    c = Config(
        _env_file=None,
        sample_rate=48000,
        whisper_model="base",
        llm_timeout=120,
        vad_threshold=0.8,
    )
    assert c.sample_rate == 48000
    assert c.whisper_model == "base"
    assert c.llm_timeout == 120
    assert c.vad_threshold == 0.8


def test_config_env_file(tmp_path: object) -> None:
    env_path = tmp_path / ".env"
    env_path.write_text("WHISPER_MODEL=base\nLLM_TIMEOUT=30\n")
    c = Config(_env_file=str(env_path), db_path=":memory:")
    assert c.whisper_model == "base"
    assert c.llm_timeout == 30


def test_config_rejects_invalid_vad_threshold() -> None:
    import pytest

    with pytest.raises(ValidationError):
        Config(_env_file=None, vad_threshold=-1.0)


def test_config_extra_fields_ignored(tmp_path: object) -> None:
    env_path = tmp_path / ".env"
    env_path.write_text("UNKNOWN_VAR=123\n")
    c = Config(_env_file=str(env_path), db_path=":memory:")
    assert not hasattr(c, "unknown_var")


def test_config_llm_provider_default() -> None:
    c = Config(_env_file=None, db_path=":memory:")
    assert c.llm_provider == "lmstudio"


def test_config_llm_provider_lmstudio() -> None:
    c = Config(_env_file=None, db_path=":memory:", llm_provider="lmstudio")
    assert c.llm_provider == "lmstudio"


def test_config_llm_base_url_default() -> None:
    c = Config(_env_file=None, db_path=":memory:")
    assert c.llm_base_url == "http://localhost:1234/v1"


def test_config_llm_api_key_default() -> None:
    c = Config(_env_file=None, db_path=":memory:")
    assert c.llm_api_key == "lmstudio"
