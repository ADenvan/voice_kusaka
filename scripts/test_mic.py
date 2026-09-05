"""Diagnostic script for microphone and VAD.

Checks:
1. Available audio devices
2. Records 3 seconds of audio
3. Shows RMS level per chunk
4. Tests Silero VAD on recorded data
"""

import time

import numpy as np
import sounddevice as sd


def list_devices() -> None:
    print("=" * 60)
    print("Audio devices:")
    print("=" * 60)
    print(f"Default input device: {sd.default.device[0]}")
    print()
    for i, dev in enumerate(sd.query_devices()):
        if dev["max_input_channels"] > 0:
            marker = " <-- default" if i == sd.default.device[0] else ""
            print(f"  [{i}] {dev['name']}  (in:{dev['max_input_channels']}, sr:{dev['default_samplerate']}){marker}")
    print()


def record_audio(duration_s: float = 3.0, sample_rate: int = 16000) -> np.ndarray:
    print(f"Recording {duration_s}s at {sample_rate}Hz ...")
    audio = sd.rec(
        int(duration_s * sample_rate),
        samplerate=sample_rate,
        channels=1,
        dtype="float32",
    )
    sd.wait()
    audio = audio[:, 0]
    print(f"Recorded {len(audio)} samples ({len(audio)/sample_rate:.2f}s)")
    return audio


def analyze_chunks(audio: np.ndarray, chunk_size: int = 512) -> None:
    print()
    print("=" * 60)
    print(f"RMS levels per {chunk_size}-sample chunk:")
    print("=" * 60)
    n_chunks = len(audio) // chunk_size
    if n_chunks == 0:
        print("Audio too short for analysis")
        return

    rms_values = []
    for i in range(n_chunks):
        start = i * chunk_size
        chunk = audio[start : start + chunk_size]
        rms = float(np.sqrt(np.mean(chunk**2)))
        rms_values.append(rms)

    max_rms = max(rms_values) if rms_values else 0
    avg_rms = float(np.mean(rms_values))

    bar_width = 40
    for i, rms in enumerate(rms_values):
        filled = int(rms / max(max_rms, 1e-6) * bar_width) if max_rms > 1e-6 else 0
        bar = "|" * filled + "." * (bar_width - filled)
        t_start = i * chunk_size / 16000
        print(f"  [{t_start:5.2f}s] {bar}  rms={rms:.5f}")

    print()
    print(f"  Max RMS: {max_rms:.5f}")
    print(f"  Avg RMS: {avg_rms:.5f}")
    print()

    if max_rms < 0.01:
        print("  WARNING: Max RMS < 0.01 — microphone may be muted or not capturing audio!")
    elif max_rms < 0.05:
        print("  WARNING: Max RMS < 0.05 — audio level is very low, check microphone volume.")
    else:
        print("  OK: Microphone is capturing audio.")


def test_silero_vad(audio: np.ndarray, sample_rate: int = 16000) -> None:
    print()
    print("=" * 60)
    print("Silero VAD test:")
    print("=" * 60)
    try:
        import torch

        print("Loading Silero VAD model...")
        model, _ = torch.hub.load(
            repo_or_dir="snakers4/silero-vad",
            model="silero_vad",
            trust_repo=True,
        )

        window = 512 if sample_rate == 16000 else 256
        n_windows = len(audio) // window
        if n_windows == 0:
            print("Audio too short for VAD")
            return

        print(f"Processing {n_windows} windows ({window} samples each)...")
        speech_count = 0
        for i in range(n_windows):
            start = i * window
            chunk = audio[start : start + window]
            tensor = torch.from_numpy(chunk).float()
            prob = model(tensor, sample_rate).item()
            is_speech = prob >= 0.5
            if is_speech:
                speech_count += 1
            t_start = start / sample_rate
            label = "SPEECH" if is_speech else "silence"
            if i % 10 == 0:
                print(f"  [{t_start:5.2f}s] prob={prob:.3f}  {label}")

        print()
        print(f"  Speech windows: {speech_count}/{n_windows}")
        if speech_count == 0:
            print("  WARNING: No speech detected! VAD threshold may be too high, or mic not working.")
        else:
            print("  OK: Speech detected by VAD.")

    except Exception as e:
        print(f"  ERROR: {e}")


def test_vad_class(audio: np.ndarray, sample_rate: int = 16000) -> None:
    print()
    print("=" * 60)
    print("SileroVAD class test (our implementation):")
    print("=" * 60)
    try:
        from src.audio.vad import SileroVAD
        from src.core.config import Config

        config = Config(_env_file=None, db_path=":memory:")
        vad = SileroVAD(config)

        chunk_size = int(sample_rate * config.chunk_duration_ms / 1000)
        n_chunks = len(audio) // chunk_size
        if n_chunks == 0:
            print("Audio too short for chunk analysis")
            return

        print(f"Processing {n_chunks} chunks ({chunk_size} samples each)...")
        speech_count = 0
        for i in range(n_chunks):
            start = i * chunk_size
            chunk = audio[start : start + chunk_size]
            is_speech = vad.is_speech(chunk)
            prob = vad.get_speech_prob(chunk)
            if is_speech:
                speech_count += 1
            t_start = start / sample_rate
            print(f"  [{t_start:5.2f}s] prob={prob:.3f}  {'SPEECH' if is_speech else 'silence'}")

        print()
        print(f"  Speech chunks: {speech_count}/{n_chunks}")

    except Exception as e:
        print(f"  ERROR: {e}")


def main() -> None:
    list_devices()
    audio = record_audio(duration_s=3.0)
    analyze_chunks(audio)
    test_silero_vad(audio)
    test_vad_class(audio)


if __name__ == "__main__":
    main()