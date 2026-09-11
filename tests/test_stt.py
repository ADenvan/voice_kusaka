import numpy as np
import pytest

from voice_ai.core.exceptions import EmptyTranscriptionError, STTError
from voice_ai.stt.whisper_engine import FasterWhisperEngine


class _FakeSegment:
    def __init__(self, text: str) -> None:
        self.text = text


class _FakeWhisperModel:
    def __init__(self, text: str = "Привет") -> None:
        self._text = text

    def transcribe(self, audio: np.ndarray, language: str = "ru") -> tuple:
        if len(audio) == 0:
            return ([], None)
        return ([_FakeSegment(self._text)], None)


@pytest.fixture
def engine_with_mock(tmp_path: object) -> FasterWhisperEngine:
    from voice_ai.core.config import Config

    config = Config(
        _env_file=None,
        db_path=":memory:",
        whisper_model="tiny",
        whisper_device="cpu",
        whisper_compute_type="int8",
    )
    return FasterWhisperEngine(config)


@pytest.mark.asyncio
async def test_transcribe_empty_audio_raises(
    engine_with_mock: FasterWhisperEngine,
) -> None:
    engine_with_mock._model = _FakeWhisperModel("")
    with pytest.raises(EmptyTranscriptionError):
        await engine_with_mock.transcribe(np.array([], dtype=np.float32))


@pytest.mark.asyncio
async def test_transcribe_returns_text(
    engine_with_mock: FasterWhisperEngine,
) -> None:
    engine_with_mock._model = _FakeWhisperModel("Привет мир")
    audio = np.ones(16000, dtype=np.float32)
    result = await engine_with_mock.transcribe(audio)
    assert result == "Привет мир"


@pytest.mark.asyncio
async def test_transcribe_stt_error(
    engine_with_mock: FasterWhisperEngine,
) -> None:
    class _BrokenModel:
        def transcribe(self, audio, language="ru"):
            raise RuntimeError("GPU OOM")

    engine_with_mock._model = _BrokenModel()
    audio = np.ones(16000, dtype=np.float32)
    with pytest.raises(STTError):
        await engine_with_mock.transcribe(audio)
