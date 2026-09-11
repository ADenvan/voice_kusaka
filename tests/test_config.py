from pydantic_core._pydantic_core import ValidationError

from voice_ai.core.config import Config


def test_config_defaults() -> None:
    c = Config(
        _env_file=None,
        db_path=":memory:",
    )
    assert c.sample_rate == 16000
    assert c.whisper_model == "large-v3"
    assert c.ollama_model == "qwen2.5:7b"
    assert c.silero_language == "ru"
    assert c.silero_speaker == "v5_ru"
    assert c.silero_voice == "baya"
    assert c.history_limit == 50


def test_config_custom_values(tmp_path: object) -> None:
    c = Config(
        _env_file=None,
        sample_rate=48000,
        whisper_model="base",
        ollama_timeout=120,
        vad_threshold=0.8,
    )
    assert c.sample_rate == 48000
    assert c.whisper_model == "base"
    assert c.ollama_timeout == 120
    assert c.vad_threshold == 0.8


def test_config_env_file(tmp_path: object) -> None:
    env_path = tmp_path / ".env"
    env_path.write_text("WHISPER_MODEL=base\nOLLAMA_TIMEOUT=30\n")
    c = Config(_env_file=str(env_path), db_path=":memory:")
    assert c.whisper_model == "base"
    assert c.ollama_timeout == 30


def test_config_rejects_invalid_vad_threshold() -> None:
    import pytest

    with pytest.raises(ValidationError):
        Config(_env_file=None, vad_threshold=-1.0)


def test_config_extra_fields_ignored(tmp_path: object) -> None:
    env_path = tmp_path / ".env"
    env_path.write_text("UNKNOWN_VAR=123\n")
    c = Config(_env_file=str(env_path), db_path=":memory:")
    assert not hasattr(c, "unknown_var")
