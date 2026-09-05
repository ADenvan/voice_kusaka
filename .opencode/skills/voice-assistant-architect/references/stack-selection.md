# Stack Selection

## Decision Criteria

Each technology choice is evaluated against:

| Criterion | Weight | Description |
|-----------|--------|-------------|
| Russian language support | HIGH | Must handle Russian text and audio well |
| Python 3.13 compatibility | HIGH | Must install and run without patches |
| Latency | MEDIUM | Lower is better for real-time interaction |
| Installation complexity | MEDIUM | Simple pip install preferred over compiling C extensions |
| GPU requirements | MEDIUM | Should work with consumer GPU (6-8 GB VRAM) |
| Community / maintenance | LOW | Active development and documentation |

---

## STT: Speech-to-Text

| Option | Russian | Py 3.13 | Latency | Install | GPU | Verdict |
|--------|---------|---------|---------|---------|-----|---------|
| **faster-whisper** | Excellent (large-v3) | Yes | Low (CTranslate2) | Simple pip | 1-3 GB | **CHOSEN** |
| openai-whisper | Good | Yes | High (PyTorch only) | Simple pip | 3-5 GB | Rejected: slow |
| OpenAI Whisper API | Excellent | Yes | Network-dependent | Simple pip | None | Rejected: needs network, paid |
| Vosk | Good | Uncertain | Very low | Complex (native) | None | Rejected: worse Russian, install issues |

**Rationale**: `faster-whisper` uses CTranslate2 for 4x faster inference than vanilla Whisper,
with the same model quality. `large-v3` provides excellent Russian recognition.
`int8_float16` compute type balances speed and accuracy on consumer GPUs.

---

## TTS: Text-to-Speech

| Option | Russian | Py 3.13 | Latency | Install | GPU | Quality | Verdict |
|--------|---------|---------|---------|---------|-----|---------|---------|
| **Silero TTS** | Native (ru) | Yes | ~100ms | Simple pip | ~100 MB | Good | **CHOSEN** |
| WhisperSpeech | Good | Uncertain | Slow | Complex | 2-4 GB | Excellent | Rejected: heavy, complex install |
| OpenAI TTS API | Excellent | Yes | Network-dependent | Simple pip | None | Excellent | Rejected: needs network, paid |
| pyttsx3 | Limited | Yes | Very low | Simple pip | None | Poor | Rejected: robotic quality |
| kokoro | No Russian | No (<3.12) | — | — | — | — | Rejected: no Russian, incompatible |

**Rationale**: Silero TTS is purpose-built for Russian, lightweight (~100 MB),
fast, and produces natural-sounding speech. The `baya` speaker provides
a pleasant female voice. 48kHz output is high quality.

---

## LLM: Large Language Model

| Option | Russian | Latency | Privacy | Cost | Verdict |
|--------|---------|---------|---------|------|---------|
| **Ollama (local)** | Good (model-dependent) | Low (local GPU) | Full | Free | **CHOSEN** |
| OpenAI API | Excellent | Network-dependent | None | Paid | Fallback option |
| llama.cpp direct | Good | Low | Full | Free | Rejected: Ollama wraps this better |

**Rationale**: Ollama provides the best balance for a local, private, single-user
assistant. It manages models, provides a clean API, supports streaming,
and works well with Russian when using appropriate models (qwen2.5, saiga).
No data leaves the machine.

See {file:skills/voice-assistant-architect/references/ollama-integration.md} for model selection details.

---

## Audio I/O

| Option | Py 3.13 | Latency | Install | Features | Verdict |
|--------|---------|---------|---------|----------|---------|
| **sounddevice** | Yes | Low | Simple pip (bundles PortAudio) | Full duplex | **CHOSEN** |
| pyaudio | Often breaks | Low | Complex C compilation | Full duplex | Rejected: install issues on 3.13/Windows |
| pyttsx3 | Yes | N/A | Simple | Output only | Rejected: no capture |

**Rationale**: `sounddevice` bundles PortAudio, installs cleanly on Windows
without compilation. Supports full-duplex (record + play simultaneously),
low-latency callback mode, and works with numpy arrays directly.

---

## Web Framework

| Option | Async | WebSocket | Docs | Performance | Verdict |
|--------|-------|-----------|------|-------------|---------|
| **FastAPI** | Native | Native | Excellent | High | **CHOSEN** |
| Flask | No (WSGI) | Add-on | Good | Lower | Rejected: no native async |

**Rationale**: FastAPI is async-native — essential for streaming audio and LLM tokens
over WebSocket. Automatic OpenAPI docs, Pydantic validation, and uvicorn
provide production-ready HTTP + WS server with minimal code.

---

## CLI Framework

| Option | Async | Decorators | Docs | Type hints | Verdict |
|--------|-------|------------|------|------------|---------|
| **Typer** | Via anyio | Clean | Excellent | Full | **CHOSEN** |
| Click | No | Verbose | Good | Partial | Rejected: more boilerplate |
| argparse | Yes (stdlib) | None | Standard | Manual | Rejected: too low-level |

**Rationale**: Typer provides the cleanest CLI with minimal code, automatic help,
type-annotated parameters, and shell completion. Built on Click but with
modern Python typing.

---

## Memory / Storage

| Option | Async | Query | Install | Scale | Verdict |
|--------|-------|-------|---------|-------|---------|
| **SQLite + aiosqlite** | Yes | SQL | Stdlib | 1 user | **CHOSEN** |
| JSON files | Via aiofiles | None | None | Fragile | Rejected: no query, corruption risk |
| PostgreSQL | Yes (asyncpg) | SQL | External DB | Multi-user | Rejected: overkill |

**Rationale**: SQLite is zero-config, ships with Python, handles concurrent reads
via WAL mode, and `aiosqlite` provides async access. Perfect for a single-user
local assistant. Easy to inspect with any SQLite browser.

---

## Dependencies Summary (MVP)

```txt
# requirements.txt
fastapi>=0.115.12,<1
uvicorn>=0.34.0
pydantic>=2.10.6
pydantic-settings>=2.0
python-dotenv>=1.0.0

# LLM
httpx>=0.27,<0.29

# STT
faster-whisper>=1.0.0
ctranslate2>=4.0.0

# TTS
torch>=2.4.1
torchaudio>=2.4.1

# Audio I/O
sounddevice>=0.5.0
soundfile>=0.13.1
numpy>=1.24.4
scipy>=1.9.3

# Memory
aiosqlite>=0.20.0

# CLI
typer>=0.12.0

# Utilities
requests>=2.31.0
tqdm>4
colorama>=0.4.6
```

### What's Excluded (from original requirements.txt)

| Package | Reason |
|---------|--------|
| flask | FastAPI chosen — one framework only |
| ollama (SDK) | httpx + Ollama REST API is lighter, no extra dependency |
| together | Not needed — Ollama is local |
| pyaudio | Replaced by sounddevice |
| librosa | scipy + soundfile cover MVP needs |
| celery | No task queues needed for 1 user |
| selenium + stealth stack | Not core to voice assistant |
| pydantic_core, certifi, anyio, sniffio, jiter, distro, setuptools | Transitive — auto-installed |
| ipython | Dev dependency → requirements-dev.txt |
| colorama + termcolor | One is enough — keep colorama |
| kokoro | Incompatible with Python 3.13 |
| text2emotion, langid, adaptive-classifier, sacremoses | Phase 4+ |

### requirements-dev.txt

```txt
ipython>=8.13.0
pytest>=8.0
pytest-asyncio>=0.23
pytest-cov>=5.0
ruff>=0.4
mypy>=1.10
```
