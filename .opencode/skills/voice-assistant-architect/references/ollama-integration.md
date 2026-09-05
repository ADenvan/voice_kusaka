# Ollama Integration

## Installation (Windows)

1. Download from https://ollama.com/download
2. Install and verify:
   ```
   ollama --version
   ```
3. Ollama runs as a background service on `http://localhost:11434`

---

## Model Selection for Russian

### Recommended Models

| Model | Size | VRAM | Russian Quality | Speed | Recommendation |
|-------|------|------|-----------------|-------|----------------|
| **qwen2.5:7b** | 4.7 GB | ~6 GB | Good | Fast | **Best for voice** — fast, good Russian |
| saiga_llama3:8b | 4.9 GB | ~7 GB | Excellent | Medium | Best Russian, slower |
| mistral:7b | 4.1 GB | ~6 GB | Fair | Fast | OK Russian, very fast |
| gemma3:4b | 3.3 GB | ~5 GB | Fair | Very fast | Lightweight option |
| qwen2.5:14b | 9 GB | ~12 GB | Very good | Slow | If you have VRAM |

### Model Pull Commands

```bash
# Recommended for voice assistant
ollama pull qwen2.5:7b

# Best Russian quality
ollama pull saiga/llama3:8b

# Lightweight fallback
ollama pull gemma3:4b
```

### Why qwen2.5:7b as Default

- **Russian**: Good comprehension and generation, handles Russian well
- **Speed**: 7B generates ~30-50 tokens/s on RTX 3060/4060 — fast enough for voice
- **Size**: ~5 GB VRAM, leaves room for Whisper + Silero
- **Context**: Supports 32K context window (configurable via `num_ctx`)
- **Streaming**: Works perfectly with Ollama's streaming API

---

## API Reference

### Chat Endpoint (Primary)

```
POST http://localhost:11434/api/chat
```

**Request:**
```json
{
  "model": "qwen2.5:7b",
  "messages": [
    {"role": "system", "content": "Ты голосовой ассистент..."},
    {"role": "user", "content": "Какая погода сегодня?"}
  ],
  "stream": true,
  "options": {
    "temperature": 0.7,
    "num_predict": 256,
    "num_ctx": 4096
  }
}
```

**Streaming Response** (NDJSON, one JSON object per line):
```json
{"model":"qwen2.5:7b","created_at":"...","message":{"role":"assistant","content":"Сегодня"},"done":false}
{"model":"qwen2.5:7b","created_at":"...","message":{"role":"assistant","content":" солнечно"},"done":false}
{"model":"qwen2.5:7b","created_at":"...","message":{"role":"assistant","content":""},"done":true}
```

### Non-Streaming Chat

Set `"stream": false` — returns single JSON with full response.

### Generate Endpoint (Alternative)

```
POST http://localhost:11434/api/generate
```

Simpler: takes `prompt` string instead of `messages` array.
Less control over context. **Prefer `/api/chat`** for multi-turn dialog.

### OpenAI-Compatible Endpoint

```
POST http://localhost:11434/v1/chat/completions
```

Ollama exposes an OpenAI-compatible API. Useful if you want to swap
between Ollama and OpenAI without changing client code.

---

## Client Implementation

### OllamaClient (llm/ollama_client.py)

```python
import asyncio
import json
from collections.abc import AsyncIterator

import httpx

from src.core.config import Config
from src.core.exceptions import LLMConnectionError, LLMTimeoutError


class OllamaClient:
    def __init__(self, config: Config) -> None:
        self.base_url = config.ollama_base_url
        self.model = config.ollama_model
        self.timeout = config.ollama_timeout
        self.temperature = config.ollama_temperature
        self.num_ctx = config.ollama_num_ctx

    async def chat_stream(self, messages: list[dict]) -> AsyncIterator[str]:
        """Stream chat tokens from Ollama."""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                async with client.stream(
                    "POST",
                    f"{self.base_url}/api/chat",
                    json={
                        "model": self.model,
                        "messages": messages,
                        "stream": True,
                        "options": {
                            "temperature": self.temperature,
                            "num_ctx": self.num_ctx,
                        },
                    },
                ) as response:
                    response.raise_for_status()
                    async for line in response.aiter_lines():
                        if not line.strip():
                            continue
                        chunk = json.loads(line)
                        content = chunk.get("message", {}).get("content", "")
                        if content:
                            yield content
                        if chunk.get("done", False):
                            return
        except httpx.ConnectError as e:
            raise LLMConnectionError(f"Cannot reach Ollama at {self.base_url}") from e
        except httpx.TimeoutException as e:
            raise LLMTimeoutError(f"Ollama timed out after {self.timeout}s") from e

    async def chat(self, messages: list[dict]) -> str:
        """Non-streaming chat — returns full response."""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/api/chat",
                    json={
                        "model": self.model,
                        "messages": messages,
                        "stream": False,
                        "options": {
                            "temperature": self.temperature,
                            "num_ctx": self.num_ctx,
                        },
                    },
                )
                response.raise_for_status()
                data = response.json()
                return data.get("message", {}).get("content", "")
        except httpx.ConnectError as e:
            raise LLMConnectionError(f"Cannot reach Ollama at {self.base_url}") from e
        except httpx.TimeoutException as e:
            raise LLMTimeoutError(f"Ollama timed out after {self.timeout}s") from e

    async def is_available(self) -> bool:
        """Check if Ollama service is running."""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.base_url}/api/tags")
                return response.status_code == 200
        except (httpx.ConnectError, httpx.TimeoutException):
            return False

    async def list_models(self) -> list[str]:
        """List available Ollama models."""
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{self.base_url}/api/tags")
            response.raise_for_status()
            data = response.json()
            return [m["name"] for m in data.get("models", [])]
```

