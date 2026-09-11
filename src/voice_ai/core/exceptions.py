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


class WakeWordError(VoiceAIError):
    """Wake word detection errors."""


class MemoryError(VoiceAIError):
    """Database/storage errors."""
