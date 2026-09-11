from unittest.mock import AsyncMock, MagicMock, patch

import numpy as np
import pytest

from voice_ai.audio.wake_word import STTWakeWord
from voice_ai.core.config import Config
from voice_ai.core.pipeline import Pipeline
from voice_ai.core.protocols import PipelineState


@pytest.fixture
def mock_pipeline(
    mock_audio_in: MagicMock,
    mock_audio_out: MagicMock,
    mock_vad: MagicMock,
    mock_stt: MagicMock,
    mock_llm: MagicMock,
    mock_tts: MagicMock,
    mock_memory: MagicMock,
) -> Pipeline:
    config = Config(_env_file=None, db_path=":memory:")
    return Pipeline(
        audio_in=mock_audio_in,
        audio_out=mock_audio_out,
        vad=mock_vad,
        stt=mock_stt,
        llm=mock_llm,
        tts=mock_tts,
        memory=mock_memory,
        config=config,
    )


@pytest.fixture
def mock_pipeline_with_wake_word(
    mock_audio_in: MagicMock,
    mock_audio_out: MagicMock,
    mock_vad: MagicMock,
    mock_stt: MagicMock,
    mock_llm: MagicMock,
    mock_tts: MagicMock,
    mock_memory: MagicMock,
) -> Pipeline:
    config = Config(_env_file=None, db_path=":memory:", activation_mode="wake_word")
    wake_word = STTWakeWord(config)
    return Pipeline(
        audio_in=mock_audio_in,
        audio_out=mock_audio_out,
        vad=mock_vad,
        stt=mock_stt,
        llm=mock_llm,
        tts=mock_tts,
        memory=mock_memory,
        config=config,
        wake_word=wake_word,
    )


class TestPipelineStates:
    def test_initial_state_is_idle(self, mock_pipeline: Pipeline) -> None:
        assert mock_pipeline.state == PipelineState.IDLE

    def test_interrupt_event_initially_clear(self, mock_pipeline: Pipeline) -> None:
        assert not mock_pipeline.interrupt_event.is_set()

    def test_shutdown_event_initially_clear(self, mock_pipeline: Pipeline) -> None:
        assert not mock_pipeline.shutdown_event.is_set()

    def test_wake_word_none_by_default(self, mock_pipeline: Pipeline) -> None:
        assert mock_pipeline.wake_word is None

    def test_wake_word_present_when_configured(self, mock_pipeline_with_wake_word: Pipeline) -> None:
        assert mock_pipeline_with_wake_word.wake_word is not None


class TestPipelineListenAndProcess:
    @pytest.mark.asyncio
    async def test_empty_audio_returns_none(self, mock_pipeline: Pipeline) -> None:
        mock_pipeline.audio_in.record_utterance = AsyncMock(
            return_value=np.array([], dtype=np.float32)
        )
        result = await mock_pipeline._listen_and_process()
        assert result is None
        assert mock_pipeline.state == PipelineState.IDLE

    @pytest.mark.asyncio
    async def test_successful_turn(self, mock_pipeline: Pipeline) -> None:
        audio = np.ones(16000, dtype=np.float32)
        mock_pipeline.audio_in.record_utterance = AsyncMock(return_value=audio)
        mock_pipeline.stt.transcribe = AsyncMock(return_value="Привет")

        async def fake_stream(msgs):
            for t in ["Здравствуйте", "!"]:
                yield t

        mock_pipeline.llm.chat_stream = fake_stream
        mock_pipeline.tts.synthesize = AsyncMock(
            return_value=np.zeros(48000, dtype=np.float32)
        )
        mock_pipeline.memory.save_message = AsyncMock()
        mock_pipeline.memory.get_history = AsyncMock(return_value=[])

        result = await mock_pipeline._listen_and_process()

        assert result is not None
        assert result.user_text == "Привет"
        assert result.assistant_text == "Здравствуйте!"
        assert not result.interrupted
        assert mock_pipeline.state == PipelineState.IDLE

    @pytest.mark.asyncio
    async def test_empty_transcription_returns_none(self, mock_pipeline: Pipeline) -> None:
        from voice_ai.core.exceptions import EmptyTranscriptionError

        audio = np.ones(16000, dtype=np.float32)
        mock_pipeline.audio_in.record_utterance = AsyncMock(return_value=audio)
        mock_pipeline.stt.transcribe = AsyncMock(side_effect=EmptyTranscriptionError)

        result = await mock_pipeline._listen_and_process()
        assert result is None

    @pytest.mark.asyncio
    async def test_tts_returns_none_still_completes(self, mock_pipeline: Pipeline) -> None:
        audio = np.ones(16000, dtype=np.float32)
        mock_pipeline.audio_in.record_utterance = AsyncMock(return_value=audio)
        mock_pipeline.stt.transcribe = AsyncMock(return_value="Тест")
        mock_pipeline.tts.synthesize = AsyncMock(return_value=None)
        mock_pipeline.memory.save_message = AsyncMock()
        mock_pipeline.memory.get_history = AsyncMock(return_value=[])

        async def fake_stream(msgs):
            yield "Ответ"

        mock_pipeline.llm.chat_stream = fake_stream

        result = await mock_pipeline._listen_and_process()
        assert result is not None
        assert result.audio_duration_s == 0.0


