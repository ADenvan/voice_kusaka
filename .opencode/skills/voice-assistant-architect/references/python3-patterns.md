# Python 3 Patterns for voice_ai

## Project Configuration

### pydantic-settings (core/config.py)

```python
from pydantic_settings import BaseSettings, SettingsConfigDict

class Config(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    sample_rate: int = 16000
    chunk_duration_ms: int = 500
    vad_threshold: float = 0.5

    whisper_model: str = "large-v3"
    whisper_device: str = "cuda"
    whisper_compute_type: str = "float16"

    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "qwen2.5:7b"
    ollama_timeout: int = 60
    ollama_temperature: float = 0.7
    ollama_num_ctx: int = 4096

    silero_language: str = "ru"
    silero_speaker: str = "baya"

    db_path: str = "data/voice_ai.db"
    history_limit: int = 50

    log_level: str = "INFO"

config = Config()
```

Load once at startup, pass via dependency injection. Never read `.env` elsewhere.

---

## Async Patterns

### Pipeline with asyncio.Queue

```python
import asyncio
from collections.abc import AsyncIterator

async def audio_producer(queue: asyncio.Queue[np.ndarray], audio_in: AudioInput) -> None:
    await audio_in.start()
    try:
        while True:
            chunk = await audio_in.read_chunk()
            await queue.put(chunk)
    finally:
        await audio_in.stop()

async def stt_consumer(
    in_queue: asyncio.Queue[np.ndarray],
    out_queue: asyncio.Queue[str],
    stt: STTEngine,
) -> None:
    buffer: list[np.ndarray] = []
    while True:
        chunk = await in_queue.get()
        buffer.append(chunk)
        # When VAD signals end of speech, transcribe buffer
        # ... (VAD integration determines when to flush)
        audio = np.concatenate(buffer)
        text = await asyncio.to_thread(stt.transcribe_sync, audio)
        if text.strip():
            await out_queue.put(text)
        buffer.clear()
```

### asyncio.to_thread for CPU-bound work

Whisper and Silero are CPU/GPU-bound. Use `to_thread` to avoid blocking:

```python
async def transcribe(self, audio: np.ndarray) -> str:
    return await asyncio.to_thread(self._transcribe_sync, audio)

def _transcribe_sync(self, audio: np.ndarray) -> str:
    segments, _ = self.model.transcribe(audio, language="ru")
    return " ".join(s.text for s in segments).strip()
```

### Streaming with AsyncIterator

```python
async def chat_stream(self, messages: list[dict]) -> AsyncIterator[str]:
    async with httpx.AsyncClient() as client:
        async with client.stream(
            "POST",
            f"{self.base_url}/api/chat",
            json={
                "model": self.model,
                "messages": messages,
                "stream": True,
            },
            timeout=self.timeout,
        ) as response:
            async for line in response.aiter_lines():
                if not line.strip():
                    continue
                chunk = json.loads(line)
                if content := chunk.get("message", {}).get("content", ""):
                    yield content
```

### Graceful Shutdown Pattern

```python
async def run_pipeline(self) -> None:
    tasks = [
        asyncio.create_task(self._audio_loop()),
        asyncio.create_task(self._stt_loop()),
        asyncio.create_task(self._llm_loop()),
        asyncio.create_task(self._tts_loop()),
    ]
    try:
        await self.shutdown_event.wait()
    finally:
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        await self._cleanup()
```

---

## Type Hints (Python 3.13)

### Protocols for Component Interfaces

```python
from typing import Protocol, AsyncIterator, NoReturn, Self
import numpy as np

class STTEngine(Protocol):
    async def transcribe(self, audio: np.ndarray) -> str: ...

class LLMClient(Protocol):
    async def chat_stream(self, messages: list[dict]) -> AsyncIterator[str]: ...
    async def chat(self, messages: list[dict]) -> str: ...

class TTSEngine(Protocol):
    async def synthesize(self, text: str) -> np.ndarray: ...
```

