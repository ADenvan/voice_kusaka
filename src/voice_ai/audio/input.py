import asyncio
import collections
import logging
from collections.abc import AsyncIterator


import numpy as np
import sounddevice as sd

from voice_ai.core.config import Config
from voice_ai.core.exceptions import DeviceNotFoundError

logger = logging.getLogger("voice_ai.audio.input")


class RingBuffer:
    def __init__(self, capacity_chunks: int = 30) -> None:
        self._buffer: collections.deque[np.ndarray] = collections.deque(
            maxlen=capacity_chunks
        )

    def append(self, chunk: np.ndarray) -> None:
        self._buffer.append(chunk)

    def get_all(self) -> np.ndarray:
        if not self._buffer:
            return np.array([], dtype=np.float32)
        return np.concatenate(list(self._buffer))

    def clear(self) -> None:
        self._buffer.clear()

    @property
    def duration_s(self) -> float:
        if not self._buffer:
            return 0.0
        total_samples = sum(len(c) for c in self._buffer)
        return total_samples / 16000

    def __len__(self) -> int:
        return len(self._buffer)


class SoundDeviceInput:
    def __init__(self, config: Config, shutdown_event: asyncio.Event | None = None) -> None:
        self._sample_rate = config.sample_rate
        self._chunk_duration_ms = config.chunk_duration_ms
        self._chunk_size = int(self._sample_rate * self._chunk_duration_ms / 1000)
        self._queue: asyncio.Queue[np.ndarray] = asyncio.Queue(maxsize=20)
        self._stream: sd.InputStream | None = None
        self._continuous_stream: sd.InputStream | None = None
        self.shutdown_event: asyncio.Event | None = shutdown_event
        self.shutdown_event = shutdown_event

    async def start(self) -> None:
        loop = asyncio.get_event_loop()
        queue = self._queue

        def _put_safe(item: np.ndarray) -> None:
            try:
                queue.put_nowait(item)
            except asyncio.QueueFull:
                pass

        try:
            self._stream = sd.InputStream(
                samplerate=self._sample_rate,
                channels=1,
                dtype="float32",
                blocksize=self._chunk_size,
                callback=lambda indata, frames, time_info, status: loop.call_soon_threadsafe(
                    _put_safe, indata[:, 0].copy()
                ),
            )
            self._stream.start()
            logger.info("Microphone started (sample_rate=%d)", self._sample_rate)
        except Exception as e:
            raise DeviceNotFoundError(f"Failed to open microphone: {e}") from e

    async def stop(self) -> None:
        if self._stream:
            self._stream.stop()
            self._stream.close()
            self._stream = None
            logger.info("Microphone stopped")

    async def read_chunk(self) -> np.ndarray:
        return await self._queue.get()

    def drain_queue(self) -> int:
        drained = 0
        while not self._queue.empty():
            try:
                self._queue.get_nowait()
                drained += 1
            except asyncio.QueueEmpty:
                break
        if drained > 0:
            logger.debug("Drained %d stale audio chunks from queue", drained)
        return drained

    async def record_utterance(
        self,
        vad: object | None = None,
        max_duration_s: float = 10.0,
        silence_timeout_s: float = 1.5,
    ) -> np.ndarray:
        chunks: list[np.ndarray] = []
        speech_started = False
        silence_count = 0
        max_silence_chunks = int(silence_timeout_s / (self._chunk_duration_ms / 1000))
        max_chunks = int(max_duration_s / (self._chunk_duration_ms / 1000))

        await self.start()
        try:
            for i in range(max_chunks * 3):
                chunk = await self.read_chunk()
                chunks.append(chunk)

                if vad is not None:
                    is_speech = vad.is_speech(chunk)
                else:
                    is_speech = self._is_speech_energy(chunk)

                if not speech_started:
                    if is_speech:
                        speech_started = True
                        logger.info(
                            "Speech detected at chunk %d (%.1fs)",
                            i, len(np.concatenate(chunks)) / self._sample_rate,
                        )
                    else:
                        chunks.clear()
                    continue

                if is_speech:
                    silence_count = 0
                else:
                    silence_count += 1

                if silence_count >= max_silence_chunks:
                    logger.info(
                        "Speech ended: %d silence chunks (%.1fs timeout)",
                        silence_count, silence_timeout_s,
                    )
                    break
        finally:
            await self.stop()

        audio = np.concatenate(chunks) if chunks else np.array([], dtype=np.float32)
        duration = len(audio) / self._sample_rate
        logger.info(
            "Recorded %.1fs of audio (%d chunks, speech=%s)",
            duration, len(chunks), speech_started,
        )
        return audio

    async def start_continuous(self) -> None:
        loop = asyncio.get_event_loop()
        queue = self._queue

        def _put_safe(item: np.ndarray) -> None:
            try:
                queue.put_nowait(item)
            except asyncio.QueueFull:
                pass

        def _callback(indata: np.ndarray, frames: int, time_info, status) -> None:
            loop.call_soon_threadsafe(_put_safe, indata[:, 0].copy())

        try:
            self._continuous_stream = sd.InputStream(
                samplerate=self._sample_rate,
                channels=1,
                dtype="float32",
                blocksize=self._chunk_size,
                callback=_callback,
            )
            self._continuous_stream.start()
            logger.info("Continuous microphone started (sample_rate=%d)", self._sample_rate)
        except Exception as e:
            raise DeviceNotFoundError(f"Failed to open continuous microphone: {e}") from e

    async def stop_continuous(self) -> None:
        if self._continuous_stream:
            self._continuous_stream.stop()
            self._continuous_stream.close()
            self._continuous_stream = None
            logger.info("Continuous microphone stopped")

    async def stream_utterances(
        self,
        vad: object,
        wake_word: object | None = None,
        pre_speech_chunks: int = 2,
        silence_timeout_s: float = 1.5,
        max_duration_s: float = 15.0,
        min_duration_s: float = 0.5,
        wake_word_window_s: float = 2.0,
    ) -> AsyncIterator[np.ndarray]:
        """Yield utterances detected by VAD with wake word state machine.

        Wake word mode (wake_word is not None):
          - AWAITING_WAKE_WORD: skip utterances without wake word
          - On wake word detection:
            - If utterance is long (> wake_word_window + 1s), yield it — contains command too
            - If short, switch to AWAITING_COMMAND and yield next utterance as command
          - AWAITING_COMMAND: yield utterance as command, switch back to AWAITING_WAKE_WORD

        Continuous mode (wake_word is None): yield every utterance.
        """
        max_silence_chunks = int(silence_timeout_s / (self._chunk_duration_ms / 1000))
        max_chunks = int(max_duration_s / (self._chunk_duration_ms / 1000))
        min_chunks = int(min_duration_s / (self._chunk_duration_ms / 1000))
        wake_word_samples = int(wake_word_window_s * self._sample_rate)
        pre_buffer = RingBuffer(capacity_chunks=pre_speech_chunks)
        awaiting_command = False

        await self.start_continuous()
        try:
            while True:
                chunks: list[np.ndarray] = []
                speech_started = False
                silence_count = 0
                total_chunks = 0

                while total_chunks < max_chunks * 3:
                    try:
                        chunk = await asyncio.wait_for(self._queue.get(), timeout=5.0)
                    except asyncio.TimeoutError:
                        if self.shutdown_event is not None and self.shutdown_event.is_set():
                            return
                        continue

                    total_chunks += 1
                    is_speech = vad.is_speech(chunk) if vad else True

                    if not speech_started:
                        pre_buffer.append(chunk)
                        if is_speech:
                            speech_started = True
                            pre_audio = pre_buffer.get_all()
                            chunks = [pre_audio] if len(pre_audio) > 0 else []
                            chunks.append(chunk)
                            pre_buffer.clear()
                        continue

                    chunks.append(chunk)
                    if is_speech:
                        silence_count = 0
                    else:
                        silence_count += 1

                    if silence_count >= max_silence_chunks and len(chunks) >= min_chunks:
                        break

                if not chunks:
                    continue

                audio = np.concatenate(chunks)
                duration = len(audio) / self._sample_rate

                if duration < min_duration_s:
                    logger.debug("Utterance too short: %.1fs, skipping", duration)
                    pre_buffer.clear()
                    continue

                logger.info("Captured utterance: %.1fs (%d chunks)", duration, len(chunks))

                if wake_word is not None and not awaiting_command:
                    wake_audio = audio[:wake_word_samples] if len(audio) >= wake_word_samples else audio
                    if await wake_word.detect(wake_audio):
                        logger.info("Wake word detected, listening for command...")
                        awaiting_command = True
                        if duration > wake_word_window_s + 1.0:
                            logger.info("Utterance contains wake word + command (%.1fs), yielding", duration)
                            yield audio
                            self.drain_queue()
                            awaiting_command = False
                            continue
                        else:
                            logger.debug("Short wake word utterance (%.1fs), waiting for command", duration)
                            self.drain_queue()
                            continue
                    else:
                        logger.debug("No wake word in utterance (%.1fs), skipping", duration)
                        self.drain_queue()
                        continue
                elif wake_word is not None and awaiting_command:
                    logger.info("Command utterance captured (%.1fs)", duration)
                    yield audio
                    self.drain_queue()
                    awaiting_command = False
                    continue
                else:
                    yield audio
                    self.drain_queue()
        finally:
            await self.stop_continuous()

    @staticmethod
    def _is_speech_energy(chunk: np.ndarray, threshold: float = 0.01) -> bool:
        rms = float(np.sqrt(np.mean(chunk**2)))
        return rms >= threshold