class TestPipelineProcessAudio:
    @pytest.mark.asyncio
    async def test_process_audio_successful(self, mock_pipeline: Pipeline) -> None:
        audio = np.ones(16000, dtype=np.float32)
        mock_pipeline.stt.transcribe = AsyncMock(return_value="Тест")
        mock_pipeline.tts.synthesize = AsyncMock(
            return_value=np.zeros(48000, dtype=np.float32)
        )
        mock_pipeline.memory.save_message = AsyncMock()
        mock_pipeline.memory.get_history = AsyncMock(return_value=[])

        async def fake_stream(msgs):
            yield "Ответ"

        mock_pipeline.llm.chat_stream = fake_stream

        result = await mock_pipeline._process_audio(audio)
        assert result is not None
        assert result.user_text == "Тест"

    @pytest.mark.asyncio
    async def test_process_audio_interrupted(self, mock_pipeline: Pipeline) -> None:
        audio = np.ones(16000, dtype=np.float32)
        mock_pipeline.stt.transcribe = AsyncMock(return_value="Тест")
        mock_pipeline.tts.synthesize = AsyncMock(
            return_value=np.zeros(48000, dtype=np.float32)
        )
        mock_pipeline.memory.save_message = AsyncMock()
        mock_pipeline.memory.get_history = AsyncMock(return_value=[])

        mock_pipeline.interrupt_event.set()

        async def fake_stream(msgs):
            yield "От"

        mock_pipeline.llm.chat_stream = fake_stream

        result = await mock_pipeline._process_audio(audio)
        assert result is not None
        assert result.interrupted


class TestPipelineActivationModes:
    def test_default_mode_is_wake_word(self) -> None:
        config = Config(_env_file=None, db_path=":memory:")
        assert config.activation_mode == "wake_word"

    def test_button_mode_config(self) -> None:
        config = Config(_env_file=None, db_path=":memory:", activation_mode="button")
        assert config.activation_mode == "button"

    def test_continuous_mode_config(self) -> None:
        config = Config(_env_file=None, db_path=":memory:", activation_mode="continuous")
        assert config.activation_mode == "continuous"

    def test_pipeline_without_wake_word_in_button_mode(self, mock_pipeline: Pipeline) -> None:
        assert mock_pipeline.config.activation_mode == "wake_word"
        assert mock_pipeline.wake_word is None


class TestPipelineShutdown:
    @pytest.mark.asyncio
    async def test_shutdown_sets_events(self, mock_pipeline: Pipeline) -> None:
        await mock_pipeline.shutdown()
        assert mock_pipeline.shutdown_event.is_set()
        assert mock_pipeline.interrupt_event.is_set()