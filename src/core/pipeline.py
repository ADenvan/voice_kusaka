import asyncio
import logging
import time
from typing import NoReturn

import numpy as np

from src.audio.input import SoundDeviceInput
from src.audio.output import SoundDeviceOutput
from src.audio.vad import SileroVAD
from src.audio.wake_word import STTWakeWord
from src.core.config import Config
from src.core.exceptions import EmptyTranscriptionError
from src.core.protocols import (
    VAD,
    AudioInput,
    AudioOutput,
    LLMClient,
    MemoryStore,
    PipelineState,
    STTEngine,
    TTSEngine,
    TurnResult,
    WakeWordDetector,
)
from src.llm.prompt_builder import PromptBuilder
from src.llm.unified_client import UnifiedLLMClient
from src.memory.context import ContextManager
from src.memory.database import SQLiteStore
from src.stt.whisper_engine import FasterWhisperEngine
from src.tts.silero_engine import BilingualSileroTTSEngine

logger = logging.getLogger("voice_ai.pipeline")


class Pipeline:
    def __init__(
        self,
        audio_in: AudioInput,
        audio_out: AudioOutput,
        vad: VAD,
        stt: STTEngine,
        llm: LLMClient,
        tts: TTSEngine,
        memory: MemoryStore,
        config: Config,
        wake_word: WakeWordDetector | None = None,
    ) -> None:
        self.audio_in = audio_in
        self.audio_out = audio_out
        self.vad = vad
        self.stt = stt
        self.llm = llm
        self.tts = tts
        self.memory = memory
        self.config = config
        self.wake_word = wake_word

        self.state = PipelineState.IDLE
        self.interrupt_event = asyncio.Event()
        self.shutdown_event = asyncio.Event()
        self.session_id: str | None = None
        self._prompt_builder = PromptBuilder()
        self._context_manager = ContextManager(max_messages=config.history_limit)
        self._activation_mode = config.activation_mode

    async def run(self) -> NoReturn:
        logger.info("Pipeline starting (mode=%s)", self._activation_mode)
        self.session_id = await self.memory.create_session()
        logger.info("Session created: %s", self.session_id)

        if hasattr(self.vad, "load"):
            logger.info("Pre-loading VAD model...")
            self.vad.load()
            logger.info("VAD model ready")

        if hasattr(self.stt, "load"):
            logger.info("Pre-loading STT model...")
            self.stt.load()
            logger.info("STT model ready")

        if hasattr(self.tts, "load"):
            logger.info("Pre-loading TTS model...")
            self.tts.load()
            logger.info("TTS model ready")

        if self.wake_word is not None and hasattr(self.wake_word, "load"):
            logger.info("Pre-loading wake word model...")
            self.wake_word.load()
            logger.info("Wake word model ready")

        try:
            if self._activation_mode == "button":
                await self._run_button_mode()
            elif self._activation_mode in ("wake_word", "continuous"):
                await self._run_continuous_mode()
            else:
                logger.warning(
                    "Unknown activation mode: %s, falling back to button",
                    self._activation_mode,
                )
                await self._run_button_mode()
        except asyncio.CancelledError:
            logger.info("Pipeline cancelled")
        finally:
            await self._cleanup()

    async def _run_button_mode(self) -> None:
        while not self.shutdown_event.is_set():
            await self._wait_for_button()
            result = await self._listen_and_process()
            if result:
                logger.info(
                    "Turn complete: latency=%dms interrupted=%s",
                    result.latency_ms, result.interrupted,
                )

    async def _run_continuous_mode(self) -> None:
        use_wake_word = self._activation_mode == "wake_word" and self.wake_word is not None
        logger.info("Continuous mode: wake_word=%s", use_wake_word)

        if not isinstance(self.audio_in, SoundDeviceInput):
            logger.error("Continuous mode requires SoundDeviceInput")
            await self._run_button_mode()
            return

        async for audio in self.audio_in.stream_utterances(
            vad=self.vad,
            wake_word=self.wake_word if use_wake_word else None,
        ):
            if self.shutdown_event.is_set():
                break
            result = await self._process_audio(audio)
            if result:
                logger.info(
                    "Turn complete: latency=%dms interrupted=%s",
                    result.latency_ms, result.interrupted,
                )

    async def _wait_for_button(self) -> None:
        self.state = PipelineState.IDLE
        logger.info("Waiting for activation (press Enter to talk)...")
        await asyncio.to_thread(input, "Нажмите Enter для записи >>> ")

    async def _listen_and_process(self) -> TurnResult | None:
        self.state = PipelineState.LISTENING
        logger.info("Listening...")

        audio = await self.audio_in.record_utterance(
            vad=self.vad,
            max_duration_s=10.0,
            silence_timeout_s=1.5,
        )

        if len(audio) == 0:
            logger.warning("No audio captured")
            self.state = PipelineState.IDLE
            return None

        return await self._process_audio(audio)

    async def _process_audio(self, audio: np.ndarray) -> TurnResult | None:
        start_time = time.monotonic()
        duration = len(audio) / self.config.sample_rate
        logger.info("Processing audio: %.1fs", duration)

        self.state = PipelineState.PROCESSING_STT
        try:
            text = await self.stt.transcribe(audio)
            logger.info("Transcription: %r", text)
        except EmptyTranscriptionError:
            logger.info("Empty transcription, skipping")
            self.state = PipelineState.IDLE
            return None
        except Exception as e:
            logger.error("STT error: %s", e)
            self.state = PipelineState.IDLE
            return None

        await self.memory.save_message(
            session_id=self.session_id, role="user", content=text
        )

        self.state = PipelineState.THINKING
        history = await self.memory.get_history(
            self.session_id, limit=self.config.history_limit
        )
        messages = self._prompt_builder.build_messages(history)

        response_parts: list[str] = []
        try:
            async for token in self.llm.chat_stream(messages):
                response_parts.append(token)
                if self.interrupt_event.is_set():
                    logger.info("Interrupted during LLM generation")
                    break
        except Exception as e:
            logger.error("LLM error: %s", e)
            response_parts.append("Извините, произошла ошибка. Попробуйте ещё раз.")

        response = "".join(response_parts)
        if not response.strip():
            self.state = PipelineState.IDLE
            return None

        logger.info("Assistant: %s", response.strip())
        print(f"\n🤖 {response.strip()}\n")

        await self.memory.save_message(
            session_id=self.session_id, role="assistant", content=response
        )

        self.state = PipelineState.SPEAKING
        logger.info("TTS: synthesizing response (%d chars)", len(response))
        audio_response = await self.tts.synthesize(response)

        if audio_response is None:
            logger.warning(
                "TTS returned None for response (%d chars): %.80s%s — falling back to text-only",
                len(response),
                response,
                "..." if len(response) > 80 else "",
            )
        else:
            logger.info("TTS: got audio response shape=%s dtype=%s len=%d duration=%.2fs",
                        audio_response.shape, audio_response.dtype, len(audio_response),
                        len(audio_response) / self.config.silero_sample_rate)

        interrupted = self.interrupt_event.is_set()

        if audio_response is not None and not interrupted:
            logger.info(
                "Playing audio response through speakers at %d Hz",
                self.config.silero_sample_rate,
            )
            await self.audio_out.play(
                audio_response, sample_rate=self.config.silero_sample_rate
            )
        elif interrupted:
            logger.info("Skipping playback (interrupted)")
        else:
            logger.warning("No audio to play (TTS returned None)")

        self.interrupt_event.clear()
        latency_ms = int((time.monotonic() - start_time) * 1000)
        self.state = PipelineState.IDLE

        return TurnResult(
            user_text=text,
            assistant_text=response,
            audio_duration_s=len(audio_response) / self.config.silero_sample_rate
            if audio_response is not None
            else 0.0,
            latency_ms=latency_ms,
            interrupted=interrupted,
        )

    async def _cleanup(self) -> None:
        logger.info("Pipeline cleanup")
        await self.audio_out.stop()
        if hasattr(self.memory, "close"):
            await self.memory.close()

    async def shutdown(self) -> None:
        self.shutdown_event.set()
        self.interrupt_event.set()


def create_pipeline(config: Config) -> Pipeline:
    audio_in = SoundDeviceInput(config)
    audio_out = SoundDeviceOutput(config)
    vad = SileroVAD(config)
    stt = FasterWhisperEngine(config)

    from src.rag.pdf_loader import PDFDocumentLoader

    if PDFDocumentLoader.has_pdf_files(config.rag_pdf_directory):
        from src.rag.agent import RAGClient, create_rag_config

        rag_config = create_rag_config(config)
        llm: LLMClient = RAGClient(rag_config)
        logger.info("RAG enabled: found PDF files in %s", config.rag_pdf_directory)
    else:
        llm = UnifiedLLMClient(config)

    tts = BilingualSileroTTSEngine(config)
    memory = SQLiteStore(config)
    wake_word: STTWakeWord | None = None
    if config.activation_mode in ("wake_word", "continuous"):
        wake_word = STTWakeWord(config)
    pipeline = Pipeline(
        audio_in, audio_out, vad, stt, llm, tts, memory, config, wake_word=wake_word
    )
    audio_in.shutdown_event = pipeline.shutdown_event
    return pipeline
