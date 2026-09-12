import asyncio
import logging

import numpy as np

from src.core.config import Config
from src.core.exceptions import EmptyTranscriptionError, STTError

logger = logging.getLogger("voice_ai.stt")


class FasterWhisperEngine:
    def __init__(self, config: Config) -> None:
        self._model_name = config.whisper_model
        self._device = config.whisper_device
        self._compute_type = config.whisper_compute_type
        self._language = config.tts_language
        self._model = None

    def load(self) -> None:
        self._load_model()

    def _load_model(self) -> None:
        if self._model is None:
            from faster_whisper import WhisperModel

            logger.info(
                "Loading Whisper model: %s (device=%s, compute_type=%s)",
                self._model_name,
                self._device,
                self._compute_type,
            )
            self._model = WhisperModel(
                self._model_name,
                device=self._device,
                compute_type=self._compute_type,
            )
            logger.info("Whisper model loaded")

    def _transcribe_sync(self, audio: np.ndarray) -> str:
        self._load_model()
        if len(audio) == 0:
            return ""
        segments, _ = self._model.transcribe(audio, language=self._language)
        text = " ".join(s.text for s in segments).strip()
        return text

    async def transcribe(self, audio: np.ndarray) -> str:
        try:
            text = await asyncio.to_thread(self._transcribe_sync, audio)
        except Exception as e:
            raise STTError(f"Transcription failed: {e}") from e

        if not text:
            raise EmptyTranscriptionError("STT returned empty result")

        logger.info("Transcribed: %s (%d chars)", text[:50], len(text))
        return text
