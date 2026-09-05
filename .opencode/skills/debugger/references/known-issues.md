# Known Issues Catalog

Known problems in the voice_ai pipeline with workarounds and resolution steps.

## 1. Silero TTS `src/` Namespace Conflict

**Severity:** Critical  
**Stage:** TTS  
**Symptom:** `ModuleNotFoundError` or `ImportError` when loading Silero TTS model  
**Exception:** `TTSError`

### Root Cause

The Silero TTS repository (`snakers4_silero-models_master`) uses `from src.silero import ...` in its `hubconf.py`. The voice_ai project also has a `src/` package with `__init__.py`. Python prioritizes regular packages over namespace packages regardless of `sys.path` order, so the project's `src` shadows Silero's.

### Workaround

Implemented in `src/tts/silero_engine.py`:

1. Remove project's `src` from `sys.modules` (saving/restoring around the import)
2. Create a temporary `__init__.py` in the Silero repo's `src/` directory
3. Insert Silero repo dir at `sys.path[0]`
4. Import `from src.silero import silero_tts`
5. Restore `sys.modules` and remove temp `__init__.py` in a `finally` block

**Do NOT refactor the `src/` package layout without understanding this workaround.**

### Diagnostic

```bash
python -c "from src.tts.silero_engine import SileroTTSEngine; from src.core.config import Config; e = SileroTTSEngine(Config()); e.load(); print('Silero loaded successfully')"
```

If this fails with an import error, the namespace conflict is occurring.

---

## 2. Silero TTS v5 Speaker vs Voice Naming

**Severity:** High  
**Stage:** TTS  
**Symptom:** `ValueError: speaker should be in aidar, baya, kseniya, eugene, xenia`  
**Exception:** `TTSError`

### Root Cause

Silero v5 uses a two-level naming scheme:

- `silero_speaker` (`v5_ru`) — the **model name** passed to `silero_tts()` for loading
- `silero_voice` (`baya`, `aidar`, `kseniya`, `eugene`, `xenia`) — the **voice** passed to `model.apply_tts(speaker=...)` for synthesis

Passing `v5_ru` as `speaker` to `apply_tts()` raises the error above.

### Correct Usage

```python
# Load model with speaker name
model, symbols = silero_tts(speaker="v5_ru")  # silero_speaker

# Synthesize with voice name
audio = model.apply_tts(text="...", speaker="baya")  # silero_voice
```

### Config (.env)

```env
SILERO_SPEAKER=v5_ru     # Model name for loading
SILERO_VOICE=baya         # Voice name for synthesis
```

### Diagnostic

Check that `.env` has both `SILERO_SPEAKER` and `SILERO_VOICE` set correctly.

---

## 3. Silero TTS v5 Sample Rate Mismatch

**Severity:** Medium  
**Stage:** TTS → Audio Output  
**Symptom:** Audio plays at wrong speed (too fast or too slow), or `TTSError`  

### Root Cause

The v5_ru model supports multiple sample rates: `[8000, 24000, 48000]`. The output sample rate must match what `AudioOutput.play()` expects. If `SILERO_SAMPLE_RATE` in `.env` doesn't match the actual synthesis rate, playback will be distorted.

### Workaround

Ensure `.env` has:

```env
SILERO_SAMPLE_RATE=48000
```

And that `AudioOutput.play()` receives the matching `sample_rate` parameter.

### Diagnostic

Check logs for:

```
TTS: v5 synthesis result shape=... dtype=... 
AudioOutput.play: dtype=... shape=... sr=48000
```

If sample rates don't match, resampling occurs automatically but may introduce quality loss.

---

## 4. Missing `omegaconf` Dependency

**Severity:** High  
**Stage:** TTS  
**Symptom:** `ModuleNotFoundError: No module named 'omegaconf'` when loading Silero model  
**Exception:** `TTSError`

### Root Cause

Silero TTS requires `omegaconf` for loading `models.yml`. This dependency is not automatically pulled in by `torch`.

### Fix

```bash
pip install omegaconf
```

Verify it's in `requirements.txt`.

### Diagnostic

```bash
python -c "import omegaconf; print(f'omegaconf: {omegaconf.__version__}')"
```

---

## 5. CUDA Out of Memory (Whisper + Ollama)

