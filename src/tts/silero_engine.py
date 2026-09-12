import asyncio
import logging
import os
import re
import tempfile
import zipfile

import numpy as np

from src.core.config import Config
from src.tts.language_detector import segment_by_language

logger = logging.getLogger("voice_ai.tts")

_SILERO_REPO_URL = "https://github.com/snakers4/silero-models/archive/master.zip"
_SILERO_REPO_DIR_NAME = "snakers4_silero-models_master"

_SUPPORTED_CHARS_PATTERN = re.compile(
    r"[^\u0400-\u04FFa-zA-Z0-9\s\.,!?;:\-\"'()]"
)


def _clean_text_for_tts(text: str) -> str:
    cleaned = _SUPPORTED_CHARS_PATTERN.sub("", text)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def _ensure_repo(repo_dir: str) -> None:
    if os.path.isdir(repo_dir):
        return
    hub_dir = os.path.dirname(repo_dir)
    os.makedirs(hub_dir, exist_ok=True)
    logger.info("Silero repo not found in torch hub cache, downloading...")
    import torch

    fd, tmp_zip = tempfile.mkstemp(suffix=".zip", dir=hub_dir)
    os.close(fd)
    try:
        torch.hub.download_url_to_file(_SILERO_REPO_URL, tmp_zip)
        with zipfile.ZipFile(tmp_zip) as z:
            top = z.namelist()[0].rstrip("/\\").split("/")[0]
            z.extractall(hub_dir)
    finally:
        if os.path.exists(tmp_zip):
            os.remove(tmp_zip)
    os.rename(os.path.join(hub_dir, top), repo_dir)
    logger.info("Silero repo downloaded to %s", repo_dir)


class _SileroModel:
    def __init__(
        self,
        language: str,
        speaker: str,
        voice: str,
        sample_rate: int,
    ) -> None:
        self._language = language
        self._speaker = speaker
        self._voice = voice
        self._sample_rate = sample_rate
        self._model = None
        self._symbols = None
        self._apply_tts_fn = None

    @property
    def sample_rate(self) -> int:
        return self._sample_rate

    def load(self) -> None:
        self._load_model()

    def _load_model(self) -> None:
        if self._model is not None:
            return

        import sys
        import torch

        logger.info("Loading Silero TTS model (language=%s)...", self._language)

        hub_dir = torch.hub.get_dir()
        repo_dir = os.path.join(hub_dir, _SILERO_REPO_DIR_NAME)
        _ensure_repo(repo_dir)

        silero_src_dir = os.path.join(repo_dir, "src")
        silero_init = os.path.join(silero_src_dir, "__init__.py")
        created_init = False
        if not os.path.exists(silero_init):
            with open(silero_init, "w"):
                pass
            created_init = True

        saved_src = sys.modules.pop("src", None)
        saved_src_subs = {
            k: v for k, v in list(sys.modules.items()) if k.startswith("src.")
        }
        for k in saved_src_subs:
            del sys.modules[k]

        if repo_dir not in sys.path:
            sys.path.insert(0, repo_dir)

        try:
            from src.silero import silero_tts
            result = silero_tts(
                language=self._language,
                speaker=self._speaker,
            )
        finally:
            if repo_dir in sys.path:
                sys.path.remove(repo_dir)
            for k in list(sys.modules):
                if k == "src" or k.startswith("src."):
                    del sys.modules[k]
            if saved_src is not None:
                sys.modules["src"] = saved_src
            sys.modules.update(saved_src_subs)
            if created_init:
                try:
                    os.remove(silero_init)
                except OSError:
                    pass

        if isinstance(result, (tuple, list)) and len(result) >= 1:
            self._model = result[0]
            if hasattr(self._model, "symbols"):
                self._symbols = self._model.symbols
            self._apply_tts_fn = None
        else:
            self._model = result

        logger.info("Silero TTS model loaded (language=%s)", self._language)

    def synthesize_sync(self, text: str) -> np.ndarray | None:
        cleaned_text = _clean_text_for_tts(text)
        if not cleaned_text.strip():
            logger.warning("TTS: text became empty after cleaning")
            return None

        self._load_model()
        logger.info(
            "TTS [%s]: synthesizing (%d chars): %.80s%s",
            self._language, len(cleaned_text), cleaned_text,
            "..." if len(cleaned_text) > 80 else "",
        )

        if self._apply_tts_fn is not None:
            audios = self._apply_tts_fn(
                [cleaned_text], self._model, self._sample_rate,
                self._symbols, "cpu",
            )
            result = np.array(audios[0], dtype=np.float32)
        else:
            audio_tensor = self._model.apply_tts(
                text=cleaned_text,
                speaker=self._voice,
                sample_rate=self._sample_rate,
            )
            result = audio_tensor.numpy().astype(np.float32)

        logger.info(
            "TTS [%s]: result shape=%s len=%d duration=%.2fs",
            self._language, result.shape, len(result),
            len(result) / self._sample_rate,
        )
        if result.max() == 0 and result.min() == 0:
            logger.warning("TTS [%s]: result is all zeros (silence)!", self._language)
        return result