Structural subtyping — no inheritance required, any class with matching
methods satisfies the Protocol.

### TypedDict for Message Format

```python
from typing import TypedDict

class Message(TypedDict):
    role: str       # "user" | "assistant" | "system"
    content: str
    timestamp: str  # ISO 8601
```

### Enum for Pipeline State

```python
from enum import Enum, auto

class PipelineState(Enum):
    IDLE = auto()
    LISTENING = auto()
    PROCESSING_STT = auto()
    THINKING = auto()
    SPEAKING = auto()
```

### assert_never for Exhaustiveness

```python
from typing import assert_never

def state_label(state: PipelineState) -> str:
    match state:
        case PipelineState.IDLE: return "idle"
        case PipelineState.LISTENING: return "listening"
        case PipelineState.PROCESSING_STT: return "processing_stt"
        case PipelineState.THINKING: return "thinking"
        case PipelineState.SPEAKING: return "speaking"
        case _: assert_never(state)
```

---

## Exception Hierarchy

```python
class VoiceAIError(Exception):
    """Base exception for all voice_ai errors."""

class AudioError(VoiceAIError):
    """Audio capture/playback errors."""

class DeviceNotFoundError(AudioError):
    """Audio device not available."""

class STTError(VoiceAIError):
    """Speech-to-text errors."""

class EmptyTranscriptionError(STTError):
    """STT returned empty result."""

class LLMError(VoiceAIError):
    """LLM connection or generation errors."""

class LLMConnectionError(LLMError):
    """Cannot reach Ollama server."""

class LLMTimeoutError(LLMError):
    """LLM generation timed out."""

class TTSError(VoiceAIError):
    """Text-to-speech errors."""

class MemoryError(VoiceAIError):
    """Database/storage errors."""
```

Usage:

```python
try:
    text = await self.stt.transcribe(audio)
except STTError as e:
    logger.error("STT failed: %s", e)
    text = ""
```

---

## Dependency Injection

No DI framework. Pass dependencies via `__init__`:

```python
class Pipeline:
    def __init__(
        self,
        audio_in: AudioInput,
        audio_out: AudioOutput,
        vad: VAD,
        stt: STTEngine,
        llm: LLMClient,
        tts: TTSEngine,
        memory: MemoryStore,
        config: Config,
    ) -> None:
        self.audio_in = audio_in
        self.audio_out = audio_out
        # ...

def create_pipeline(config: Config) -> Pipeline:
    audio_in = SoundDeviceInput(config)
    audio_out = SoundDeviceOutput(config)
    vad = SileroVAD(config)
    stt = FasterWhisperEngine(config)
    llm = OllamaClient(config)
    tts = SileroTTSEngine(config)
    memory = SQLiteStore(config)
    return Pipeline(audio_in, audio_out, vad, stt, llm, tts, memory, config)
```

Easy to test — swap any component with a mock implementing the Protocol.

---

## Logging

```python
import logging

logger = logging.getLogger("voice_ai")

# Structured format — machine-readable, not print()
formatter = logging.Formatter(
    "%(asctime)s | %(name)s | %(levelname)s | %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)

# Usage
logger.info("STT transcribed: %s (%d chars)", text[:50], len(text))
logger.error("Ollama connection failed: %s", e)
logger.debug("Audio chunk: shape=%s dtype=%s", chunk.shape, chunk.dtype)
```

Never use `print()` for logging. Use `logger.debug` for verbose output
and `logger.info` for state transitions.

---

## Dataclass for Structured Data

```python
from dataclasses import dataclass, field

@dataclass
class TurnResult:
    user_text: str
    assistant_text: str
    audio_duration_s: float
    latency_ms: int
    interrupted: bool = False

@dataclass
class SessionInfo:
    session_id: str
    created_at: str
    turn_count: int = 0
    messages: list[Message] = field(default_factory=list)
```
