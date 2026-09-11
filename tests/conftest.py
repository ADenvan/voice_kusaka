from unittest.mock import AsyncMock, MagicMock

import numpy as np
import pytest

from voice_ai.core.config import Config


@pytest.fixture
def mock_config(tmp_path: object) -> Config:
    env_path = tmp_path / ".env"
    env_path.write_text("")
    return Config(
        _env_file=str(env_path),
        db_path=str(tmp_path / "test.db"),
        whisper_model="tiny",
        whisper_device="cpu",
        whisper_compute_type="int8",
    )


@pytest.fixture
def silence_chunk() -> np.ndarray:
    return np.zeros(8000, dtype=np.float32)


@pytest.fixture
def speech_chunk() -> np.ndarray:
    rng = np.random.default_rng(42)
    return (rng.standard_normal(8000) * 0.3).astype(np.float32)


@pytest.fixture
def mock_stt() -> MagicMock:
    stt = MagicMock()
    stt.transcribe = AsyncMock(return_value="Привет")
    return stt


@pytest.fixture
def mock_llm() -> MagicMock:
    async def _stream(messages: list[dict]) -> object:
        for token in ["Привет", "!"]:
            yield token

    llm = MagicMock()
    llm.chat_stream = _stream
    llm.chat = AsyncMock(return_value="Привет!")
    llm.is_available = AsyncMock(return_value=True)
    return llm


@pytest.fixture
def mock_tts() -> MagicMock:
    tts = MagicMock()
    audio = np.zeros(48000, dtype=np.float32)
    tts.synthesize = AsyncMock(return_value=audio)
    return tts


@pytest.fixture
def mock_audio_in() -> MagicMock:
    audio_in = MagicMock()
    audio_in.start = AsyncMock(return_value=None)
    audio_in.stop = AsyncMock(return_value=None)
    audio_in.record_utterance = AsyncMock(
        return_value=np.ones(16000, dtype=np.float32)
    )
    return audio_in


@pytest.fixture
def mock_audio_out() -> MagicMock:
    audio_out = MagicMock()
    audio_out.play = AsyncMock(return_value=None)
    audio_out.interrupt = MagicMock()
    audio_out.stop = AsyncMock(return_value=None)
    return audio_out


@pytest.fixture
def mock_vad() -> MagicMock:
    vad = MagicMock()
    vad.is_speech = MagicMock(return_value=True)
    vad.get_speech_prob = MagicMock(return_value=0.9)
    return vad


@pytest.fixture
def mock_memory() -> MagicMock:
    memory = MagicMock()
    memory.create_session = AsyncMock(return_value="test-session")
    memory.save_message = AsyncMock(return_value=None)
    memory.get_history = AsyncMock(return_value=[])
    memory.delete_session = AsyncMock(return_value=None)
    return memory


@pytest.fixture
def mock_wake_word() -> MagicMock:
    wake = MagicMock()
    wake.detect = AsyncMock(return_value=True)
    wake.load = MagicMock()
    wake.reset_cooldown = MagicMock()
    return wake