class SileroTTSEngine:
    def __init__(self, config: Config) -> None:
        self._model = _SileroModel(
            language=config.silero_language,
            speaker=config.silero_speaker,
            voice=config.silero_voice,
            sample_rate=config.silero_sample_rate,
        )

    def load(self) -> None:
        self._model.load()

    def _ensure_repo(self, repo_dir: str) -> None:
        _ensure_repo(repo_dir)

    async def synthesize(self, text: str) -> np.ndarray | None:
        if not text.strip():
            logger.debug("TTS: skipping empty text")
            return None
        try:
            result = await asyncio.to_thread(self._model.synthesize_sync, text)
        except ValueError as e:
            logger.error("TTS synthesis failed: %s", e)
            return None
        except Exception as e:
            logger.error("TTS synthesis failed: %s", e, exc_info=True)
            return None

        if result is None and text.strip():
            logger.warning("TTS returned None for non-empty text")
        return result


class BilingualSileroTTSEngine:
    def __init__(self, config: Config) -> None:
        self._ru_model = _SileroModel(
            language=config.silero_language,
            speaker=config.silero_speaker,
            voice=config.silero_voice,
            sample_rate=config.silero_sample_rate,
        )
        self._en_model = _SileroModel(
            language=config.silero_en_language,
            speaker=config.silero_en_speaker,
            voice=config.silero_en_voice,
            sample_rate=config.silero_en_sample_rate,
        )
        self._sample_rate = config.silero_sample_rate

    def load(self) -> None:
        logger.info("Pre-loading bilingual TTS models (RU + EN)...")
        self._ru_model.load()
        self._en_model.load()
        logger.info("Bilingual TTS models ready")

    @property
    def sample_rate(self) -> int:
        return self._sample_rate

    def _get_model(self, language: str) -> _SileroModel:
        if language == "en":
            return self._en_model
        return self._ru_model

    def _synthesize_segment(self, language: str, text: str) -> np.ndarray | None:
        model = self._get_model(language)
        try:
            return model.synthesize_sync(text)
        except ValueError as e:
            logger.error("TTS [%s] synthesis failed: %s", language, e)
            return None
        except Exception as e:
            logger.error("TTS [%s] synthesis failed: %s", language, e, exc_info=True)
            return None

    async def synthesize(self, text: str) -> np.ndarray | None:
        if not text.strip():
            logger.debug("TTS: skipping empty text")
            return None

        segments = segment_by_language(text)
        if not segments:
            logger.warning("TTS: no segments after language detection")
            return None

        logger.info("TTS: %d language segments detected", len(segments))

        try:
            audio_chunks = await asyncio.to_thread(
                self._synthesize_all_segments, segments,
            )
        except Exception as e:
            logger.error("TTS bilingual synthesis error: %s", e, exc_info=True)
            return None

        valid_chunks = [chunk for chunk in audio_chunks if chunk is not None]
        if not valid_chunks:
            logger.warning("TTS: all segments returned None")
            return None

        result = np.concatenate(valid_chunks)
        logger.info(
            "TTS: concatenated %d chunks → shape=%s duration=%.2fs",
            len(valid_chunks), result.shape, len(result) / self._sample_rate,
        )
        return result

    def _synthesize_all_segments(
        self, segments: list[tuple[str, str]],
    ) -> list[np.ndarray | None]:
        return [
            self._synthesize_segment(lang, text)
            for lang, text in segments
        ]
