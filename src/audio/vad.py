import logging

import numpy as np

from src.core.config import Config

logger = logging.getLogger("voice_ai.audio.vad")


class SileroVAD:
    def __init__(self, config: Config) -> None:
        self._threshold = config.vad_threshold
        self._sample_rate = config.sample_rate
        self._min_speech_duration_ms = config.vad_min_speech_duration_ms
        self._min_silence_duration_ms = config.vad_min_silence_duration_ms
        self._speech_pad_ms = config.vad_speech_pad_ms
        self._model = None

    def load(self) -> None:
        self._load_model()

    def _load_model(self) -> None:
        if self._model is None:
            import torch

            logger.info("Loading Silero VAD model...")
            self._model, _ = torch.hub.load(
                repo_or_dir="snakers4/silero-vad",
                model="silero_vad",
                trust_repo=True,
            )
            logger.info("Silero VAD model loaded")

    def _window_size(self) -> int:
        return 512 if self._sample_rate == 16000 else 256

    def _compute_probs(self, chunk: np.ndarray) -> list[float]:
        import torch

        self._load_model()
        window = self._window_size()
        probs: list[float] = []
        offset = 0
        while offset < len(chunk):
            end = offset + window
            sub = chunk[offset:end]
            if len(sub) < window:
                sub = np.pad(sub, (0, window - len(sub)), mode="constant")
            tensor = torch.from_numpy(sub).float()
            probs.append(self._model(tensor, self._sample_rate).item())
            offset = end
        return probs

    def is_speech(self, chunk: np.ndarray) -> bool:
        probs = self._compute_probs(chunk)
        result = max(probs) >= self._threshold
        logger.debug(
            "VAD: max_prob=%.3f threshold=%.3f speech=%s samples=%d",
            max(probs), self._threshold, result, len(chunk),
        )
        return result

    def get_speech_prob(self, chunk: np.ndarray) -> float:
        probs = self._compute_probs(chunk)
        return max(probs)


class EnergyVAD:
    def __init__(self, config: Config) -> None:
        self._threshold = 0.01

    def is_speech(self, chunk: np.ndarray) -> bool:
        rms = float(np.sqrt(np.mean(chunk**2)))
        return rms >= self._threshold

    def get_speech_prob(self, chunk: np.ndarray) -> float:
        rms = float(np.sqrt(np.mean(chunk**2)))
        return min(rms / 0.05, 1.0)
