#!/usr/bin/env python3
"""
Simple TTS service that generates basic audio tones.
This is a fallback when Kokoro TTS is not available.
"""

import asyncio
import numpy as np
from typing import AsyncGenerator, Optional

from pipecat.frames.frames import (
    ErrorFrame,
    Frame,
    TTSAudioRawFrame,
    TTSStartedFrame,
    TTSStoppedFrame,
)
from pipecat.services.tts_service import TTSService
from pipecat.utils.tracing.service_decorators import traced_tts


class SimpleTTSService(TTSService):
    """Simple TTS service that generates basic audio tones."""

    def __init__(
        self,
        *,
        sample_rate: int = 24000,
        **kwargs,
    ):
        """Initialize the simple TTS service."""
        super().__init__(sample_rate=sample_rate, **kwargs)

    def can_generate_metrics(self) -> bool:
        return True

    async def run_tts(self, text: str) -> AsyncGenerator[Frame, None]:
        """Generate simple audio for the given text."""
        try:
            # Send TTS started frame
            yield TTSStartedFrame()

            # Generate a simple beep sound (1 second)
            duration = 1.0  # seconds
            frequency = 440.0  # Hz (A4 note)
            
            # Generate sine wave
            t = np.linspace(0, duration, int(self.sample_rate * duration), False)
            audio = np.sin(2 * np.pi * frequency * t) * 0.3  # 30% volume
            
            # Convert to 16-bit PCM
            audio_int16 = (audio * 32767).astype(np.int16)
            
            # Send audio frame
            yield TTSAudioRawFrame(
                audio=audio_int16.tobytes(),
                sample_rate=self.sample_rate,
            )
            
            # Send TTS stopped frame
            yield TTSStoppedFrame()
            
        except Exception as e:
            yield ErrorFrame(error=str(e), fatal=False)
