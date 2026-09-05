---
name: voice-assistant-architect
description: >
  Voice architecture AI-assistant voice_ai.
  Full Conveyor: Microphone → VAD → STT → LLM → TTS → Speakers.
  Russian language, Ollama, faster-whisper, Silero TTS, SQLite, Typer CLI, FastAPI.
---

# voice_ai — Architect Skill

## Role

Expert architect for **voice_ai** — a local, Russian-language voice AI assistant
running on Windows (Python 3.13). The system processes the full pipeline:

```
Микрофон → [VAD] → Буфер → [faster-whisper STT] → Текст
  → [Ollama LLM, streaming] → Токены → Полный ответ
  → [Silero TTS] → Аудио-буфер → [sounddevice] → Динамики
```

Key constraints: 1 user, local machine, Russian only, persistent memory (SQLite).

## When to Use

- Designing or modifying any module in the pipeline
- Choosing between implementation approaches
- Reviewing architecture for correctness, latency, or error handling
- Planning new features (wake word, API endpoints, memory management)
- Debugging integration issues between pipeline stages

## Project Structure

```
voice_ai/
├── src/
│   ├── core/
│   │   ├── config.py              # pydantic-settings, .env (silero_speaker vs silero_voice)
│   │   ├── pipeline.py            # Pipeline orchestrator, prints assistant response
│   │   └── exceptions.py          # Custom exception hierarchy
│   ├── audio/
│   │   ├── input.py               # sounddevice: microphone capture + VAD
│   │   ├── output.py              # sounddevice: speaker playback (resamples to device rate)
│   │   └── vad.py                 # Silero VAD (512-sample windows)
│   ├── stt/
│   │   └── whisper_engine.py      # faster-whisper, Russian, CUDA, .load() preload
│   ├── llm/
│   │   ├── ollama_client.py       # Ollama API, streaming
│   │   └── prompt_builder.py      # System prompt, context, tools
│   ├── tts/
│   │   └── silero_engine.py       # Silero TTS v5 (bypasses src/ conflict, .load() preload)
│   ├── memory/
│   │   ├── database.py            # SQLite + aiosqlite
│   │   └── context.py             # Dialog context management
│   ├── api/                       # (Phase 3 — FastAPI, not yet implemented)
│   └── cli/
│       └── app.py                 # Typer CLI: `run` and `chat` commands
├── tests/
│   ├── test_audio.py
│   ├── test_config.py
│   ├── test_integration.py
│   ├── test_llm.py
│   ├── test_memory.py
│   ├── test_pipeline.py
│   ├── test_stt.py
│   ├── test_tts.py
│   └── conftest.py
├── scripts/
│   └── test_mic.py                # Microphone diagnostic script
├── data/
│   └── voice_ai.db                # SQLite database
├── .env                           # Environment variables
├── .env.example                   # Template for .env
├── requirements.txt               # Runtime dependencies
├── requirements-dev.txt           # Dev dependencies (pytest, etc.)
└── pyproject.toml                 # Project metadata
```

## Component Interfaces

Each module exposes a Protocol or ABC with minimal surface area:

### AudioInput
```python
class AudioInput(Protocol):
    async def start(self) -> None: ...
    async def stop(self) -> None: ...
    async def read_chunk(self) -> np.ndarray: ...  # PCM 16-bit 16kHz mono
```

### STTEngine
```python
class STTEngine(Protocol):
    async def transcribe(self, audio: np.ndarray) -> str: ...
```

### LLMClient
```python
class LLMClient(Protocol):
    async def chat_stream(self, messages: list[dict]) -> AsyncIterator[str]: ...
    async def chat(self, messages: list[dict]) -> str: ...
```

### TTSEngine
```python
class TTSEngine(Protocol):
    def load(self) -> None: ...                      # Pre-load model (called at pipeline start)
    async def synthesize(self, text: str) -> np.ndarray | None: ...  # PCM float32, multirate (v5: 8/24/48kHz)
```

### AudioOutput
```python
class AudioOutput(Protocol):
    async def play(self, audio: np.ndarray, sample_rate: int) -> None: ...
    async def stop(self) -> None: ...
```

### MemoryStore
```python
class MemoryStore(Protocol):
    async def save_message(self, session_id: str, role: str, content: str) -> None: ...
    async def get_history(self, session_id: str, limit: int) -> list[dict]: ...
    async def create_session(self) -> str: ...
```

## Pipeline Flow

```
┌─────────┐    ┌─────┐    ┌──────────┐    ┌───────────┐
│ Mic In  │───▶│ VAD │───▶│   STT    │───▶│    LLM    │
│ (16kHz) │    │     │    │(whisper) │    │ (Ollama)  │
└─────────┘    └─────┘    └──────────┘    └─────┬─────┘
                                           stream│tokens
                                                 ▼
                                           ┌───────────┐    ┌───────────┐    ┌──────────┐
                                           │    TTS    │───▶│ Audio Out │───▶│ Speaker  │
                                           │ (Silero)  │    │(resample) │    │          │
                                           └───────────┘    └───────────┘    └──────────┘
```

### Pipeline States

```
IDLE ──▶ LISTENING ──▶ PROCESSING_STT ──▶ THINKING ──▶ SPEAKING ──▶ IDLE
             │                                                  ▲
             └────────── (interrupt: user speaks) ─────────────┘
```

### Async Model

