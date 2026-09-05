"""Diagnostic script for TTS synthesis and audio playback.

Checks:
1. Silero TTS model loading
2. Text synthesis (Russian text)
3. Audio array validation (dtype, shape, values)
4. WAV file save for manual verification
5. Playback through sounddevice
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import os
import tempfile
import logging

import numpy as np

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(name)s | %(levelname)s | %(message)s")
logger = logging.getLogger("test_tts")


def test_silero_tts_load() -> None:
    print("=" * 60)
    print("Step 1: Loading Silero TTS model")
    print("=" * 60)
    from src.tts.silero_engine import SileroTTSEngine
    from src.core.config import Config

    config = Config(_env_file=None)
    print(f"  Config: language={config.silero_language}, speaker={config.silero_speaker}, "
          f"voice={config.silero_voice}, sample_rate={config.silero_sample_rate}")

    tts = SileroTTSEngine(config)
    print("  Calling tts.load()...")
    tts.load()
    print(f"  Model loaded: _model={type(tts._model)}, _apply_tts_fn={type(tts._apply_tts_fn)}, "
          f"_symbols={type(tts._symbols)}")
    print(f"  _model is None? {tts._model is None}")
    print(f"  _apply_tts_fn is None? {tts._apply_tts_fn is None}")
    if tts._symbols is not None:
        print(f"  _symbols count: {len(tts._symbols) if hasattr(tts._symbols, '__len__') else 'N/A'}")
    return tts


def test_synthesis(tts, text: str) -> np.ndarray | None:
    print()
    print("=" * 60)
    print(f"Step 2: Synthesizing text: '{text}'")
    print("=" * 60)

    result = tts._synthesize_sync(text)

    if result is None:
        print("  FAIL: _synthesize_sync returned None!")
        print("  The TTS engine failed to synthesize the text.")
        print("  Check the error logs above for details.")
        return None

    print(f"  SUCCESS: Got audio array")
    print(f"    dtype:   {result.dtype}")
    print(f"    shape:   {result.shape}")
    print(f"    min:     {result.min():.6f}")
    print(f"    max:     {result.max():.6f}")
    print(f"    mean:    {result.mean():.6f}")
    print(f"    rms:     {np.sqrt(np.mean(result**2)):.6f}")
    print(f"    samples: {len(result)}")

    if result.max() == 0 and result.min() == 0:
        print("  WARNING: Audio is all zeros — silence!")
    if np.all(np.abs(result) < 1e-6):
        print("  WARNING: Audio values near zero — effectively silence!")

    duration = len(result) / 48000
    print(f"    duration: {duration:.2f}s (at 48000 Hz)")

    return result


def test_synthesis_direct() -> None:
    print()
    print("=" * 60)
    print("Step 2b: Direct Silero TTS call (bypassing SileroTTSEngine)")
    print("=" * 60)
    try:
        import torch

        hub_dir = torch.hub.get_dir()
        repo_dir = os.path.join(hub_dir, "snakers4_silero-models_master")
        silero_src_dir = os.path.join(repo_dir, "src")
        silero_init = os.path.join(silero_src_dir, "__init__.py")
        created_init = False
        if not os.path.exists(silero_init):
            with open(silero_init, "w"):
                pass
            created_init = True

        saved_src = sys.modules.pop("src", None)
        saved_src_subs = {k: v for k, v in list(sys.modules.items()) if k.startswith("src.")}
        for k in saved_src_subs:
            del sys.modules[k]

        if repo_dir not in sys.path:
            sys.path.insert(0, repo_dir)

        try:
            from src.silero import silero_tts
            print("  Loading model via silero_tts(language='ru', speaker='v5_ru')...")
            result = silero_tts(language="ru", speaker="v5_ru")
        finally:
            if repo_dir in sys.path:
                sys.path.remove(repo_dir)
            for k in list(sys.modules):
                if k == "src" or k.startswith("src."):
                    del sys.modules[k]
            if saved_src is not None:
                sys.modules["src"] = saved_src
            sys.modules.update(saved_src_subs)
            if created_init:
                try:
                    os.remove(silero_init)
                except OSError:
                    pass

        if isinstance(result, tuple) and len(result) == 5:
            model, symbols, sample_rate, _, apply_tts_fn = result
            print(f"  Got 5-tuple: model={type(model)}, symbols={len(symbols)}, "
                  f"sample_rate={sample_rate}, apply_tts_fn={type(apply_tts_fn)}")
        else:
            model = result[0] if isinstance(result, (tuple, list)) else result
            apply_tts_fn = None
            sample_rate = 48000
            print(f"  Got non-5-tuple result, type={type(result)}")

        test_text = "Привет, это тестовое сообщение."
        print(f"  Synthesizing: '{test_text}'")

        if apply_tts_fn is not None:
            print("  Using apply_tts_fn (v5 API)...")
            audios = apply_tts_fn([test_text], model, 48000, symbols, "cpu")
            audio = np.array(audios[0], dtype=np.float32)
            print(f"  Result: dtype={audio.dtype}, shape={audio.shape}, "
                  f"min={audio.min():.6f}, max={audio.max():.6f}, len={len(audio)}")
        else:
            print("  Using model.apply_tts() (older API)...")
            audio_tensor = model.apply_tts(text=test_text, speaker="baya", sample_rate=48000)
            audio = audio_tensor.numpy().astype(np.float32)
            print(f"  Result: dtype={audio.dtype}, shape={audio.shape}, "
                  f"min={audio.min():.6f}, max={audio.max():.6f}, len={len(audio)}")

    except Exception as e:
        print(f"  FAILED: {e}")
        import traceback
        traceback.print_exc()


def test_save_wav(audio: np.ndarray, sample_rate: int = 48000) -> str:
    print()
    print("=" * 60)
    print("Step 3: Saving audio to WAV file")
    print("=" * 60)
    try:
        import soundfile as sf
        wav_path = os.path.join(tempfile.gettempdir(), "test_tts_output.wav")
        sf.write(wav_path, audio, sample_rate)
        file_size = os.path.getsize(wav_path)
        print(f"  Saved: {wav_path} ({file_size} bytes)")
        print(f"  Play manually:  python -m sounddevice or any audio player")
        return wav_path
    except Exception as e:
        print(f"  FAILED to save WAV: {e}")
        return ""


def test_playback(audio: np.ndarray, sample_rate: int = 48000) -> None:
    print()
    print("=" * 60)
    print("Step 4: Playback through sounddevice")
    print("=" * 60)

    import sounddevice as sd

    print("  Available output devices:")
    for i, dev in enumerate(sd.query_devices()):
        if dev["max_output_channels"] > 0:
            marker = " <-- default" if i == sd.default.device[1] else ""
            print(f"    [{i}] {dev['name']}  (out:{dev['max_output_channels']}, sr:{dev['default_samplerate']}){marker}")

    default_out = sd.query_devices(sd.default.device[1])
    print(f"\n  Default output device: {default_out['name']} "
          f"(sr={default_out['default_samplerate']}, channels={default_out['max_output_channels']})")
    print(f"  Attempting playback: {len(audio)} samples at {sample_rate} Hz, duration={len(audio)/sample_rate:.2f}s")

    try:
        sd.play(audio, samplerate=sample_rate, blocking=True)
        sd.wait()
        print("  Playback completed successfully!")
    except Exception as e:
        print(f"  Playback FAILED: {e}")
        import traceback
        traceback.print_exc()

        print("\n  Trying with resampled audio at device default rate...")
        try:
            device_sr = int(default_out["default_samplerate"])
            if device_sr != sample_rate:
                from scipy.signal import resample as scipy_resample
                num_samples = int(len(audio) * device_sr / sample_rate)
                resampled = scipy_resample(audio, num_samples).astype(np.float32)
                print(f"  Resampled: {len(audio)} @ {sample_rate}Hz -> {len(resampled)} @ {device_sr}Hz")
                sd.play(resampled, samplerate=device_sr, blocking=True)
                sd.wait()
                print("  Resampled playback completed successfully!")
            else:
                print("  Sample rates match, no resampling needed.")
        except Exception as e2:
            print(f"  Resampled playback also FAILED: {e2}")


def test_playback_chunks(audio: np.ndarray, sample_rate: int = 48000) -> None:
    print()
    print("=" * 60)
    print("Step 5: Playback in chunks (like SoundDeviceOutput.play)")
    print("=" * 60)

    import sounddevice as sd

    chunk_size = int(sample_rate * 0.1)
    print(f"  Chunk size: {chunk_size} samples ({0.1*1000:.0f}ms)")
    print(f"  Total chunks: {len(audio) // chunk_size + 1}")

    try:
        for i in range(0, len(audio), chunk_size):
            chunk = audio[i: i + chunk_size]
            sd.play(chunk, samplerate=sample_rate, blocking=True)
        sd.wait()
        print("  Chunked playback completed successfully!")
    except Exception as e:
        print(f"  Chunked playback FAILED: {e}")
        import traceback
        traceback.print_exc()


def main() -> None:
    test_text = "Привет! Это тест озвучивания. Если вы слышите это сообщение, значит текст в речь работает правильно."

    tts = test_silero_tts_load()
    audio = test_synthesis(tts, test_text)

    if audio is not None:
        test_save_wav(audio, sample_rate=48000)
        test_playback(audio, sample_rate=48000)
        test_playback_chunks(audio, sample_rate=48000)
    else:
        print("\n  TTS synthesis returned None — running direct Silero test...")
        test_synthesis_direct()


if __name__ == "__main__":
    main()