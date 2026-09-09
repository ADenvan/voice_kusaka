# Voice AI — Local Russian Voice Assistant

Full pipeline: **Microphone -> VAD -> STT -> LLM -> TTS -> Speakers**

Runs entirely locally — Ollama, Whisper, Silero without cloud APIs.

## Architecture

```
Mic (16kHz) -> [Silero VAD] -> [faster-whisper STT] -> Text
  -> [Ollama LLM, streaming] -> Response
  -> [Silero TTS v5] -> Audio -> [sounddevice] -> Speakers
```

| Component | Technology | Model |
|-----------|-----------|--------|
| VAD | Silero | silero-vad (512 windows) |
| STT | faster-whisper | large-v3, CUDA |
| LLM | Ollama | qwen2.5:7b |
| TTS | Silero | v5_ru, voice=baya, 48kHz |
| Memory | SQLite (aiosqlite) | — |

## Setup

### 1. Install PyTorch (CUDA 12.4)
```bash
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu124
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

### 3. Start Ollama
```bash
ollama serve
ollama pull qwen2.5:7b
ollama pull gpt-oss:20b
```

### 4. Configure audio output device
```bash
python -c "import sounddevice as sd; print(sd.query_devices())"
```
Найдите свой индекс наушников/динамиков и установите его. `.env`:
  - Device [18] - VG248 (NVIDIA High Definition Audio), Windows WASAPI (0 in, 2 out)
```
OUTPUT_DEVICE=18 #
```

### 5. Run
```bash
python -m src.cli.app run
python -m src.cli.app run --log-level DEBUG
python -m src.cli.app run --mode button     # Enter для активации
python -m src.cli.app run --mode wake_word  # Активация по фразе "войс ай"
python -m src.cli.app run --mode continuous # Реагировать на любую речь

python -m src.cli.app run --lang en # Английский
```

### Text mode (no microphone)
```bash
python -m src.cli.app chat
```

### Diagnostics
```bash
python scripts/test_mic.py
python scripts/test_audio_output.py
python scripts/test_tts.py
```

### Tests
```bash
pytest tests/ -v -k "not test_models_command"
```

## Configuration

Copy `.env.example` to `.env`:

| Variable | Default | Description |
|-----------|-------------|----------|
| `WHISPER_MODEL` | large-v3 | Whisper model |
| `WHISPER_DEVICE` | cuda | Device (cuda/cpu) |
| `OLLAMA_MODEL` | qwen2.5:7b | LLM model |
| `SILERO_SPEAKER` | v5_ru | TTS model name |
| `SILERO_VOICE` | baya | TTS voice |
| `SILERO_SAMPLE_RATE` | 48000 | TTS sample rate |
| `OUTPUT_DEVICE` | None | Sounddevice output device index (None = system default) |

Full list in `.env.example`.

## Project Structure

```
src/
├── core/          config, pipeline, protocols, exceptions
├── audio/         input (mic), output (speakers + device select), vad
├── stt/           faster-whisper engine
├── llm/           ollama client, prompt builder
├── tts/           silero TTS engine
├── memory/        SQLite store, context manager
└── cli/           Typer CLI (run, chat, models, show-config)
scripts/
├── test_mic.py            Mic + VAD diagnostics
├── test_audio_output.py   Output devices + playback test
└── test_tts.py            TTS synthesis + playback test
```

## Known Quirks

- **Silero TTS `src/` conflict** — project's `src/` package shadows Silero import. Workaround: temporary `__init__.py` + `sys.modules` manipulation in `silero_engine.py`.
- **Silero two-level naming** — `SILERO_SPEAKER` (model, e.g. `v5_ru`) != `SILERO_VOICE` (voice, e.g. `baya`).
- **Audio output device** — Windows may default to HDMI monitor. Set `OUTPUT_DEVICE` in `.env` to route audio to headset.
- **Preload time** — ~24s until ready (VAD + STT + TTS model loading).
- **First TTS run downloads Silero repo** — on first run (or after cache clear), the TTS engine auto-downloads the Silero models repository (~30 MB) into the torch hub cache. Requires internet. Subsequent runs use the cached version.
- **Russian-only TTS** — the `v5_ru` model only supports Russian text. English text will be displayed but not spoken. Use a multi-language model or add translation for English speech.
- **Hieroglyphs in LLM responses** — qwen2.5:7b may occasionally insert Chinese/Arabic characters. System prompt instructs LLM to respond only in Russian, and TTS automatically cleans unsupported characters before synthesis.

## Requirements

- Windows 10/11 with microphone and speakers
- NVIDIA GPU 8+ GB VRAM (large-v3 ~3GB + qwen2.5:7b ~5GB)
- Python 3.13
- CUDA 12.x
- Ollama

## Roadmap

| Phase | Status |
|-------|--------|
| Phase 1: MVP (Enter -> voice -> STT -> LLM -> TTS -> speaker) | Done |
| Phase 2: Wake word + continuous listening | Done |
| Phase 3: Emotions, language, classification | TODO |