- Main loop: `asyncio` event loop
- Inter-module communication: `asyncio.Queue`
- Signals: `asyncio.Event` (e.g., `interrupt_event`)
- Each stage is a coroutine consuming from an input queue and producing to an output queue

## Implementation Phases

### Phase 1: MVP (Button activation, CLI) ✅ DONE
- `core/config.py` — configuration with pydantic-settings
- `audio/input.py` — record on button press via sounddevice
- `audio/vad.py` — Silero VAD (512-sample windows at 16kHz)
- `stt/whisper_engine.py` — faster-whisper transcription (CUDA)
- `llm/ollama_client.py` — Ollama chat with streaming
- `tts/silero_engine.py` — Silero TTS v5 (package model, voice selection)
- `audio/output.py` — playback via sounddevice
- `memory/database.py` — SQLite with aiosqlite
- `core/pipeline.py` — sequential pipeline with console output
- `cli/app.py` — Typer CLI

### Phase 2: VAD + Wake Word
- `audio/vad.py` — Silero VAD ✅ DONE (512-sample windows)
- `audio/wake_word.py` — detect "voice_ai" keyword
- Update pipeline for continuous listening

### Phase 3: API + WebSocket
- `api/server.py` — FastAPI with REST + WS
- `api/routes.py` — endpoints for chat, history, config
- Stream audio chunks over WebSocket

## Error Handling Strategy

| Stage | Error | Action |
|-------|-------|--------|
| Audio input | Device not found | Fail fast with clear message |
| VAD | False positive | Reset buffer, continue listening |
| STT | Empty transcription | Prompt user to repeat |
| LLM | Connection refused | Retry with backoff, fallback message |
| LLM | Timeout | Return partial response + apology |
| TTS | Synthesis failure | Print text to console, log error |
| Audio output | Playback error | Log + continue (non-fatal) |
| Memory | DB locked | Retry with WAL mode |

## Configuration (.env)

```env
# Audio
SAMPLE_RATE=16000
CHUNK_DURATION_MS=500
VAD_THRESHOLD=0.5

# STT
WHISPER_MODEL=large-v3
WHISPER_DEVICE=cuda
WHISPER_COMPUTE_TYPE=float16

# LLM
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=qwen2.5:7b
OLLAMA_TIMEOUT=60
OLLAMA_TEMPERATURE=0.7
OLLAMA_NUM_CTX=4096

# TTS
SILERO_LANGUAGE=ru
SILERO_SPEAKER=v5_ru
SILERO_VOICE=baya
SILERO_SAMPLE_RATE=48000

# Memory
DB_PATH=data/voice_ai.db
HISTORY_LIMIT=50

# Pipeline
LOG_LEVEL=INFO
```

## Known Issues & Workarounds

### Silero TTS `src` namespace conflict

The Silero TTS repo (`snakers4_silero-models_master`) uses `from src.silero import ...` in its
`hubconf.py`. Our project also has a `src/` package. Python gives regular packages (with
`__init__.py`) priority over namespace packages regardless of `sys.path` order, so our `src`
shadows Silero's.

**Workaround** (`src/tts/silero_engine.py`):
1. Remove our `src` from `sys.modules` (saving/restoring around the import)
2. Create a temporary `__init__.py` in the Silero repo's `src/` to make it a regular package
3. Insert the Silero repo dir at `sys.path[0]`
4. Import `from src.silero import silero_tts`
5. Restore `sys.modules` and remove the temp `__init__.py` in a `finally` block

### Silero TTS v5 speaker vs model name

Silero v5 uses a **two-level naming scheme**:
- `silero_speaker` (`v5_ru`) — the model name passed to `silero_tts()` for loading
- `silero_voice` (`baya`, `aidar`, `kseniya`, `eugene`, `xenia`) — the voice passed to
  `model.apply_tts(speaker=...)` for synthesis

Passing `v5_ru` as `speaker` to `apply_tts()` raises `speaker should be in aidar, baya, ...`.

### Silero TTS v5 sample rates

The v5_ru model supports multiple sample rates: `[8000, 24000, 48000]`. The config default is
`48000`. Lower rates save bandwidth at the cost of quality.

### Dependency: omegaconf

Silero TTS requires `omegaconf` for loading `models.yml`. This is not pulled in automatically
by `torch` — it must be in `requirements.txt` explicitly.

## Runtime Dependencies

| Package | Purpose | Notes |
|---------|---------|-------|
| faster-whisper | STT (Whisper large-v3) | CUDA support, CTranslate2 backend |
| torch | Silero VAD + TTS model loading | GPU optional |
| sounddevice | Microphone input + speaker output | PortAudio bindings |
| httpx | Ollama API client (async + streaming) | |
| pydantic-settings | Config from `.env` | |
| aiosqlite | Async SQLite for memory store | |
| typer | CLI interface | |
| numpy | Audio buffer manipulation | |
| omegaconf | Silero models.yml loading | Required by Silero TTS |

## References

Deep-dive documentation for each architectural concern:

- {file:skills/voice-assistant-architect/references/pipeline-architecture.md} — Data flow, async model, state machine, latency budgets
- {file:skills/voice-assistant-architect/references/stack-selection.md} — Technology choices with justification
- {file:skills/voice-assistant-architect/references/python3-patterns.md} — Python 3.13 idioms, async patterns, type hints
- {file:skills/voice-assistant-architect/references/audio-processing.md} — Audio formats, VAD, wake word, buffering
- {file:skills/voice-assistant-architect/references/ollama-integration.md} — Ollama setup, models, API, streaming, Russian support
