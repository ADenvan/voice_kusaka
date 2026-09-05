import os

import numpy as np
import pytest

from src.core.config import Config
from src.tts.silero_engine import SileroTTSEngine, _clean_text_for_tts


class _FakeTensor:
    def __init__(self, data: np.ndarray) -> None:
        self._data = data

    def numpy(self) -> np.ndarray:
        return self._data


class _FakeSileroModel:
    def apply_tts(self, text: str, speaker: str, sample_rate: int):
        duration = max(len(text) * 100, 4800)
        return _FakeTensor(np.zeros(duration, dtype=np.float32))


@pytest.fixture
def tts_engine() -> SileroTTSEngine:
    config = Config(_env_file=None, db_path=":memory:")
    return SileroTTSEngine(config)


@pytest.mark.asyncio
async def test_synthesize_empty_text(tts_engine: SileroTTSEngine) -> None:
    result = await tts_engine.synthesize("")
    assert result is None


@pytest.mark.asyncio
async def test_synthesize_whitespace_only(
    tts_engine: SileroTTSEngine,
) -> None:
    result = await tts_engine.synthesize("   ")
    assert result is None


@pytest.mark.asyncio
async def test_synthesize_with_mock_model(
    tts_engine: SileroTTSEngine,
) -> None:
    tts_engine._model = _FakeSileroModel()
    result = await tts_engine.synthesize("Привет")
    assert result is not None
    assert isinstance(result, np.ndarray)
    assert result.dtype == np.float32


def test_ensure_repo_downloads_when_missing(tts_engine: SileroTTSEngine) -> None:
    from unittest.mock import MagicMock, patch

    repo_dir = "/fake/hub/snakers4_silero-models_master"
    hub_dir = "/fake/hub"
    tmp_zip = "/fake/hub/tmp123.zip"

    mock_zip_instance = MagicMock()
    mock_zip_instance.namelist.return_value = [
        "silero-models-master/src/",
        "silero-models-master/hubconf.py",
    ]

    with (
        patch("os.path.isdir", return_value=False),
        patch("os.makedirs") as mock_makedirs,
        patch("tempfile.mkstemp", return_value=(42, tmp_zip)),
        patch("os.close"),
        patch("torch.hub.download_url_to_file") as mock_download,
        patch("zipfile.ZipFile") as mock_zip_cls,
        patch("os.remove"),
        patch("os.rename") as mock_rename,
    ):
        mock_zip_cls.return_value.__enter__ = MagicMock(return_value=mock_zip_instance)
        mock_zip_cls.return_value.__exit__ = MagicMock(return_value=False)

        tts_engine._ensure_repo(repo_dir)

        mock_makedirs.assert_called_once_with(hub_dir, exist_ok=True)
        mock_download.assert_called_once()
        mock_zip_instance.extractall.assert_called_once_with(hub_dir)
        mock_rename.assert_called_once_with(
            os.path.join(hub_dir, "silero-models-master"), repo_dir
        )


def test_ensure_repo_skips_when_present(tts_engine: SileroTTSEngine) -> None:
    from unittest.mock import patch

    repo_dir = "/fake/hub/snakers4_silero-models_master"

    with (
        patch("os.path.isdir", return_value=True),
        patch("torch.hub.download_url_to_file") as mock_download,
    ):
        tts_engine._ensure_repo(repo_dir)
        mock_download.assert_not_called()


def test_clean_text_removes_chinese_characters() -> None:
    text = "Привет我可以帮助你？你需要我做些什么？"
    cleaned = _clean_text_for_tts(text)
    assert cleaned == "Привет"


def test_clean_text_removes_emoji() -> None:
    text = "Привет! 👋 Как дела? 🎉"
    cleaned = _clean_text_for_tts(text)
    assert cleaned == "Привет! Как дела?"


def test_clean_text_preserves_russian_and_basic_chars() -> None:
    text = "Привет, мир! Это тест-сообщение."
    cleaned = _clean_text_for_tts(text)
    assert cleaned == text


def test_clean_text_normalizes_whitespace() -> None:
    text = "Привет   мир!  Как   дела?"
    cleaned = _clean_text_for_tts(text)
    assert cleaned == "Привет мир! Как дела?"


def test_clean_text_removes_mixed_unsupported() -> None:
    text = "Текст с 中文 и العربية символами"
    cleaned = _clean_text_for_tts(text)
    assert cleaned == "Текст с и символами"
