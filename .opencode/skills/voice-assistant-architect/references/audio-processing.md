# Audio Processing

## Audio Format Standard

All internal audio in voice_ai uses **PCM float32 numpy arrays**:

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| Sample rate (STT) | 16000 Hz | Whisper requires 16kHz |
| Sample rate (TTS) | 48000 Hz | Silero native output rate |
| Channels | 1 (mono) | Voice only, no stereo needed |
| Dtype | float32 | numpy standard, sounddevice compatible |
| Range | [-1.0, 1.0] | Normalized PCM |

### Resampling

When Silero outputs 48kHz but playback device expects 16kHz (or vice versa):

```python
from scipy.signal import resample

def resample_audio(audio: np.ndarray, orig_rate: int, target_rate: int) -> np.ndarray:
    if orig_rate == target_rate:
        return audio
    num_samples = int(len(audio) * target_rate / orig_rate)
    return resample(audio, num_samples).astype(np.float32)
```

For STT: resample 48kHz → 16kHz (faster-whisper handles this internally).
For playback: keep Silero's native 48kHz for quality.

---

## Microphone Capture (sounddevice)

### Callback Mode (Continuous)

```python
import sounddevice as sd
import numpy as np

class SoundDeviceInput:
    def __init__(self, config: Config):
        self.sample_rate = config.sample_rate  # 16000
        self.chunk_duration_ms = config.chunk_duration_ms  # 500
        self.chunk_size = int(self.sample_rate * self.chunk_duration_ms / 1000)
        self._queue: asyncio.Queue[np.ndarray] = asyncio.Queue(maxsize=20)
        self._stream: sd.InputStream | None = None

    async def start(self) -> None:
        loop = asyncio.get_event_loop()
        self._stream = sd.InputStream(
            samplerate=self.sample_rate,
            channels=1,
            dtype="float32",
            blocksize=self.chunk_size,
            callback=lambda indata, frames, time, status: loop.call_soon_threadsafe(
                self._queue.put_nowait, indata[:, 0].copy()
            ),
        )
        self._stream.start()

    async def read_chunk(self) -> np.ndarray:
        return await self._queue.get()

    async def stop(self) -> None:
        if self._stream:
            self._stream.stop()
            self._stream.close()
```

### Block Mode (Button-press recording)

```python
async def record_utterance(self, max_duration_s: float = 10.0) -> np.ndarray:
    """Record until silence detected or max duration reached."""
    chunks: list[np.ndarray] = []
    silence_chunks = 0
    max_silence = int(1.5 / (self.chunk_duration_ms / 1000))  # 1.5s silence

    await self.start()
    try:
        for _ in range(int(max_duration_s / (self.chunk_duration_ms / 1000))):
            chunk = await self.read_chunk()
            chunks.append(chunk)
            if self._is_silence(chunk):
                silence_chunks += 1
            else:
                silence_chunks = 0
            if silence_chunks >= max_silence:
                break
    finally:
        await self.stop()

    return np.concatenate(chunks) if chunks else np.array([], dtype=np.float32)
```

---

## Speaker Playback (sounddevice)

```python
class SoundDeviceOutput:
    def __init__(self, config: Config):
        self._interrupt = False

    async def play(self, audio: np.ndarray, sample_rate: int = 48000) -> None:
        self._interrupt = False
        chunk_size = int(sample_rate * 0.1)  # 100ms chunks for interrupt responsiveness

        for i in range(0, len(audio), chunk_size):
            if self._interrupt:
                break
            chunk = audio[i:i + chunk_size]
            sd.play(chunk, samplerate=sample_rate, blocking=True)

    def interrupt(self) -> None:
        self._interrupt = True
        sd.stop()

    async def stop(self) -> None:
        sd.stop()
```

---

## Voice Activity Detection (VAD)

### Option 1: Silero VAD (Recommended)

```python
class SileroVAD:
    def __init__(self, config: Config):
        self.model, utils = torch.hub.load(
            repo_or_dir="snakers4/silero-vad",
            model="silero_vad",
            trust_repo=True,
        )
        self.threshold = config.vad_threshold  # 0.5
        self.sample_rate = 16000

    def is_speech(self, chunk: np.ndarray) -> bool:
        tensor = torch.from_numpy(chunk).float()
        prob = self.model(tensor, self.sample_rate).item()
        return prob >= self.threshold

    def get_speech_prob(self, chunk: np.ndarray) -> float:
        tensor = torch.from_numpy(chunk).float()
        return self.model(tensor, self.sample_rate).item()
```

### Option 2: Energy-based (Fallback, no GPU)

```python
class EnergyVAD:
    def __init__(self, config: Config):
        self.threshold = 0.01  # RMS threshold, tune empirically

    def is_speech(self, chunk: np.ndarray) -> bool:
        rms = np.sqrt(np.mean(chunk ** 2))
        return rms >= self.threshold
```

### VAD Integration Pattern

