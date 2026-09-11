import asyncio

import numpy as np
import pytest

from voice_ai.core.config import Config
from voice_ai.core.pipeline import Pipeline
from voice_ai.memory.database import SQLiteStore


@pytest.fixture
def integration_config(tmp_path: object) -> Config:
    return Config(
        _env_file=None,
        db_path=str(tmp_path / "integration.db"),
        whisper_model="tiny",
        whisper_device="cpu",
        whisper_compute_type="int8",
        activation_mode="button",
    )


class _StubAudioIn:
    def __init__(self) -> None:
        self._call_count = 0

    async def start(self) -> None:
        pass

    async def stop(self) -> None:
        pass

    async def read_chunk(self) -> np.ndarray:
        return np.zeros(8000, dtype=np.float32)

    async def record_utterance(
        self, vad=None, max_duration_s=10.0, silence_timeout_s=1.5
    ) -> np.ndarray:
        self._call_count += 1
        if self._call_count > 2:
            raise asyncio.CancelledError("stop test")
        return np.ones(16000, dtype=np.float32)


class _StubAudioOut:
    def __init__(self) -> None:
        self.played: list[np.ndarray] = []

    async def play(
        self, audio: np.ndarray, sample_rate: int = 48000
    ) -> None:
        self.played.append(audio)

    def interrupt(self) -> None:
        pass

    async def stop(self) -> None:
        pass


class _StubVAD:
    def is_speech(self, chunk: np.ndarray) -> bool:
        return True

    def get_speech_prob(self, chunk: np.ndarray) -> float:
        return 0.9


class _StubSTT:
    async def transcribe(self, audio: np.ndarray) -> str:
        return "Привет, как дела?"


class _StubLLM:
    async def chat_stream(self, messages: list[dict]) -> object:
        for token in ["Отлично", "!"]:
            yield token

    async def chat(self, messages: list[dict]) -> str:
        return "Отлично!"


class _StubTTS:
    async def synthesize(self, text: str) -> np.ndarray | None:
        return np.zeros(48000, dtype=np.float32)


@pytest.mark.asyncio
async def test_full_pipeline_smoke(integration_config: Config) -> None:
    memory = SQLiteStore(integration_config)
    pipeline = Pipeline(
        audio_in=_StubAudioIn(),
        audio_out=_StubAudioOut(),
        vad=_StubVAD(),
        stt=_StubSTT(),
        llm=_StubLLM(),
        tts=_StubTTS(),
        memory=memory,
        config=integration_config,
    )

    pipeline.shutdown_event = asyncio.Event()

    async def stop_after_turns():
        await asyncio.sleep(0.5)
        pipeline.shutdown_event.set()
        pipeline.interrupt_event.set()

    async def instant_activate():
        pass

    pipeline._wait_for_button = instant_activate

    stop_task = asyncio.create_task(stop_after_turns())

    try:
        await pipeline.run()
    except asyncio.CancelledError:
        pass
    finally:
        stop_task.cancel()
        await memory.close()


@pytest.mark.asyncio
async def test_pipeline_saves_to_memory(integration_config: Config) -> None:
    memory = SQLiteStore(integration_config)
    audio_out = _StubAudioOut()

    pipeline = Pipeline(
        audio_in=_StubAudioIn(),
        audio_out=audio_out,
        vad=_StubVAD(),
        stt=_StubSTT(),
        llm=_StubLLM(),
        tts=_StubTTS(),
        memory=memory,
        config=integration_config,
    )

    pipeline.shutdown_event = asyncio.Event()

    async def instant_activate():
        pass

    pipeline._wait_for_button = instant_activate

    async def stop_after_first():
        await asyncio.sleep(0.3)
        pipeline.shutdown_event.set()
        pipeline.interrupt_event.set()

    stop_task = asyncio.create_task(stop_after_first())

    try:
        await pipeline.run()
    except asyncio.CancelledError:
        pass
    finally:
        stop_task.cancel()

    history = await memory.get_history(pipeline.session_id, limit=100)
    assert len(history) >= 2
    assert history[0]["role"] == "user"
    assert history[0]["content"] == "Привет, как дела?"
    assert history[1]["role"] == "assistant"
    assert "Отлично" in history[1]["content"]

    assert len(audio_out.played) > 0

    await memory.close()