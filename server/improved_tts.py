#!/usr/bin/env python3
"""
Improved TTS service that generates more realistic audio.
This is a fallback when KittenTTS is not available.
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


class ImprovedTTSService(TTSService):
    """Improved TTS service that generates more realistic audio."""

    def __init__(
        self,
        *,
        sample_rate: int = 24000,
        **kwargs,
    ):
        """Initialize the improved TTS service."""
        super().__init__(sample_rate=sample_rate, **kwargs)

    def can_generate_metrics(self) -> bool:
        return True

    def _generate_speech_like_audio(self, text: str) -> bytes:
        """Generate speech-like audio using formants and sine waves."""
        # Convert text to phonemes (simplified)
        phonemes = self._text_to_phonemes(text)
        
        # Generate audio for each phoneme
        audio_segments = []
        for phoneme in phonemes:
            duration = 0.1  # 100ms per phoneme
            samples = int(duration * self.sample_rate)
            
            # Generate formant-based audio
            audio = self._generate_phoneme_audio(phoneme, samples)
            audio_segments.append(audio)
        
        # Concatenate all segments
        if audio_segments:
            full_audio = np.concatenate(audio_segments)
        else:
            # Fallback to a simple beep
            full_audio = self._generate_beep(1.0)
        
        # Convert to 16-bit PCM
        audio_int16 = (full_audio * 32767).astype(np.int16)
        return audio_int16.tobytes()

    def _text_to_phonemes(self, text: str) -> list:
        """Convert text to phonemes (simplified)."""
        # Simple phoneme mapping
        phoneme_map = {
            'a': 'ah', 'e': 'eh', 'i': 'iy', 'o': 'ow', 'u': 'uw',
            'b': 'b', 'c': 'k', 'd': 'd', 'f': 'f', 'g': 'g',
            'h': 'hh', 'j': 'jh', 'k': 'k', 'l': 'l', 'm': 'm',
            'n': 'n', 'p': 'p', 'q': 'k', 'r': 'r', 's': 's',
            't': 't', 'v': 'v', 'w': 'w', 'x': 'ks', 'y': 'y', 'z': 'z'
        }
        
        phonemes = []
        for char in text.lower():
            if char in phoneme_map:
                phonemes.append(phoneme_map[char])
            elif char == ' ':
                phonemes.append('silence')
        
        return phonemes

    def _generate_phoneme_audio(self, phoneme: str, samples: int) -> np.ndarray:
        """Generate audio for a specific phoneme."""
        t = np.linspace(0, samples / self.sample_rate, samples, False)
        
        if phoneme == 'silence':
            return np.zeros(samples)
        
        # Formant frequencies for different phonemes
        formants = {
            'ah': [800, 1200, 2500],  # 'a' sound
            'eh': [600, 2000, 2800],  # 'e' sound
            'iy': [300, 2200, 3000],  # 'i' sound
            'ow': [500, 1000, 2400],  # 'o' sound
            'uw': [300, 800, 2200],   # 'u' sound
            'b': [200, 800, 1200],    # voiced stop
            'd': [200, 800, 1200],    # voiced stop
            'g': [200, 800, 1200],    # voiced stop
            'p': [200, 800, 1200],    # unvoiced stop
            't': [200, 800, 1200],    # unvoiced stop
            'k': [200, 800, 1200],    # unvoiced stop
            'f': [400, 1600, 2400],   # fricative
            's': [400, 1600, 2400],   # fricative
            'v': [400, 1600, 2400],   # fricative
            'z': [400, 1600, 2400],   # fricative
            'm': [300, 1000, 2000],   # nasal
            'n': [300, 1000, 2000],   # nasal
            'l': [400, 1200, 2400],   # liquid
            'r': [400, 1200, 2400],   # liquid
            'w': [300, 800, 2200],    # glide
            'y': [300, 2200, 3000],   # glide
            'hh': [400, 1600, 2400],  # aspiration
        }
        
        if phoneme in formants:
            f1, f2, f3 = formants[phoneme]
            
            # Generate formant-based audio
            audio = (
                0.5 * np.sin(2 * np.pi * f1 * t) +
                0.3 * np.sin(2 * np.pi * f2 * t) +
                0.2 * np.sin(2 * np.pi * f3 * t)
            )
            
            # Add some noise for fricatives
            if phoneme in ['f', 's', 'v', 'z', 'hh']:
                noise = np.random.normal(0, 0.1, samples)
                audio += noise
            
            # Apply envelope
            envelope = np.exp(-3 * t / (samples / self.sample_rate))
            audio *= envelope
            
        else:
            # Default to a simple tone
            audio = 0.3 * np.sin(2 * np.pi * 440 * t)
        
        return audio

    def _generate_beep(self, duration: float) -> np.ndarray:
        """Generate a simple beep sound."""
        samples = int(duration * self.sample_rate)
        t = np.linspace(0, duration, samples, False)
        
        # Generate a beep with harmonics
        audio = (
            0.4 * np.sin(2 * np.pi * 440 * t) +  # Fundamental
            0.2 * np.sin(2 * np.pi * 880 * t) +  # First harmonic
            0.1 * np.sin(2 * np.pi * 1320 * t)   # Second harmonic
        )
        
        # Apply fade in/out
        fade_samples = int(0.1 * self.sample_rate)
        fade_in = np.linspace(0, 1, fade_samples)
        fade_out = np.linspace(1, 0, fade_samples)
        
        audio[:fade_samples] *= fade_in
        audio[-fade_samples:] *= fade_out
        
        return audio

    @traced_tts
    async def run_tts(self, text: str) -> AsyncGenerator[Frame, None]:
        """Generate speech from text using improved TTS.

        Args:
            text: The text to convert to speech.

        Yields:
            TTS frames including audio data.
        """
        try:
            # Send TTS started frame
            yield TTSStartedFrame()

            # Generate audio
            audio_bytes = self._generate_speech_like_audio(text)

            # Send audio frame
            yield TTSAudioRawFrame(
                audio=audio_bytes,
                sample_rate=self.sample_rate,
                num_channels=1,
            )

            # Send TTS stopped frame
            yield TTSStoppedFrame()

        except Exception as e:
            yield ErrorFrame(error=str(e), fatal=False)
