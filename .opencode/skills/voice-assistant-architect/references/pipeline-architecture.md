# Pipeline Architecture

## Full Data Flow Diagram

```
                        ┌──────────────────────────────────────────────────┐
                        │              Pipeline Orchestrator               │
                        │              (core/pipeline.py)                  │
                        └──┬──────────┬──────────┬──────────┬────────────┘
                           │          │          │          │
            ┌──────────────┘    │     │     │     └──────────────┐
            ▼                   ▼     │     ▼                   ▼
   ┌────────────┐      ┌──────────┐  │  ┌──────────┐    ┌────────────┐
   │  Mic In    │─────▶│   VAD    │  │  │   STT    │    │  Memory    │
   │ (16kHz     │      │ (silero  │  │  │ (faster  │    │ (SQLite    │
   │  PCM mono) │      │  VAD)    │  │  │  whisper)│    │  aiosqlite)│
   └────────────┘      └────┬─────┘  │  └────┬─────┘    └─────┬──────┘
                            │        │       │                │
                     speech_detected  │    text:str      history:messages
                            │        │       │                │
                            ▼        │       ▼                ▼
                     ┌───────────┐   │  ┌─────────────┐  ┌──────────┐
                     │  Buffer   │───┘  │     LLM     │◀─│ Context  │
                     │ (queue)   │      │  (Ollama,   │  │ Builder  │
                     └───────────┘      │  streaming) │  └──────────┘
                                        └──────┬──────┘
                                          tokens│
                                                ▼
                                         ┌────────────┐
                                         │    TTS     │
                                         │  (Silero)  │
                                         └──────┬─────┘
                                                │ audio:ndarray
                                                ▼
                                         ┌────────────┐      ┌──────────┐
                                         │ Audio Out  │─────▶│ Speaker  │
                                         │(resample)  │      │          │
                                         └────────────┘      └──────────┘
```

## Async Model

### Event Loop

Single `asyncio` event loop. All I/O-bound operations are coroutines.
CPU-bound operations (Whisper inference, Silero synthesis) run in
`asyncio.to_thread()` to avoid blocking the loop.

### Inter-Module Queues

```
audio_queue:  asyncio.Queue[np.ndarray]   # VAD → STT
text_queue:   asyncio.Queue[str]           # STT → LLM
token_queue:  asyncio.Queue[str]           # LLM → TTS (collected into full text)
audio_out_q:  asyncio.Queue[np.ndarray]    # TTS → Speaker
```

Queue sizes:
- `audio_queue`: maxsize=10 (each chunk ~0.5s of audio)
- `text_queue`: maxsize=5
- `token_queue`: maxsize=100 (tokens arrive fast)
- `audio_out_q`: maxsize=5 (each chunk ~2-5s of audio)

### Signal Events

```python
interrupt_event: asyncio.Event   # Set when user interrupts (starts speaking)
shutdown_event: asyncio.Event    # Set for graceful shutdown
idle_event: asyncio.Event        # Set when pipeline is IDLE
```

## Pipeline Orchestrator

### State Machine

```
         ┌──────────────────────────────────────────────────┐
         │                                                  │
         ▼                                                  │
  ┌──────────┐   button press /    ┌────────────┐          │
  │   IDLE   │────────────────────▶│ LISTENING  │          │
  └──────────┘   wake word         └─────┬──────┘          │
       ▲                              speech_end             │
       │                                │                    │
       │                                ▼                    │
       │                        ┌──────────────┐             │
       │                        │PROCESSING_STT│             │
       │                        └──────┬───────┘             │
       │                          text │                     │
       │                               ▼                     │
       │                         ┌───────────┐              │
       │                         │  THINKING  │─────┐       │
       │                         └─────┬─────┘     │       │
       │                          text │           │timeout │
       │                               ▼           │       │
       │                         ┌───────────┐    │       │
       │     playback_done       │  SPEAKING  │◀───┘       │
       │◄───────────────────────└─────┬──────┘             │
       │                                  │interrupt        │
       │                                  └─────────────────┘
       └────────────────────────────────────────────────────┘
                    (interrupt during SPEAKING → LISTENING)
```

### Core Implementation Pattern

```python
class Pipeline:
    def __init__(self, config: Config):
        self.state = PipelineState.IDLE
        self.audio_in: AudioInput
        self.vad: VAD
        self.stt: STTEngine
        self.llm: LLMClient
        self.tts: TTSEngine
        self.audio_out: AudioOutput
        self.memory: MemoryStore
        self.interrupt_event = asyncio.Event()
        self._tasks: list[asyncio.Task] = []

    async def run(self) -> NoReturn:
        """Main loop — runs until shutdown_event is set."""
        while not self.shutdown_event.is_set():
            await self._wait_for_activation()
            await self._listen_and_process()

    async def _listen_and_process(self) -> None:
        """One complete turn: listen → transcribe → think → speak."""
        self.state = PipelineState.LISTENING
        audio = await self._record_until_silence()

        self.state = PipelineState.PROCESSING_STT
        text = await self.stt.transcribe(audio)
        if not text.strip():
            self.state = PipelineState.IDLE
            return

        await self.memory.save_message(session_id=self.session_id, role="user", content=text)

        self.state = PipelineState.THINKING
        messages = await self.memory.get_history(self.session_id, limit=config.history_limit)
        response_parts: list[str] = []
        async for token in self.llm.chat_stream(messages):
            response_parts.append(token)
            if self.interrupt_event.is_set():
                break
        response = "".join(response_parts)

        await self.memory.save_message(session_id=self.session_id, role="assistant", content=response)

        self.state = PipelineState.SPEAKING
        audio_response = await self.tts.synthesize(response)
        if not self.interrupt_event.is_set():
            await self.audio_out.play(audio_response, sample_rate=48000)

        self.interrupt_event.clear()
        self.state = PipelineState.IDLE
```

## Data Formats at Each Stage

| Stage | Input | Output | Format |
|-------|-------|--------|--------|
| Mic capture | Microphone stream | PCM chunks | float32 ndarray, 16kHz, mono, shape=(N,) |
| VAD | PCM chunk | speech/void flag | bool |
| STT | PCM audio (full utterance) | Text | str, UTF-8, Russian |
| LLM | messages[] | tokens → full text | str chunks → str |
| TTS | Text | Audio | float32 ndarray, 48kHz, mono (Silero native) |
| Audio Out | Audio + sample_rate | Speaker stream | resample to device rate if needed |

## Latency Budget (Target)

| Stage | Target | Notes |
|-------|--------|-------|
| VAD | <50ms | Per-chunk decision |
| STT | 1-3s | Depends on utterance length + GPU |
| LLM (first token) | <1s | Ollama local, depends on model |
| LLM (full response) | 3-10s | Depends on response length |
| TTS | <1s | Silero is fast, ~100ms for short phrase |
| Audio output | <100ms | sounddevice latency |
| **Total (first audio)** | **<5s** | From end of speech to first audio out |

## Interrupt Handling

When the user starts speaking during SPEAKING state:

1. `VAD` detects speech → sets `interrupt_event`
2. `audio_out.play()` checks event between chunks → stops playback
3. Pipeline transitions to LISTENING → records new utterance
4. Interrupted response is saved to memory as-is (partially generated)

## Graceful Shutdown

1. Set `shutdown_event`
2. Wait for current turn to complete (max 5s timeout)
3. Cancel all `asyncio.Task` objects
4. Close database connection
5. Release audio devices
