import asyncio
import time
from difflib import SequenceMatcher

import numpy as np
from loguru import logger

from src.core.config import Config
from src.core.exceptions import WakeWordError


class STTWakeWord:
    WAKE_PHRASES: list[str] = ["войс ай", "voice ai", "войсай", "войс айай"]

    def __init__(self, config: Config) -> None:
        self._model_name = config.wake_word_model
        self._device = config.wake_word_device
        self._compute_type = config.wake_word_compute_type
        self._phrases = config.wake_word_phrases or self.WAKE_PHRASES
        self._threshold = config.wake_word_match_threshold
        self._cooldown_s = config.wake_word_cooldown_s
        self._last_detection_time: float = 0.0
        self._model = None

    def load(self) -> None:
        self._load_model()

    def _load_model(self) -> None:
        if self._model is None:
            from faster_whisper import WhisperModel

            logger.info(
                "Loading wake word model: {} (device={}, compute_type={})",
                self._model_name, self._device, self._compute_type,
            )
            try:
                self._model = WhisperModel(
                    self._model_name,
                    device=self._device,
                    compute_type=self._compute_type,
                )
                logger.info("Wake word model loaded")
            except Exception as e:
                raise WakeWordError(f"Failed to load wake word model: {e}") from e

    def _transcribe_sync(self, audio: np.ndarray) -> str:
        self._load_model()
        if len(audio) == 0:
            return ""
        segments, _ = self._model.transcribe(audio, language="ru")
        text = " ".join(s.text for s in segments).strip().lower()
        return text

    async def detect(self, audio: np.ndarray) -> bool:
        now = time.monotonic()
        if now - self._last_detection_time < self._cooldown_s:
            remaining = self._cooldown_s - (now - self._last_detection_time)
            logger.debug("Wake word: cooldown active ({:.1f}s left)", remaining)
            return False

        try:
            text = await asyncio.to_thread(self._transcribe_sync, audio)
        except Exception as e:
            logger.error("Wake word transcription error: {}", e)
            return False

        if not text:
            return False

        logger.debug("Wake word heard: {!r}", text)

        matched = self._fuzzy_match(text, self._phrases, self._threshold)
        if matched:
            self._last_detection_time = time.monotonic()
            logger.info("Wake word detected! Heard: {!r}, matched phrase: {!r}", text, matched)
        return matched is not None

    @staticmethod
    def _fuzzy_match(text: str, phrases: list[str], threshold: float) -> str | None:
        text_lower = text.lower().strip()
        for phrase in phrases:
            phrase_lower = phrase.lower().strip()
            if phrase_lower in text_lower:
                return phrase
            ratio = SequenceMatcher(None, text_lower, phrase_lower).ratio()
            if ratio >= threshold:
                return phrase
            words = text_lower.split()
            for i in range(len(words)):
                for j in range(i + 1, min(i + 4, len(words) + 1)):
                    substr = " ".join(words[i:j])
                    if phrase_lower in substr:
                        return phrase
                    r = SequenceMatcher(None, substr, phrase_lower).ratio()
                    if r >= threshold:
                        return phrase
        return None

    def reset_cooldown(self) -> None:
        self._last_detection_time = 0.0