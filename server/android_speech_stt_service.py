"""Android Speech API STT service using Google Cloud Speech."""
from __future__ import annotations

import asyncio
from typing import AsyncGenerator

from google.cloud import speech
from loguru import logger
from pipecat.frames.frames import ErrorFrame, Frame, TranscriptionFrame
from pipecat.services.stt_service import STTService
from pipecat.utils.datetime import time_now_iso8601

from .audio_utils import ensure_pcm16, TARGET_SAMPLE_RATE


class AndroidSpeechSTTService(STTService):
    """Speech-to-text using Google Cloud's Speech-to-Text API."""

    def __init__(self, credentials_path: str | None = None, **kwargs):
        super().__init__(sample_rate=TARGET_SAMPLE_RATE, **kwargs)
        if credentials_path:
            self._client = speech.SpeechClient.from_service_account_file(
                credentials_path
            )
        else:
            self._client = speech.SpeechClient()
        self._settings = {"engine": "android"}

    async def run_stt(self, audio: bytes) -> AsyncGenerator[Frame, None]:
        try:
            await self.start_processing_metrics()
            await self.start_ttfb_metrics()
            audio_norm = ensure_pcm16(
                audio,
                self.sample_rate,
                TARGET_SAMPLE_RATE,
            )
            config = speech.RecognitionConfig(
                encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
                sample_rate_hertz=TARGET_SAMPLE_RATE,
                language_code="en-US",
            )
            audio_google = speech.RecognitionAudio(content=audio_norm)
            response = await asyncio.to_thread(
                self._client.recognize,
                config=config,
                audio=audio_google,
            )
            await self.stop_ttfb_metrics()
            await self.stop_processing_metrics()
            for result in response.results:
                text = result.alternatives[0].transcript.strip()
                if text:
                    yield TranscriptionFrame(
                        text,
                        self._user_id,
                        time_now_iso8601(),
                        None,
                    )
        except Exception as e:
            logger.exception(f"Android Speech transcription error: {e}")
            yield ErrorFrame(f"Android Speech transcription error: {e}")
