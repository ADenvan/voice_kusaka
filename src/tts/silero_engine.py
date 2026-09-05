import asyncio
import logging
import os
import re
import tempfile
import zipfile

import numpy as np

from src.core.config import Config

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


class SileroTTSEngine:
    def __init__(self, config: Config) -> None:
        self._language = config.silero_language
        self._speaker = config.silero_speaker
        self._voice = config.silero_voice
        self._sample_rate = config.silero_sample_rate
        self._model = None
        self._symbols = None
        self._apply_tts_fn = None

    def load(self) -> None:
        self._load_model()

    def _ensure_repo(self, repo_dir: str) -> None:
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

    def _load_model(self) -> None:
        if self._model is None:
            import sys

            import torch

            logger.info("Loading Silero TTS model (language=%s)...", self._language)

            hub_dir = torch.hub.get_dir()
            repo_dir = os.path.join(hub_dir, _SILERO_REPO_DIR_NAME)
            self._ensure_repo(repo_dir)

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
                if hasattr(self._model, 'symbols'):
                    self._symbols = self._model.symbols
                if len(result) >= 2 and isinstance(result[1], str):
                    pass
                self._apply_tts_fn = None
            else:
                self._model = result

            logger.info("Silero TTS model loaded")

    def _synthesize_sync(self, text: str) -> np.ndarray | None:
        if not text.strip():
            logger.debug("TTS: skipping empty text")
            return None
        
        cleaned_text = _clean_text_for_tts(text)
        if cleaned_text != text:
            logger.warning(
                "TTS: cleaned unsupported characters (original=%d, cleaned=%d)",
                len(text), len(cleaned_text)
            )
        
        if not cleaned_text.strip():
            logger.warning("TTS: text became empty after cleaning unsupported characters")
            return None
        
        try:
            self._load_model()
            logger.info("TTS: synthesizing text (%d chars): %.80s%s", len(cleaned_text), cleaned_text, "..." if len(cleaned_text) > 80 else "")
            if self._apply_tts_fn is not None:
                logger.info("TTS: using v5 apply_tts_fn API (voice=%s, sr=%d)", self._voice, self._sample_rate)
                audios = self._apply_tts_fn(
                    [cleaned_text], self._model, self._sample_rate, self._symbols, "cpu",
                )
                result = np.array(audios[0], dtype=np.float32)
                logger.info("TTS: v5 synthesis result shape=%s dtype=%s min=%.6f max=%.6f rms=%.6f len=%d",
                            result.shape, result.dtype, float(result.min()), float(result.max()),
                            float(np.sqrt(np.mean(result**2))), len(result))
                if result.max() == 0 and result.min() == 0:
                    logger.warning("TTS: v5 result is all zeros (silence)!")
                return result
            logger.info("TTS: using legacy apply_tts API (speaker=%s, sr=%d)", self._voice, self._sample_rate)
            audio_tensor = self._model.apply_tts(
                text=cleaned_text,
                speaker=self._voice,
                sample_rate=self._sample_rate,
            )
            result = audio_tensor.numpy().astype(np.float32)
            logger.info("TTS: legacy synthesis result shape=%s dtype=%s min=%.6f max=%.6f rms=%.6f len=%d",
                        result.shape, result.dtype, float(result.min()), float(result.max()),
                        float(np.sqrt(np.mean(result**2))), len(result))
            if result.max() == 0 and result.min() == 0:
                logger.warning("TTS: legacy result is all zeros (silence)!")
            return result
        except ValueError as e:
            logger.error("TTS synthesis failed: text contains unsupported characters (likely non-Russian text with Russian model). Error: %s", e)
            return None
        except Exception as e:
            logger.error("TTS synthesis failed: %s", e, exc_info=True)
            return None

    async def synthesize(self, text: str) -> np.ndarray | None:
        try:
            result = await asyncio.to_thread(self._synthesize_sync, text)
        except Exception as e:
            logger.error("TTS synthesis error: %s", e)
            return None

        if result is None and text.strip():
            logger.warning("TTS returned None for non-empty text, falling back to text-only mode")
        return result
