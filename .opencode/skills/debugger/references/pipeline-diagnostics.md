# Pipeline Diagnostics Reference

Stage-by-stage diagnostic procedures for the voice_ai pipeline: Mic → VAD → STT → LLM → TTS → Speakers.

## Stage 1: Microphone Input

**Logger:** `voice_ai.audio.input`  
**Source:** `src/audio/input.py`  
**Protocol:** `AudioInput.start()`, `AudioInput.stop()`, `AudioInput.read_chunk()`  
**Config:** `SAMPLE_RATE=16000`, `OUTPUT_DEVICE=None`

### Symptoms

| Symptom | Likely Cause | Check |
|---------|-------------|-------|
| No audio captured | Microphone not detected | `sd.query_devices()` |
| `DeviceNotFoundError` | Invalid device index in `.env` | Check `OUTPUT_DEVICE` |
| Very low amplitude | Mic gain too low | Check OS audio settings |
| Crackling/noise | Sample rate mismatch | Verify `SAMPLE_RATE=16000` |

### Diagnostic Steps

1. Check available audio devices:
   ```bash
   python -c "import sounddevice as sd; print(sd.query_devices())"
   ```

2. Test microphone capture:
   ```bash
   python scripts/test_mic.py
   ```

3. Run audio tests:
   ```bash
   pytest tests/test_audio.py -v -k "input or mic"
   ```

4. Check logs for `Microphone started (sample_rate=16000)` — if missing, `start()` failed silently.

### Log Patterns

- Normal: `Microphone started (sample_rate=16000)`
- Error: `Could not determine default output device`
- Warning: No audio-related log entries at all → `start()` was never called

---

## Stage 2: VAD (Voice Activity Detection)

**Logger:** `voice_ai.audio.vad`  
**Source:** `src/audio/vad.py`  
**Protocol:** `VAD.is_speech(chunk)`, `VAD.load()`  
**Config:** `VAD_THRESHOLD=0.5`, `VAD_MIN_SPEECH_DURATION_MS=250`, `VAD_MIN_SILENCE_DURATION_MS=100`, `VAD_SPEECH_PAD_MS=300`

### Symptoms

| Symptom | Likely Cause | Check |
|---------|-------------|-------|
| VAD never triggers speech | `VAD_THRESHOLD` too high | Lower to 0.3 |
| VAD triggers on noise | `VAD_THRESHOLD` too low | Raise to 0.7 |
| Speech cut off mid-sentence | `VAD_MIN_SILENCE_DURATION_MS` too short | Increase to 200-300ms |
| Brief noises trigger recording | `VAD_MIN_SPEECH_DURATION_MS` too short | Increase to 300-400ms |

### Diagnostic Steps

1. Check VAD loads correctly:
   ```bash
   python -c "from src.audio.vad import SileroVAD; from src.core.config import Config; v = SileroVAD(Config()); v.load(); print('VAD loaded')"
   ```

2. Run tests:
   ```bash
   pytest tests/test_audio.py -v -k "vad"
   ```

3. Set `LOG_LEVEL=DEBUG` to see `DEBUG` messages from `voice_ai.audio.vad`

### Log Patterns

- Normal: `Silero VAD model loaded`
- Normal (DEBUG): `Speech detected: prob=0.xx`
- Error: No VAD log entries → model failed to load

---

## Stage 3: STT (Speech-to-Text)

**Logger:** `voice_ai.stt`  
**Source:** `src/stt/whisper_engine.py`  
**Protocol:** `STTEngine.transcribe(audio) -> str`  
**Config:** `WHISPER_MODEL=large-v3`, `WHISPER_DEVICE=cuda`, `WHISPER_COMPUTE_TYPE=float16`  
**Exception hierarchy:** `STTError` → `EmptyTranscriptionError`

### Symptoms

| Symptom | Likely Cause | Check |
|---------|-------------|-------|
| `EmptyTranscriptionError` | Audio empty or too quiet | See Stage 1 & 2 |
| `RuntimeError: CUDA out of memory` | GPU memory conflict with Ollama | See known-issues #5 |
| Model loads very slowly | `large-v3` on CPU | Consider `WHISPER_MODEL=medium` |
| Wrong language transcription | Model not Russian-capable | Verify model supports Russian |
| `ImportError` on faster_whisper | Dependency missing | `pip install faster-whisper` |

### Diagnostic Steps

1. Verify model can be loaded:
   ```bash
   python -c "from src.stt.whisper_engine import FasterWhisperEngine; from src.core.config import Config; e = FasterWhisperEngine(Config()); e.load(); print('Whisper model loaded')"
   ```

