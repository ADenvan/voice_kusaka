# Debug Commands Reference

Bash commands and diagnostic procedures for troubleshooting each stage of the voice_ai pipeline.

## Environment Checks

### CUDA Availability

```bash
python -c "import torch; print(f'CUDA available: {torch.cuda.is_available()}'); print(f'Device: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else \"N/A\"}')"
```

### GPU Memory

```bash
python -c "import torch; print(f'GPU memory: {torch.cuda.mem_get_info()[0] / 1024**3:.1f} GB free / {torch.cuda.mem_get_info()[1] / 1024**3:.1f} GB total') if torch.cuda.is_available() else print('No CUDA')"
```

### Audio Devices

```bash
python -c "import sounddevice as sd; devices = sd.query_devices(); print(devices)"
```

### Ollama Status

```bash
curl -s http://localhost:11434/api/tags
```

If `Connection refused`, start Ollama:

```bash
ollama serve
```

Check model availability:

```bash
ollama list
```

Pull a model if missing:

```bash
ollama pull qwen2.5:7b
```

### Python Dependencies

```bash
python -c "import faster_whisper; print(f'faster-whisper: {faster_whisper.__version__}')"
python -c "import torch; print(f'torch: {torch.__version__}')"
python -c "import sounddevice; print(f'sounddevice: {sounddevice.__portaudio_version__}')"
python -c "import omegaconf; print(f'omegaconf: {omegaconf.__version__}')"
python -c "import aiosqlite; print(f'aiosqlite: {aiosqlite.__version__}')"
```

### .env Configuration

```bash
python -c "from src.core.config import Config; c = Config(); print(f'sample_rate={c.sample_rate} whisper_model={c.whisper_model} whisper_device={c.whisper_device} ollama_model={c.ollama_model} ollama_base_url={c.ollama_base_url} silero_speaker={c.silero_speaker} silero_voice={c.silero_voice} silero_sample_rate={c.silero_sample_rate} log_level={c.log_level}')"
```

## Pipeline Stage Tests

### Audio Input Test

```bash
pytest tests/test_audio.py -v -k "input or mic"
```

Quick mic capture test:

```bash
python -c "import sounddevice as sd; import numpy as np; print('Recording 2s...'); data = sd.rec(int(16000 * 2), samplerate=16000, channels=1, dtype='int16'); sd.wait(); print(f'Captured {len(data)} samples, max amplitude={np.max(np.abs(data))}')"
```

### VAD Test

```bash
pytest tests/test_audio.py -v -k "vad"
```

### STT Test

```bash
pytest tests/test_stt.py -v
```

Quick transcription test (requires model loaded):

```bash
python -c "from src.stt.whisper_engine import FasterWhisperEngine; from src.core.config import Config; e = FasterWhisperEngine(Config()); e.load(); print('Model loaded')"
```

### LLM Test

```bash
pytest tests/test_llm.py -v
```

Quick Ollama connectivity test:

```bash
python -c "import httpx; r = httpx.get('http://localhost:11434/api/tags'); print(f'Status: {r.status_code}'); print(r.json().get('models', []))"
```

### TTS Test

```bash
pytest tests/test_tts.py -v
```

Quick synthesis test:

```bash
python -c "from src.tts.silero_engine import SileroTTSEngine; from src.core.config import Config; e = SileroTTSEngine(Config()); e.load(); audio = e.synthesize('Привет'); print(f'Result: {type(audio)} shape={getattr(audio, \"shape\", None)}')"
```

### Memory / Database Test

```bash
pytest tests/test_memory.py -v
```

SQLite integrity check:

```bash
python -c "import sqlite3; conn = sqlite3.connect('data/voice_ai.db'); print(conn.execute('PRAGMA integrity_check').fetchone()); conn.close()"
```

### Pipeline Integration Test

```bash
pytest tests/test_pipeline.py -v
```

### Full Test Suite

```bash
pytest tests/ -v --tb=short
```

Run with coverage:

```bash
pytest tests/ -v --cov=src --cov-report=term-missing
```

## Log Analysis

### View Pipeline Logs

If running with `LOG_LEVEL=DEBUG`:

```bash
# Run pipeline with verbose logging
python -m src.cli.app run --log-level DEBUG
```

### Search for Specific Errors

Search logs in terminal output for error patterns:

- STT errors: `voice_ai.stt`
- LLM errors: `voice_ai.llm`
- TTS errors: `voice_ai.tts`
- Audio errors: `voice_ai.audio`
- Pipeline errors: `voice_ai.pipeline`

### Logger Names by Stage

| Stage | Logger Name |
|-------|-------------|
| Audio Input | `voice_ai.audio.input` |
| Audio Output | `voice_ai.audio.output` |
| VAD | `voice_ai.audio.vad` |
| STT | `voice_ai.stt` |
| LLM | `voice_ai.llm` |
| TTS | `voice_ai.tts` |
| Pipeline | `voice_ai.pipeline` |

## Diagnostic Scripts

### Microphone Check

Use the existing diagnostic script:

```bash
python scripts/test_mic.py
```

### Full Environment Report

```bash
python -c "
import sys
print(f'Python: {sys.version}')
try:
    import torch
    print(f'torch: {torch.__version__}, CUDA: {torch.cuda.is_available()}')
except ImportError:
    print('torch: NOT INSTALLED')
try:
    import faster_whisper
    print(f'faster-whisper: {faster_whisper.__version__}')
except ImportError:
    print('faster-whisper: NOT INSTALLED')
try:
    import sounddevice as sd
    print(f'sounddevice: {sd.__portaudio_version__}')
    devs = sd.query_devices()
    print(f'Audio devices: {len(devs)}')
except ImportError:
    print('sounddevice: NOT INSTALLED')
try:
    import httpx
    r = httpx.get('http://localhost:11434/api/tags', timeout=3)
    print(f'Ollama: status={r.status_code}')
except Exception as e:
    print(f'Ollama: UNREACHABLE ({e})')
try:
    import sqlite3
    conn = sqlite3.connect('data/voice_ai.db')
    print(f'SQLite: OK, integrity={conn.execute(\"PRAGMA integrity_check\").fetchone()[0]}')
    conn.close()
except Exception as e:
    print(f'SQLite: ERROR ({e})')
"
```