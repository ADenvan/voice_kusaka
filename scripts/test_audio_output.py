"""Diagnostic script for audio output devices and playback.

Checks:
1. Lists all audio output devices with sample rates
2. Generates a test tone (440Hz sine, 1s)
3. Plays directly via sd.play()
4. Plays via OutputStream callback
5. Plays via SoundDeviceOutput class (same as pipeline)
6. Checks for common issues (device rate mismatch, dtype issues)
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import time
import logging

import numpy as np
import sounddevice as sd

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(name)s | %(levelname)s | %(message)s")
logger = logging.getLogger("test_audio_output")


def list_output_devices() -> None:
    print("=" * 60)
    print("Step 1: Audio output devices")
    print("=" * 60)
    print(f"Default input device:  {sd.default.device[0]}")
    print(f"Default output device: {sd.default.device[1]}")
    print()
    for i, dev in enumerate(sd.query_devices()):
        if dev["max_output_channels"] > 0:
            is_default = " <-- default" if i == sd.default.device[1] else ""
            print(f"  [{i:2d}] {dev['name']}")
            print(f"       out_channels={dev['max_output_channels']}, "
                  f"default_samplerate={dev['default_samplerate']}{is_default}")
    print()


def generate_tone(freq: float = 440.0, duration: float = 1.0, sample_rate: int = 48000) -> np.ndarray:
    t = np.linspace(0, duration, int(duration * sample_rate), dtype=np.float32)
    tone = (0.5 * np.sin(2 * np.pi * freq * t)).astype(np.float32)
    return tone


def test_direct_playback(tone: np.ndarray, sample_rate: int) -> None:
    print("=" * 60)
    print("Step 2: Direct sd.play() — 440Hz tone, 1s")
    print("=" * 60)
    print(f"  Audio: dtype={tone.dtype}, shape={tone.shape}, "
          f"min={tone.min():.4f}, max={tone.max():.4f}, len={len(tone)}")
    try:
        sd.play(tone, samplerate=sample_rate, blocking=True)
        sd.wait()
        print("  SUCCESS: Direct playback completed.")
    except Exception as e:
        print(f"  FAILED: {e}")
        import traceback
        traceback.print_exc()
    print()


def test_direct_playback_at_device_rate(tone: np.ndarray, orig_sr: int) -> None:
    print("=" * 60)
    print("Step 3: sd.play() at device default sample rate")
    print("=" * 60)
    default_sr = int(sd.query_devices(sd.default.device[1])["default_samplerate"])
    print(f"  Device default sample rate: {default_sr}")
    print(f"  Tone sample rate: {orig_sr}")

    if default_sr == orig_sr:
        print("  Rates match, no resampling needed.")
        print()
        return

    from scipy.signal import resample as scipy_resample
    num_samples = int(len(tone) * default_sr / orig_sr)
    resampled = scipy_resample(tone, num_samples).astype(np.float32)
    print(f"  Resampled: {len(tone)} @ {orig_sr}Hz -> {len(resampled)} @ {default_sr}Hz")

    try:
        sd.play(resampled, samplerate=default_sr, blocking=True)
        sd.wait()
        print("  SUCCESS: Playback at device rate completed.")
    except Exception as e:
        print(f"  FAILED: {e}")
    print()


def test_output_stream(tone: np.ndarray, sample_rate: int) -> None:
    print("=" * 60)
    print("Step 4: OutputStream with callback — 440Hz tone")
    print("=" * 60)
    print(f"  Using OutputStream at {sample_rate}Hz...")

    try:
        position = [0]
        total_frames = len(tone)

        def callback(outdata, frames, time_info, status):
            start = position[0]
            end = min(start + frames, total_frames)
            if start >= total_frames:
                outdata[:] = 0
                raise sd.CallbackStop
            remaining = end - start
            outdata[:remaining, 0] = tone[start:end]
            if remaining < frames:
                outdata[remaining:, 0] = 0
            position[0] = end

        with sd.OutputStream(samplerate=sample_rate, channels=1, dtype='float32',
                           callback=callback, blocksize=1024) as stream:
            print(f"  Stream started: samplerate={stream.samplerate}, channels={stream.channels}, "
                  f"dtype={stream.dtype}, device={stream.device}")
            time.sleep(len(tone) / sample_rate + 0.5)

        print("  SUCCESS: OutputStream playback completed.")
    except Exception as e:
        print(f"  FAILED: {e}")
        import traceback
        traceback.print_exc()
    print()


def test_pipeline_output_class(tone: np.ndarray, sample_rate: int) -> None:
    print("=" * 60)
    print("Step 5: SoundDeviceOutput (pipeline class) — 440Hz tone")
    print("=" * 60)
    try:
        from src.audio.output import SoundDeviceOutput
        from src.core.config import Config

        config = Config(_env_file=None)
        output = SoundDeviceOutput(config)

        import asyncio
        asyncio.run(output.play(tone, sample_rate=sample_rate))
        print("  SUCCESS: SoundDeviceOutput.play() completed.")
    except Exception as e:
        print(f"  FAILED: {e}")
        import traceback
        traceback.print_exc()
    print()


def test_pipeline_output_class_with_tts_audio() -> None:
    print("=" * 60)
    print("Step 6: Full TTS -> SoundDeviceOutput pipeline test")
    print("=" * 60)
    try:
        from src.tts.silero_engine import SileroTTSEngine
        from src.audio.output import SoundDeviceOutput
        from src.core.config import Config

        config = Config(_env_file=None)
        tts = SileroTTSEngine(config)
        print("  Loading TTS model...")
        tts.load()
        print(f"  Model loaded: _model={type(tts._model)}, _apply_tts_fn={type(tts._apply_tts_fn)}")

        text = "Тест озвучивания через пайплайн."
        print(f"  Synthesizing: '{text}'")
        import asyncio
        audio = asyncio.run(tts.synthesize(text))

        if audio is None:
            print("  FAILED: TTS returned None!")
            return

        print(f"  Audio: dtype={audio.dtype}, shape={audio.shape}, "
              f"min={audio.min():.6f}, max={audio.max():.6f}, len={len(audio)}")

        output = SoundDeviceOutput(config)
        print(f"  Playing through SoundDeviceOutput at {config.silero_sample_rate}Hz...")
        asyncio.run(output.play(audio, sample_rate=config.silero_sample_rate))
        print("  SUCCESS: Full TTS → playback completed!")

    except Exception as e:
        print(f"  FAILED: {e}")
        import traceback
        traceback.print_exc()
    print()


def main() -> None:
    list_output_devices()
    tone_48k = generate_tone(freq=440.0, duration=1.0, sample_rate=48000)
    tone_16k = generate_tone(freq=440.0, duration=1.0, sample_rate=16000)

    print(f"Generated 440Hz tone at 48kHz: {len(tone_48k)} samples, {len(tone_48k)/48000:.2f}s")
    print(f"Generated 440Hz tone at 16kHz: {len(tone_16k)} samples, {len(tone_16k)/16000:.2f}s")
    print()

    test_direct_playback(tone_48k, 48000)
    test_direct_playback_at_device_rate(tone_48k, 48000)
    test_output_stream(tone_48k, 48000)
    test_pipeline_output_class(tone_48k, 48000)
    test_pipeline_output_class_with_tts_audio()


if __name__ == "__main__":
    main()