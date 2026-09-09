import os

import numpy as np
import pytest

from src.core.config import Config
from src.tts.silero_engine import (
    BilingualSileroTTSEngine,
    SileroTTSEngine,
    _clean_text_for_tts,
    _ensure_repo,
)


class _FakeTensor:
    def __init__(self, data: np.ndarray) -> None:
        self._data = data

    def numpy(self) -> np.ndarray:
        return self._data


class _FakeSileroModelInner:
    def apply_tts(self, text: str, speaker: str, sample_rate: int):
        duration = max(len(text) * 100, 4800)
        return _FakeTensor(np.zeros(duration, dtype=np.float32))


@pytest.fixture
def tts_engine() -> SileroTTSEngine:
    config = Config(_env_file=None, db_path=":memory:")
    return SileroTTSEngine(config)


@pytest.fixture
def bilingual_engine() -> BilingualSileroTTSEngine:
    config = Config(_env_file=None, db_path=":memory:")
    return BilingualSileroTTSEngine(config)


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
    tts_engine._model._model = _FakeSileroModelInner()
    result = await tts_engine.synthesize("Привет")
    assert result is not None
    assert isinstance(result, np.ndarray)
    assert result.dtype == np.float32


def test_ensure_repo_downloads_when_missing() -> None:
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
        patch("zipfile.ZipFile") as mock_zip_cls,
        patch("os.remove"),
        patch("os.rename") as mock_rename,
    ):
        mock_zip_cls.return_value.__enter__ = MagicMock(return_value=mock_zip_instance)
        mock_zip_cls.return_value.__exit__ = MagicMock(return_value=False)

        mock_torch = MagicMock()
        with patch.dict("sys.modules", {"torch": mock_torch}):
            _ensure_repo(repo_dir)

        mock_makedirs.assert_called_once_with(hub_dir, exist_ok=True)
        mock_torch.hub.download_url_to_file.assert_called_once()
        mock_zip_instance.extractall.assert_called_once_with(hub_dir)
        mock_rename.assert_called_once_with(
            os.path.join(hub_dir, "silero-models-master"), repo_dir
        )


def test_ensure_repo_skips_when_present() -> None:
    from unittest.mock import MagicMock, patch

    repo_dir = "/fake/hub/snakers4_silero-models_master"

    mock_torch = MagicMock()
    with patch("os.path.isdir", return_value=True):
        with patch.dict("sys.modules", {"torch": mock_torch}):
            _ensure_repo(repo_dir)
    mock_torch.hub.download_url_to_file.assert_not_called()


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


@pytest.mark.asyncio
async def test_bilingual_synthesize_empty_text(
    bilingual_engine: BilingualSileroTTSEngine,
) -> None:
    result = await bilingual_engine.synthesize("")
    assert result is None


@pytest.mark.asyncio
async def test_bilingual_synthesize_russian_only(
    bilingual_engine: BilingualSileroTTSEngine,
) -> None:
    bilingual_engine._ru_model._model = _FakeSileroModelInner()
    result = await bilingual_engine.synthesize("Привет мир")
    assert result is not None
    assert isinstance(result, np.ndarray)
    assert result.dtype == np.float32


@pytest.mark.asyncio
async def test_bilingual_synthesize_english_only(
    bilingual_engine: BilingualSileroTTSEngine,
) -> None:
    bilingual_engine._en_model._model = _FakeSileroModelInner()
    result = await bilingual_engine.synthesize("Hello world")
    assert result is not None
    assert isinstance(result, np.ndarray)
    assert result.dtype == np.float32


@pytest.mark.asyncio
async def test_bilingual_synthesize_mixed(
    bilingual_engine: BilingualSileroTTSEngine,
) -> None:
    bilingual_engine._ru_model._model = _FakeSileroModelInner()
    bilingual_engine._en_model._model = _FakeSileroModelInner()
    result = await bilingual_engine.synthesize("Привет Hello Мир")
    assert result is not None
    assert isinstance(result, np.ndarray)
    assert result.dtype == np.float32