2. Run tests:
   ```bash
   pytest tests/test_stt.py -v
   ```

3. Check GPU memory before/after loading:
   ```bash
   python -c "import torch; print(f'GPU free: {torch.cuda.mem_get_info()[0] / 1024**3:.1f} GB')"
   ```

### Log Patterns

- Normal: `Whisper model loaded`
- Normal: `Transcribed: <text> (<N> chars)`
- Warning: `Empty transcription, skipping`
- Error: `STT error: <message>`

---

## Stage 4: LLM (Ollama)

**Logger:** `voice_ai.llm`  
**Source:** `src/llm/ollama_client.py`  
**Protocol:** `LLMClient.chat_stream(messages)`, `LLMClient.chat(messages)`  
**Config:** `OLLAMA_BASE_URL=http://localhost:11434`, `OLLAMA_MODEL=qwen2.5:7b`, `OLLAMA_TIMEOUT=60`, `OLLAMA_TEMPERATURE=0.7`, `OLLAMA_NUM_CTX=4096`  
**Exception hierarchy:** `LLMError` → `LLMConnectionError`, `LLMTimeoutError`

### Symptoms

| Symptom | Likely Cause | Check |
|---------|-------------|-------|
| `LLMConnectionError` | Ollama server not running | `curl localhost:11434/api/tags` |
| `LLMTimeoutError` | Model too slow or overloaded | Increase `OLLAMA_TIMEOUT` |
| Connection refused | Wrong `OLLAMA_BASE_URL` | Verify URL in `.env` |
| Model not found | Model not pulled | `ollama pull qwen2.5:7b` |
| Empty response | Model returned empty content | Check `OLLAMA_NUM_PREDICT` (default 256) |

### Diagnostic Steps

1. Check Ollama is running:
   ```bash
   curl -s http://localhost:11434/api/tags
   ```

2. Verify model is available:
   ```bash
   ollama list
   ```

3. Test LLM directly:
   ```bash
   pytest tests/test_llm.py -v
   ```

4. Check config:
   ```bash
   python -c "from src.core.config import Config; c = Config(); print(f'OLLAMA_BASE_URL={c.ollama_base_url} OLLAMA_MODEL={c.ollama_model} OLLAMA_TIMEOUT={c.ollama_timeout}')"
   ```

### Log Patterns

- Normal: (streaming tokens received)
- Error: `LLM error: <message>`
- Error: `Cannot reach Ollama server`

---

## Stage 5: TTS (Text-to-Speech)

**Logger:** `voice_ai.tts`  
**Source:** `src/tts/silero_engine.py`  
**Protocol:** `TTSEngine.load()`, `TTSEngine.synthesize(text) -> np.ndarray | None`  
**Config:** `SILERO_LANGUAGE=ru`, `SILERO_SPEAKER=v5_ru`, `SILERO_VOICE=baya`, `SILERO_SAMPLE_RATE=48000`  
**Exception hierarchy:** `TTSError`

### Symptoms

| Symptom | Likely Cause | Check |
|---------|-------------|-------|
| `ImportError` / `ModuleNotFoundError` | `src/` namespace conflict | See known-issues #1 |
| `ValueError: speaker should be in...` | `silero_speaker` vs `silero_voice` confusion | See known-issues #2 |
| `ModuleNotFoundError: No module named 'omegaconf'` | Missing dependency | `pip install omegaconf`, see known-issues #4 |
| `TTSError` during synthesis | GPU OOM or model load failure | Check GPU memory |
| TTS returns `None` | Model not loaded, empty text, or synthesis failure | Check logs for specific error |
| Audio plays at wrong speed | Sample rate mismatch | See known-issues #3 |

### Diagnostic Steps

1. Verify Silero loads:
   ```bash
   python -c "from src.tts.silero_engine import SileroTTSEngine; from src.core.config import Config; e = SileroTTSEngine(Config()); e.load(); print('TTS loaded')"
   ```

2. Test synthesis:
   ```bash
   python -c "from src.tts.silero_engine import SileroTTSEngine; from src.core.config import Config; e = SileroTTSEngine(Config()); e.load(); r = e.synthesize('Привет'); print(f'Result: {type(r)} shape={getattr(r, \"shape\", None)}')"
   ```

3. Run tests:
   ```bash
   pytest tests/test_tts.py -v
   ```