**Severity:** High  
**Stage:** STT / LLM  
**Symptom:** `RuntimeError: CUDA out of memory` during whisper transcription or Ollama inference  
**Exception:** `STTError` or `LLMError`

### Root Cause

Both faster-whisper (with CUDA) and Ollama (with GPU acceleration) compete for GPU memory. On GPUs with limited VRAM (e.g., 6-8 GB), loading large Whisper models can exhaust memory before Ollama can run.

### Workarounds

1. **Reduce Whisper model size**: Use `WHISPER_MODEL=medium` or `small` instead of `large-v3`
2. **Use CPU for Whisper**: Set `WHISPER_DEVICE=cpu` (slower but frees GPU memory)
3. **Reduce Ollama context**: Lower `OLLAMA_NUM_CTX` from 4096 to 2048
4. **Force Ollama to CPU**: Set `OLLAMA_KEEP_ALIVE=0` and run `OLLAMA_LLM_DEVICE=cpu`
5. **Use float16 compute**: Already default with `WHISPER_COMPUTE_TYPE=float16`

### Diagnostic

```bash
python -c "import torch; print(f'GPU memory: {torch.cuda.mem_get_info()[0] / 1024**3:.1f} GB free / {torch.cuda.mem_get_info()[1] / 1024**3:.1f} GB total')"
```

---

## 6. SQLite Database Locked

**Severity:** Medium  
**Stage:** Memory  
**Symptom:** `aiosqlite.core.OperationalError: database is locked`  
**Exception:** `MemoryError`

### Root Cause

SQLite in default journal mode only allows one writer at a time. Concurrent async operations can cause lock contention.

### Workaround

The project uses WAL mode (Write-Ahead Logging). Ensure this is set in `src/memory/database.py`:

```python
await db.execute("PRAGMA journal_mode=WAL")
```

### Diagnostic

```bash
python -c "import sqlite3; conn = sqlite3.connect('data/voice_ai.db'); print(conn.execute('PRAGMA journal_mode').fetchone()); conn.close()"
```

Expected output: `('wal',)`

---

## 7. Audio Device Not Found / Wrong Device Index

**Severity:** High  
**Stage:** Audio Input / Audio Output  
**Symptom:** `DeviceNotFoundError` or no sound during playback  
**Exception:** `DeviceNotFoundError` or `AudioError`

### Root Cause

Audio device indices can change between sessions. If `OUTPUT_DEVICE` is set to a specific index that no longer exists, playback will fail.

### Workaround

Leave `OUTPUT_DEVICE` unset (None) in `.env` to use the default device. If specifying a device, check available devices first:

```bash
python -c "import sounddevice as sd; print(sd.query_devices())"
```

### Diagnostic

Check logs for:

```
Default audio output: [<index>] <device_name> (sr=<rate>, ch=<channels>)
```

Or the error:

```
Could not determine default output device
```

---

## 8. Ollama Model Not Found / Connection Refused

**Severity:** High  
**Stage:** LLM  
**Symptom:** `LLMConnectionError` or model not found  
**Exception:** `LLMConnectionError`

### Root Cause

Ollama server is not running, or the specified model is not pulled.

### Fix

1. Start Ollama: `ollama serve`
2. Pull the model: `ollama pull qwen2.5:7b`
3. Verify: `ollama list`

### Diagnostic

```bash
curl -s http://localhost:11434/api/tags | python -m json.tool
```

Check `.env` matches:

```env
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=qwen2.5:7b
```

---

## 9. Empty Transcription from Whisper

**Severity:** Medium  
**Stage:** STT  
**Symptom:** `EmptyTranscriptionError` in logs, assistant doesn't respond  
**Exception:** `EmptyTranscriptionError`

### Root Cause

- Audio too quiet (low amplitude)
- VAD threshold too high (cutting off speech)
- Microphone not picking up audio
- Wrong language configuration (model expects Russian but receives silence)

### Workaround

1. Check microphone amplitude with `scripts/test_mic.py`
2. Lower `VAD_THRESHOLD` in `.env` (default 0.5, try 0.3)
3. Increase `VAD_MIN_SPEECH_DURATION_MS` if brief noises trigger VAD
4. Ensure `WHISPER_MODEL` supports Russian

### Diagnostic

Check logs for:

```
Audio captured: <duration>s, <samples> samples
Transcription: ''
```