```python
async def record_until_silence(
    self,
    initial_timeout_s: float = 5.0,
    silence_timeout_s: float = 1.5,
) -> np.ndarray:
    """Record from mic, start on speech, stop on silence."""
    chunks: list[np.ndarray] = []
    speech_started = False
    silence_count = 0
    max_silence_chunks = int(silence_timeout_s / (self.chunk_ms / 1000))

    start_time = asyncio.get_event_loop().time()
    timeout_chunks = int(initial_timeout_s / (self.chunk_ms / 1000))

    for i in range(timeout_chunks * 3):  # 3x buffer
        chunk = await self.audio_in.read_chunk()
        is_speech = self.vad.is_speech(chunk)

        if not speech_started:
            if is_speech:
                speech_started = True
                chunks.append(chunk)
            continue

        chunks.append(chunk)
        if is_speech:
            silence_count = 0
        else:
            silence_count += 1

        if silence_count >= max_silence_chunks:
            break

    return np.concatenate(chunks) if chunks else np.array([], dtype=np.float32)
```

---

## Wake Word Detection ("voice_ai")

### Phase 2 Feature — Not for MVP

Three implementation approaches, ordered by recommendation:

### Option 1: STT-based keyword detection (Simplest)

```python
class STTWakeWord:
    WAKE_PHRASES = ["войс ай", "voice ai", "войс айай", "войсай"]

    def __init__(self, config: Config):
        self.stt = FasterWhisperEngine(config)  # Reuse main STT with small model
        self.wake_model_size = "tiny" or "base"  # Fast, low VRAM
        self._wake_stt = self._init_wake_stt()

    def _init_wake_stt(self):
        from faster_whisper import WhisperModel
        return WhisperModel("tiny", device="cuda", compute_type="int8")

    async def detect(self, audio_chunk: np.ndarray) -> bool:
        segments, _ = self._wake_stt.transcribe(audio_chunk, language="ru")
        text = " ".join(s.text for s in segments).lower().strip()
        return any(phrase in text for phrase in self.WAKE_PHRASES)
```

**Pros**: Reuses existing stack, no new dependencies.
**Cons**: Higher latency (~300ms), higher GPU usage (constant inference).

### Option 2: OpenWakeWord (Dedicated lightweight model)

```python
class OpenWakeWordDetector:
    def __init__(self):
        from openwakeword import Model
        self.model = Model()
        # Train custom model for "voice_ai" using synthetic data
        # or use pre-trained and map to keyword

    async def detect(self, audio_chunk: np.ndarray) -> bool:
        prediction = self.model.predict(audio_chunk)
        return prediction.get("voice_ai", 0) > 0.5
```

**Pros**: Very low latency (~50ms), low GPU/CPU, custom keyword.
**Cons**: Requires training custom model, additional dependency.

### Option 3: Porcupine (Commercial, high accuracy)

```python
class PorcupineWakeWord:
    def __init__(self, access_key: str):
        import pvporcupine
        self.porcupine = pvporcupine.create(
            access_key=access_key,
            keyword_paths=["voice_ai.ppn"],  # Custom keyword file
        )
```

**Pros**: Best accuracy, built-in noise robustness.
**Cons**: Free tier limited, requires custom .ppn file creation.

### Recommended Path

1. **MVP**: Button press activation (no wake word needed)
2. **V2**: STT-based detection (reuse Whisper tiny model)
3. **V3**: OpenWakeWord or Porcupine for production-quality detection

---

## Audio Buffering

### Ring Buffer for Continuous Capture

```python
class RingBuffer:
    def __init__(self, capacity_chunks: int = 30):
        self._buffer: collections.deque[np.ndarray] = collections.deque(
            maxlen=capacity_chunks
        )

    def append(self, chunk: np.ndarray) -> None:
        self._buffer.append(chunk)

    def get_all(self) -> np.ndarray:
        return np.concatenate(list(self._buffer))

    def clear(self) -> None:
        self._buffer.clear()

    @property
    def duration_s(self, sample_rate: int = 16000) -> float:
        total_samples = sum(len(c) for c in self._buffer)
        return total_samples / sample_rate
```

### Pre-speech Buffer

Keep a rolling buffer of the last ~1s of audio before speech is detected,
so the start of the utterance isn't clipped:

```python
PRE_SPEECH_CHUNKS = 2  # ~1s at 500ms chunks

async def listen_with_prebuffer(self) -> np.ndarray:
    pre_buffer = RingBuffer(capacity_chunks=PRE_SPEECH_CHUNKS)
    while True:
        chunk = await self.audio_in.read_chunk()
        if self.vad.is_speech(chunk):
            speech_chunks = [chunk]
            # ... continue recording until silence
            all_audio = np.concatenate(list(pre_buffer._buffer) + speech_chunks)
            return all_audio
        pre_buffer.append(chunk)
```

---

## Noise Handling

- **Auto Gain**: Not needed — sounddevice provides normalized float32
- **Noise Gate**: VAD threshold effectively acts as noise gate
- **Clipping Protection**: Clamp float32 to [-1.0, 1.0] before processing

```python
def clamp_audio(audio: np.ndarray) -> np.ndarray:
    return np.clip(audio, -1.0, 1.0).astype(np.float32)
```
