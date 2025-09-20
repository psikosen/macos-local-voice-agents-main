"""Whisper.cpp-based STT service."""
from __future__ import annotations

import asyncio
from typing import AsyncGenerator

import numpy as np
from loguru import logger
from pipecat.frames.frames import ErrorFrame, Frame, TranscriptionFrame
from pipecat.services.stt_service import STTService
from pipecat.utils.datetime import time_now_iso8601

from .audio_utils import ensure_pcm16, TARGET_SAMPLE_RATE


class WhisperCPPSTTService(STTService):
    """Speech-to-text using whisper.cpp bindings."""

    def __init__(self, model_path: str, **kwargs):
        super().__init__(sample_rate=TARGET_SAMPLE_RATE, **kwargs)
        import whispercpp

        self._model = whispercpp.Whisper(model_path)
        self._settings = {"engine": "whispercpp"}

    async def run_stt(self, audio: bytes) -> AsyncGenerator[Frame, None]:
        try:
            await self.start_processing_metrics()
            await self.start_ttfb_metrics()
            audio_norm = ensure_pcm16(
                audio,
                self.sample_rate,
                TARGET_SAMPLE_RATE,
            )
            audio_float = (
                np.frombuffer(audio_norm, dtype=np.int16).astype(np.float32)
                / 32768.0
            )
            result = await asyncio.to_thread(
                self._model.transcribe,
                audio_float,
            )
            text = result.get("text", "").strip()
            await self.stop_ttfb_metrics()
            await self.stop_processing_metrics()
            if text:
                yield TranscriptionFrame(
                    text,
                    self._user_id,
                    time_now_iso8601(),
                    self._settings.get("language"),
                )
        except Exception as e:
            logger.exception(f"whisper.cpp transcription error: {e}")
            yield ErrorFrame(f"Whisper.cpp transcription error: {e}")
