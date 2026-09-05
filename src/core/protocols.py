from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Protocol, TypedDict

import numpy as np


class PipelineState(Enum):
    IDLE = auto()
    LISTENING = auto()
    PROCESSING_STT = auto()
    THINKING = auto()
    SPEAKING = auto()


class Message(TypedDict):
    role: str
    content: str
    timestamp: str


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


class AudioInput(Protocol):
    async def start(self) -> None: ...
    async def stop(self) -> None: ...
    async def read_chunk(self) -> np.ndarray: ...


class AudioOutput(Protocol):
    async def play(self, audio: np.ndarray, sample_rate: int) -> None: ...
    def interrupt(self) -> None: ...
    async def stop(self) -> None: ...

class VAD(Protocol):
    def is_speech(self, chunk: np.ndarray) -> bool: ...
    def get_speech_prob(self, chunk: np.ndarray) -> float: ...

class STTEngine(Protocol):
    async def transcribe(self, audio: np.ndarray) -> str: ...

class LLMClient(Protocol):
    async def chat_stream(self, messages: list[dict]) -> AsyncIterator[str]: ...
    async def chat(self, messages: list[dict]) -> str: ...

class TTSEngine(Protocol):
    async def synthesize(self, text: str) -> np.ndarray | None: ...

class WakeWordDetector(Protocol):
    def load(self) -> None: ...
    async def detect(self, audio: np.ndarray) -> bool: ...

class MemoryStore(Protocol):
    async def save_message(self, session_id: str, role: str, content: str) -> None: ...
    async def get_history(self, session_id: str, limit: int) -> list[dict]: ...
    async def create_session(self) -> str: ...
    async def delete_session(self, session_id: str) -> None: ...
