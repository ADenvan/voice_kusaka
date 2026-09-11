import time
from unittest.mock import AsyncMock, MagicMock, patch

import numpy as np
import pytest

from voice_ai.audio.wake_word import STTWakeWord
from voice_ai.core.config import Config
from voice_ai.core.exceptions import WakeWordError


@pytest.fixture
def wake_config(tmp_path) -> Config:
    return Config(
        _env_file=None,
        db_path=str(tmp_path / "test.db"),
        wake_word_model="tiny",
        wake_word_device="cpu",
        wake_word_compute_type="int8",
        wake_word_phrases=["войс ай", "voice ai", "войсай"],
        wake_word_match_threshold=0.7,
        wake_word_cooldown_s=3.0,
    )


class TestFuzzyMatch:
    def test_exact_phrase_match(self) -> None:
        result = STTWakeWord._fuzzy_match(
            "войс ай", ["войс ай", "voice ai"], 0.7
        )
        assert result == "войс ай"

    def test_exact_substring_match(self) -> None:
        result = STTWakeWord._fuzzy_match(
            "привет войс ай как дела", ["войс ай", "voice ai"], 0.7
        )
        assert result == "войс ай"

    def test_fuzzy_match_near_phrase(self) -> None:
        result = STTWakeWord._fuzzy_match(
            "войсай", ["войс ай", "voice ai"], 0.7
        )
        assert result is not None

    def test_no_match_unrelated_text(self) -> None:
        result = STTWakeWord._fuzzy_match(
            "какая сегодня погода", ["войс ай", "voice ai"], 0.7
        )
        assert result is None

    def test_no_match_short_unrelated(self) -> None:
        result = STTWakeWord._fuzzy_match(
            "да", ["войс ай", "voice ai"], 0.7
        )
        assert result is None

    def test_fuzzy_match_partial_word(self) -> None:
        result = STTWakeWord._fuzzy_match(
            "войс", ["войс ай", "voice ai"], 0.7
        )
        assert result is not None

    def test_english_phrase_match(self) -> None:
        result = STTWakeWord._fuzzy_match(
            "voice ai", ["войс ай", "voice ai"], 0.7
        )
        assert result == "voice ai"

    def test_empty_text_no_match(self) -> None:
        result = STTWakeWord._fuzzy_match(
            "", ["войс ай", "voice ai"], 0.7
        )
        assert result is None

    def test_case_insensitive_match(self) -> None:
        result = STTWakeWord._fuzzy_match(
            "ВОЙС АЙ", ["войс ай"], 0.7
        )
        assert result == "войс ай"

    def test_sliding_window_match(self) -> None:
        result = STTWakeWord._fuzzy_match(
            "я сказал войс ай и ушёл", ["войс ай"], 0.7
        )
        assert result == "войс ай"


class TestSTTWakeWord:
    @pytest.mark.asyncio
    async def test_detect_returns_false_on_empty_audio(self, wake_config: Config) -> None:
        wake = STTWakeWord(wake_config)
        wake._model = MagicMock()
        result = await wake.detect(np.array([], dtype=np.float32))
        assert result is False

    @pytest.mark.asyncio
    async def test_detect_returns_false_when_cooldown_active(self, wake_config: Config) -> None:
        wake = STTWakeWord(wake_config)
        wake._model = MagicMock()
        wake._last_detection_time = time.monotonic()
        audio = np.random.randn(32000).astype(np.float32)
        result = await wake.detect(audio)
        assert result is False

    def test_reset_cooldown(self, wake_config: Config) -> None:
        wake = STTWakeWord(wake_config)
        wake._last_detection_time = time.monotonic()
        wake.reset_cooldown()
        assert wake._last_detection_time == 0.0

    @pytest.mark.asyncio
    async def test_detect_with_mock_transcription_match(self, wake_config: Config) -> None:
        wake = STTWakeWord(wake_config)
        wake._model = MagicMock()
        wake._transcribe_sync = MagicMock(return_value="войс ай")

        audio = np.random.randn(32000).astype(np.float32)
        result = await wake.detect(audio)
        assert result is True

    @pytest.mark.asyncio
    async def test_detect_with_mock_transcription_no_match(self, wake_config: Config) -> None:
        wake = STTWakeWord(wake_config)
        wake._model = MagicMock()
        wake._transcribe_sync = MagicMock(return_value="привет как дела")

        audio = np.random.randn(32000).astype(np.float32)
        result = await wake.detect(audio)
        assert result is False

    @pytest.mark.asyncio
    async def test_detect_handles_transcription_error(self, wake_config: Config) -> None:
        wake = STTWakeWord(wake_config)
        wake._model = MagicMock()
        wake._transcribe_sync = MagicMock(side_effect=Exception("STT error"))

        audio = np.random.randn(32000).astype(np.float32)
        result = await wake.detect(audio)
        assert result is False

    def test_load_raises_on_failure(self, wake_config: Config) -> None:
        wake = STTWakeWord(wake_config)
        with patch("voice_ai.audio.wake_word.WakeWordError", WakeWordError):
            with patch("faster_whisper.WhisperModel", side_effect=RuntimeError("no model")):
                with pytest.raises(WakeWordError):
                    wake._load_model()