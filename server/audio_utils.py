"""Audio utilities for normalization."""
from __future__ import annotations

import numpy as np
from scipy import signal

TARGET_SAMPLE_RATE = 24000


def ensure_pcm16(
    audio: bytes,
    source_rate: int,
    target_rate: int = TARGET_SAMPLE_RATE,
) -> bytes:
    """Normalize raw PCM audio to 16-bit, target sample rate.

    Args:
        audio: Input audio bytes (16-bit PCM).
        source_rate: Sample rate of the input audio.
        target_rate: Desired output sample rate (default: 24kHz).
    Returns:
        Bytes of normalized 16-bit PCM audio at target sample rate.
    """
    audio_np = np.frombuffer(audio, dtype=np.int16).astype(np.float32)
    if source_rate != target_rate:
        audio_np = signal.resample(
            audio_np, int(len(audio_np) * target_rate / source_rate)
        )
    audio_int16 = np.clip(audio_np, -32768, 32767).astype(np.int16)
    return audio_int16.tobytes()