4. Check `.env` config:
   ```bash
   python -c "from src.core.config import Config; c = Config(); print(f'SILERO_SPEAKER={c.silero_speaker} SILERO_VOICE={c.silero_voice} SILERO_SAMPLE_RATE={c.silero_sample_rate}')"
   ```

### Log Patterns

- Normal: `Silero TTS model loaded`
- Normal: `TTS: synthesizing text (N chars): <preview>`
- Normal: `TTS: v5 synthesis result shape=(N,) dtype=float32`
- Warning: `TTS: v5 result is all zeros (silence)!`
- Warning: `TTS returned None for non-empty text, falling back to text-only mode`
- Error: `TTS synthesis failed: <message>`

---

## Stage 6: Audio Output (Speakers)

**Logger:** `voice_ai.audio.output`  
**Source:** `src/audio/output.py`  
**Protocol:** `AudioOutput.play(audio, sample_rate)`, `AudioOutput.stop()`  
**Config:** `SILERO_SAMPLE_RATE=48000`, `OUTPUT_DEVICE=None`

### Symptoms

| Symptom | Likely Cause | Check |
|---------|-------------|-------|
| No sound output | Wrong device or muted speakers | Check `OUTPUT_DEVICE` in `.env` |
| Crackling/distortion | Sample rate mismatch | Verify `SILERO_SAMPLE_RATE` matches output |
| `DeviceNotFoundError` | Invalid device index | `sd.query_devices()` |
| Playback too fast/slow | Resampling error | Check log for resampling messages |

### Diagnostic Steps

1. Check audio devices:
   ```bash
   python -c "import sounddevice as sd; devs = sd.query_devices(); print(devs)"
   ```

2. Run tests:
   ```bash
   pytest tests/test_audio.py -v -k "output"
   ```

3. Look for log output device info:
   ```
   Default audio output: [<index>] <device_name> (sr=<rate>, ch=<channels>)
   ```

### Log Patterns

- Normal: `Default audio output: [<index>] <name> (sr=<rate>)`
- Normal: `Playing N samples at <rate>Hz on device <name>`
- Normal: `Resampling <old>Hz -> <new>Hz for device [<index>] <name>`
- Warning: `Could not determine default output device`
- Warning: `Could not query audio output device`
- Error: `Playback start error: <message>`

---

## Stage 7: Memory (SQLite)

**Logger:** (uses standard `logging` in `src/memory/database.py`)  
**Source:** `src/memory/database.py`  
**Protocol:** `MemoryStore.create_session()`, `MemoryStore.save_message()`, `MemoryStore.get_history()`  
**Config:** `DB_PATH=data/voice_ai.db`, `HISTORY_LIMIT=50`  
**Exception hierarchy:** `MemoryError`

### Symptoms

| Symptom | Likely Cause | Check |
|---------|-------------|-------|
| `OperationalError: database is locked` | WAL mode not enabled | See known-issues #6 |
| Session not persisted | DB path doesn't exist | Check `DB_PATH` dir exists |
| History limit too small | `HISTORY_LIMIT` too low | Increase in `.env` |

### Diagnostic Steps

1. Check DB integrity:
   ```bash
   python -c "import sqlite3; conn = sqlite3.connect('data/voice_ai.db'); print(conn.execute('PRAGMA integrity_check').fetchone()); print(conn.execute('PRAGMA journal_mode').fetchone()); conn.close()"
   ```

2. Run tests:
   ```bash
   pytest tests/test_memory.py -v
   ```

---

## Pipeline State Machine

```
IDLE → LISTENING → PROCESSING_STT → THINKING → SPEAKING → IDLE
                                        ↑                    |
                                        └── (interrupt) ─────┘
```

### State-Related Log Patterns

| State | Log Entry |
|-------|-----------|
| IDLE | `Waiting for activation (press Enter to talk)...` |
| LISTENING | `Listening...` |
| PROCESSING_STT | `Transcription: "<text>"` |
| THINKING | (streaming tokens from LLM) |
| SPEAKING | `TTS: synthesizing response (N chars)` |

### Common Pipeline-Level Issues

| Issue | Log Pattern | Likely Stage |
|-------|-------------|-------------|
| No response at all | Pipeline starts, no state transitions | Audio Input / VAD |
| Empty response from assistant | `Assistant: ""` | STT / LLM |
| Text but no audio | `No audio to play (TTS returned None)` | TTS |
| Pipeline hangs | No log entries after `Listening...` | VAD / STT |
| Pipeline crashes | `Pipeline error: <exception>` | Any stage |