If samples count is near 0, the microphone is not capturing audio.

---

## 10. TTS Returns None (Silence)

**Severity:** Medium  
**Stage:** TTS  
**Symptom:** Assistant prints text but does not speak; log shows `TTS returned None for response`  
**Exception:** None (graceful fallback to text)

### Root Cause

- Empty input text passed to `synthesize()`
- Silero model not loaded correctly (namespace conflict, see issue #1)
- Text contains characters Silero cannot synthesize
- GPU memory exhausted during TTS

### Diagnostic

Check logs for:

```
TTS: skipping empty text
TTS synthesis failed: ...
TTS returned None for non-empty text, falling back to text-only mode
```

Verify Silero loads correctly (see issue #1).

---

## Quick Reference: Exception → Stage Mapping

| Exception | Stage | Known Issue |
|-----------|-------|-------------|
| `DeviceNotFoundError` | Audio Input | #7 Audio device |
| `AudioError` | Audio I/O | #7 Audio device |
| `EmptyTranscriptionError` | STT | #9 Empty transcription |
| `STTError` | STT | #5 CUDA OOM |
| `LLMConnectionError` | LLM | #8 Ollama connection |
| `LLMTimeoutError` | LLM | #8 Ollama timeout |
| `LLMError` | LLM | #5 CUDA OOM, #8 |
| `TTSError` | TTS | #1 namespace, #2 speaker/voice, #3 sample rate, #4 omegaconf, #10 None output, #11 FileNotFoundError, #12 Unsupported language, #13 Hieroglyphs in text |
| `MemoryError` | Memory | #6 DB locked |

---

## 13. LLM Inserts Foreign Characters (Hieroglyphs) Breaking TTS

**Severity:** High  
**Stage:** TTS  
**Symptom:** Assistant response contains Chinese/Arabic/other non-Latin characters, TTS synthesis fails with `ValueError`, audio output is silent or incomplete  
**Exception:** `ValueError` from Silero TTS

### Root Cause

The LLM (qwen2.5:7b) is multilingual and sometimes "switches" to other languages mid-response, especially when:
- User asks for text in another language
- Model gets confused by context
- Response includes code snippets or technical terms with non-Russian characters

The Silero TTS v5_ru model only supports Russian + basic Latin characters. When it encounters hieroglyphs (Chinese, Arabic, etc.), it raises `ValueError` and synthesis fails.

### Fix (Implemented)

Two-layer protection:

**1. System prompt instruction** (`src/llm/prompt_builder.py`):
Added explicit instruction to respond ONLY in Russian:
```
- ВАЖНО: Отвечай ТОЛЬКО на русском языке. Никогда не используй другие языки
  (английский, китайский, немецкий и т.д.) в своих ответах, даже если пользователь
  просит текст на другом языке. Вместо этого объясни, что ты отвечаешь только на русском.
```

**2. Text cleaning before TTS** (`src/tts/silero_engine.py`):
Added `_clean_text_for_tts()` function that:
- Removes all characters outside Russian/Latin alphabet, digits, and basic punctuation
- Normalizes whitespace
- Logs when cleaning occurs
- Returns None if text becomes empty after cleaning

The regex pattern: `[^\u0400-\u04FFa-zA-Z0-9\s\.,!?;:\-\"'()]`

### Behavior

**Before fix:**
```
Assistant: Однажды львица встретила мышь... 我可以帮助你？你需要我做些什么？
TTS synthesis failed: ValueError
TTS returned None for response
No audio to play
```

**After fix:**
```
Assistant: Однажды львица встретила мышь... 我可以帮助你？你需要我做些什么？
TTS: cleaned unsupported characters from text (original=80 chars, cleaned=45 chars)
TTS: synthesizing text (45 chars): Однажды львица встретила мышь...
[Audio plays successfully]
```

### Diagnostic

Test the cleaning function:
```python
from src.tts.silero_engine import _clean_text_for_tts

text = "Привет我可以帮助你？你需要我做些什么？"
cleaned = _clean_text_for_tts(text)
print(f"Original: {text}")
print(f"Cleaned: {cleaned}")
# Output: "Привет"
```

### Limitations

- Cleaning removes ALL non-Russian/Latin characters, including emoji, special symbols, etc.
- If user explicitly asks for English text, LLM should refuse (per system prompt), but if it doesn't, TTS will clean it
- Code snippets with special characters may be partially cleaned

### Future Improvements

- Detect language before TTS and use appropriate model (v5_en for English, v5_ru for Russian)
- Add transliteration for common technical terms
- Better error messages showing which characters were removed

---

## 12. Silero TTS v5_ru Does Not Support English Text

**Severity:** Medium  
**Stage:** TTS  
**Symptom:** `ValueError` when synthesizing English text, TTS returns None, assistant speaks only Russian  
**Exception:** `TTSError` (logged as ValueError)

### Root Cause

The Silero TTS model `v5_ru` is Russian-only. It contains a limited symbol set (Russian letters + basic punctuation) and raises `ValueError` when encountering characters outside this set (e.g., English letters).

The model's `apply_tts()` method calls `process_simple_text()` which validates all characters against the supported symbol set. If any character is unsupported, it raises `ValueError` with no message.

### Workaround

The code now catches `ValueError` specifically and logs a clear error message:
```
TTS synthesis failed: text contains unsupported characters (likely non-Russian text with Russian model)
```

The assistant will fall back to text-only mode (display the response without speaking).

### Solutions

**Option 1: Use a multi-language model**  
Change `SILERO_SPEAKER` in `.env` to a multi-language model like `v5_multi` (if available) or `multi_v2`.

**Option 2: Translate before TTS**  
Add a translation step in the pipeline to convert English text to Russian before synthesis.

**Option 3: Use separate models for different languages**  
Load both `v5_ru` and `v5_en` models, detect language, and use the appropriate model.

### Diagnostic

Check if text contains unsupported characters:
```python
from src.core.config import Config
from src.tts.silero_engine import SileroTTSEngine

config = Config()
engine = SileroTTSEngine(config)
engine.load()

# Check supported symbols
print("Supported symbols:", engine._symbols)

# Test English text
result = engine._synthesize_sync("Hello world")
print("Result:", result)  # Will be None with error logged
```

### Current Status

The assistant will display English text but won't speak it. Russian text works normally.

---

## 11. Silero TTS Repo Missing from Torch Hub Cache (First Run)

**Severity:** High  
**Stage:** TTS  
**Symptom:** `FileNotFoundError: [Errno 2] No such file or directory: '.../snakers4_silero-models_master/src/__init__.py'` when loading TTS model  
**Exception:** `TTSError`

### Root Cause

The `SileroTTSEngine._load_model()` method assumes the Silero TTS repository (`snakers4/silero-models`) is already present in the torch.hub cache directory. On a fresh machine (or after cache is cleared), the repository has never been downloaded, so the directory `snakers4_silero-models_master/src/` does not exist. The workaround code for issue #1 tries to create `__init__.py` in that non-existent directory, causing `FileNotFoundError`.

Unlike the VAD engine (which calls `torch.hub.load()` and auto-downloads the repo), the TTS engine previously did not trigger the download before attempting to import from the cache.

### Fix (Implemented)

The `_load_model()` method now calls `_ensure_repo(repo_dir)` before the namespace conflict workaround. If the repository directory does not exist:
1. Download `https://github.com/snakers4/silero-models/archive/master.zip` via `torch.hub.download_url_to_file`
2. Extract the archive into the torch.hub cache directory
3. Rename the extracted folder (`silero-models-master`) to the expected name (`snakers4_silero-models_master`)
4. Proceed with the existing namespace conflict workaround

This ensures the repository is always present before attempting to create the shim `__init__.py`.

### Manual Workaround (if auto-download fails)

Run this command **from a directory that is NOT the project root** (to avoid the `src/` package shadowing during hubconf import):

```bash
cd C:\Users\YourUsername
python -c "import torch; torch.hub.load('snakers4/silero-models', 'silero_tts', language='ru', speaker='v5_ru', trust_repo=True)"
```

This downloads the repository and model weights into the torch.hub cache. Subsequent runs will use the cached version.

### Diagnostic

Check if the repository exists in the torch hub cache:

```bash
python -c "import torch, os; repo_dir = os.path.join(torch.hub.get_dir(), 'snakers4_silero-models_master'); print(f'Repo exists: {os.path.isdir(repo_dir)}')"
```

If `False`, the auto-download will trigger on next TTS load (requires internet connection).