---

## System Prompt for Russian Voice Assistant

### Prompt Builder (llm/prompt_builder.py)

```python
SYSTEM_PROMPT = """\
Ты — голосовой ассистент voice_ai. Ты разговариваешь с пользователем на русском языке.

Правила:
- Отвечай кратко и по делу. Твои ответы будут озвучиваться, поэтому избегай длинных абзацев.
- Используй простой, разговорный русский язык.
- Не используй markdown, списки с буллетами или форматирование — только чистый текст.
- Если не знаешь ответ, честно скажи об этом.
- Отвечай в одном-двух предложениях, если вопрос простой.
- Для сложных вопросов давай структурированный, но устный ответ.
"""

class PromptBuilder:
    @staticmethod
    def build_messages(
        history: list[dict],
        system_prompt: str = SYSTEM_PROMPT,
    ) -> list[dict]:
        messages = [{"role": "system", "content": system_prompt}]
        for msg in history:
            messages.append({
                "role": msg["role"],
                "content": msg["content"],
            })
        return messages
```

### Why These Rules

- **Brief responses**: TTS sounds unnatural with long paragraphs; short = better audio
- **No markdown**: Bullet points and headers are read aloud awkwardly by TTS
- **Conversational tone**: Voice assistant should sound natural, not encyclopedic
- **Russian only**: Consistent language prevents model from switching mid-sentence

---

## Generation Parameters

| Parameter | Default | Range | Effect |
|-----------|---------|-------|--------|
| `temperature` | 0.7 | 0.1-1.0 | Higher = more creative, lower = more deterministic |
| `num_predict` | 256 | 64-1024 | Max tokens to generate. 256 ≈ 1-2 min of speech |
| `num_ctx` | 4096 | 2048-32768 | Context window. 4096 ≈ 6K chars of history |
| `top_k` | 40 | 1-100 | Top-K sampling (Ollama default is fine) |
| `top_p` | 0.9 | 0.0-1.0 | Nucleus sampling (Ollama default is fine) |

### Tuning for Voice

- **`num_predict: 256`** — prevents runaway generation. 256 tokens ≈ 30-60 seconds of speech.
  Most voice answers should be much shorter.
- **`temperature: 0.7`** — slightly creative but stays on topic.
  Lower (0.3) for factual Q&A, higher (0.9) for creative tasks.
- **`num_ctx: 4096`** — balances memory (larger = more VRAM) and context.
  Increase to 8192 if conversations are long.

---

## Context Management

### Message History Window

Keep the last N messages in the context window to avoid exceeding `num_ctx`:

```python
class ContextManager:
    def __init__(self, max_messages: int = 50):
        self.max_messages = max_messages

    def trim_history(self, messages: list[dict]) -> list[dict]:
        """Keep system prompt + last N messages."""
        if len(messages) <= self.max_messages + 1:
            return messages

        system = messages[0] if messages[0]["role"] == "system" else None
        rest = messages[1:] if system else messages

        trimmed = rest[-self.max_messages:]
        return [system] + trimmed if system else trimmed
```

### Token Counting Estimation

```python
def estimate_tokens(text: str) -> int:
    """Rough estimate: 1 token ≈ 4 chars for Russian."""
    return len(text) // 3  # Russian is ~3 chars/token (worse than English ~4)
```

Use this to check if context will fit before sending to Ollama.

---

## Error Handling

| Error | Detection | Recovery |
|-------|-----------|----------|
| Ollama not running | `ConnectError` | Show message: "Запустите Ollama: ollama serve" |
| Model not found | 404 response | Suggest: "Скачайте модель: ollama pull qwen2.5:7b" |
| Generation timeout | `TimeoutException` | Return partial response + apology |
| Ollama crashed mid-stream | Connection reset | Log error, return what was collected |
| VRAM OOM | Ollama error response | Suggest smaller model or reduce `num_ctx` |

### Startup Health Check

```python
async def check_ollama_health(config: Config) -> None:
    """Run at startup. Fail fast with actionable message."""
    client = OllamaClient(config)
    if not await client.is_available():
        raise LLMConnectionError(
            "Ollama не запущен. Запустите: ollama serve"
        )
    models = await client.list_models()
    if config.ollama_model not in models:
        raise LLMConnectionError(
            f"Модель '{config.ollama_model}' не установлена. "
            f"Скачайте: ollama pull {config.ollama_model}"
        )
```

---

## Ollama CLI Reference

```bash
# List installed models
ollama list

# Pull a model
ollama pull qwen2.5:7b

# Delete a model
ollama rm qwen2.5:7b

# Run model interactively (for testing)
ollama run qwen2.5:7b

# Show model info
ollama show qwen2.5:7b

# Start Ollama server (usually auto-starts)
ollama serve
```

---

## Performance Tips

1. **Keep model loaded**: Ollama keeps the model in VRAM after first inference.
   Subsequent calls are fast. Don't unload between turns.

2. **`num_predict` limit**: Set low (128-256) for voice — prevents long rambling responses
   that waste generation time and sound bad via TTS.

3. **Quantization**: Ollama models are already quantized (Q4_K_M by default).
   This is fine for voice assistant quality.

4. **GPU selection**: If you have multiple GPUs, set:
   ```env
   CUDA_VISIBLE_DEVICES=0
   ```

5. **Context reuse**: Ollama caches the KV-cache for the same conversation.
   Sending the same prefix (system + history) enables fast prefix processing
   on subsequent turns.
