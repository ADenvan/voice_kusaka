import numpy as np

from voice_ai.audio.input import RingBuffer
from voice_ai.audio.output import clamp_audio, resample_audio


def test_resample_same_rate() -> None:
    audio = np.ones(16000, dtype=np.float32)
    result = resample_audio(audio, 16000, 16000)
    assert result is audio


def test_resample_upsample() -> None:
    audio = np.ones(16000, dtype=np.float32)
    result = resample_audio(audio, 16000, 48000)
    assert abs(len(result) - 48000) < 100
    assert result.dtype == np.float32


def test_resample_downsample() -> None:
    audio = np.ones(48000, dtype=np.float32)
    result = resample_audio(audio, 48000, 16000)
    assert abs(len(result) - 16000) < 100
    assert result.dtype == np.float32


def test_clamp_audio_within_range() -> None:
    audio = np.array([0.5, -0.3, 0.0], dtype=np.float32)
    result = clamp_audio(audio)
    np.testing.assert_array_equal(result, audio)


def test_clamp_audio_exceeds_range() -> None:
    audio = np.array([2.0, -1.5, 0.0], dtype=np.float32)
    result = clamp_audio(audio)
    assert result.max() <= 1.0
    assert result.min() >= -1.0
    assert result.dtype == np.float32


def test_energy_vad_silence() -> None:
    from voice_ai.audio.vad import EnergyVAD
    from voice_ai.core.config import Config

    config = Config(_env_file=None, db_path=":memory:")
    vad = EnergyVAD(config)
    silence = np.zeros(8000, dtype=np.float32)
    assert not vad.is_speech(silence)


def test_energy_vad_speech() -> None:
    from voice_ai.audio.vad import EnergyVAD
    from voice_ai.core.config import Config

    config = Config(_env_file=None, db_path=":memory:")
    vad = EnergyVAD(config)
    rng = np.random.default_rng(42)
    speech = (rng.standard_normal(8000) * 0.3).astype(np.float32)
    assert vad.is_speech(speech)


def test_energy_vad_prob_range() -> None:
    from voice_ai.audio.vad import EnergyVAD
    from voice_ai.core.config import Config

    config = Config(_env_file=None, db_path=":memory:")
    vad = EnergyVAD(config)
    silence = np.zeros(8000, dtype=np.float32)
    prob = vad.get_speech_prob(silence)
    assert 0.0 <= prob <= 1.0


class TestRingBuffer:
    def test_empty_buffer(self) -> None:
        buf = RingBuffer(capacity_chunks=5)
        result = buf.get_all()
        assert len(result) == 0
        assert result.dtype == np.float32

    def test_append_and_get_all(self) -> None:
        buf = RingBuffer(capacity_chunks=5)
        chunk1 = np.ones(100, dtype=np.float32)
        chunk2 = np.ones(100, dtype=np.float32) * 2
        buf.append(chunk1)
        buf.append(chunk2)
        result = buf.get_all()
        assert len(result) == 200
        np.testing.assert_array_equal(result[:100], chunk1)
        np.testing.assert_array_equal(result[100:], chunk2)

    def test_capacity_overflow(self) -> None:
        buf = RingBuffer(capacity_chunks=3)
        for i in range(5):
            buf.append(np.array([float(i)], dtype=np.float32))
        assert len(buf) == 3
        result = buf.get_all()
        assert len(result) == 3
        assert result[0] == 2.0
        assert result[1] == 3.0
        assert result[2] == 4.0

    def test_clear(self) -> None:
        buf = RingBuffer(capacity_chunks=5)
        buf.append(np.ones(100, dtype=np.float32))
        buf.clear()
        result = buf.get_all()
        assert len(result) == 0

    def test_duration_s(self) -> None:
        buf = RingBuffer(capacity_chunks=5)
        chunk = np.ones(16000, dtype=np.float32)
        buf.append(chunk)
        assert abs(buf.duration_s - 1.0) < 0.01

    def test_len(self) -> None:
        buf = RingBuffer(capacity_chunks=5)
        assert len(buf) == 0
        buf.append(np.ones(100, dtype=np.float32))
        assert len(buf) == 1
        buf.append(np.ones(100, dtype=np.float32))
        assert len(buf) == 2
