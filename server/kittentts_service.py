import asyncio
import concurrent.futures
import io
import os
import sys
import wave
from pathlib import Path
from typing import AsyncGenerator, Optional

import numpy as np
from loguru import logger

try:
    from kittentts import KittenTTS
except ImportError as e:
    logger.error("KittenTTS not installed. Please run: pip install kittentts")
    raise e

from pipecat.frames.frames import (
    ErrorFrame,
    Frame,
    TTSAudioRawFrame,
    TTSStartedFrame,
    TTSStoppedFrame,
)
from pipecat.services.tts_service import TTSService
from pipecat.utils.tracing.service_decorators import traced_tts


class KittenTTSService(TTSService):
    """KittenTTS service implementation for Pipecat.
    
    Provides text-to-speech synthesis using KittenTTS models running locally.
    Uses a separate thread for audio generation to avoid blocking the pipeline.
    """
    
    def __init__(
        self,
        *,
        model: str = None,  # Will auto-detect
        voice: str = "expr-voice-2-f",
        sample_rate: int = 24000,
        max_workers: int = 1,
        **kwargs,
    ):
        """Initialize the KittenTTS service.
        
        Args:
            model: Model path (auto-detected if None)
            voice: The voice to use for synthesis (default: "expr-voice-2-f").
            sample_rate: Output sample rate (default: 24000).
            max_workers: Number of threads for audio generation (default: 1).
            **kwargs: Additional arguments passed to the parent TTSService.
        """
        super().__init__(sample_rate=sample_rate, **kwargs)
        
        self._model_name = model
        self._voice = voice
        self._executor = concurrent.futures.ThreadPoolExecutor(max_workers=max_workers)
        
        # Initialize model in a separate thread to avoid blocking
        self._model = None
        self._init_future = self._executor.submit(self._initialize_model)
        
        self._available_voices = [
            'expr-voice-1-m', 'expr-voice-1-f',
            'expr-voice-2-m', 'expr-voice-2-f',
            'expr-voice-3-m', 'expr-voice-3-f',
            'expr-voice-4-m', 'expr-voice-4-f',
            'expr-voice-5-m', 'expr-voice-5-f'
        ]
        
        self._settings = {
            "model": model,
            "voice": voice,
            "sample_rate": sample_rate,
        }
    
    def _find_model_path(self):
        """Find the KittenTTS model in various possible locations"""
        
        # Possible model locations
        possible_paths = [
            # Original Hugging Face style path
            "KittenML/kitten-tts-nano-0.1",
            
            # Direct cache paths
            Path.home() / ".cache" / "kittentts" / "KittenML" / "kitten-tts-nano-0.1",
            Path.home() / ".cache" / "kittentts" / "KittenML" / "kitten-tts-nano-0.1" / "model.onnx",
            Path.home() / ".cache" / "huggingface" / "hub" / "models--KittenML--kitten-tts-nano-0.1",
            
            # Package installation directory
            Path(__file__).parent / "models" / "kitten-tts-nano-0.1",
            
            # Current directory fallback
            Path.cwd() / "KittenML" / "kitten-tts-nano-0.1",
            Path.cwd() / "models" / "kitten-tts-nano-0.1",
            
            # Simple name
            "kitten-tts-nano-0.1",
        ]
        
        # Check environment variable
        if "KITTENTTS_MODEL_PATH" in os.environ:
            possible_paths.insert(0, Path(os.environ["KITTENTTS_MODEL_PATH"]))
        
        # Try each path
        for path in possible_paths:
            if isinstance(path, Path):
                # Check if it's a directory with model.onnx or if it's the model.onnx file itself
                if path.is_dir() and (path / "model.onnx").exists():
                    return str(path)
                elif path.suffix == ".onnx" and path.exists():
                    return str(path.parent)  # Return directory containing the model
                elif path.exists():
                    return str(path)
            else:
                # For string paths, let KittenTTS handle them
                return path
        
        # If nothing found, return the default and hope KittenTTS can download it
        return "KittenML/kitten-tts-nano-0.1"
    
    def _initialize_model(self):
        """Initialize the KittenTTS model. This runs in a separate thread."""
        try:
            # Set cache directory environment variable
            cache_dir = Path.home() / ".cache" / "kittentts"
            cache_dir.mkdir(parents=True, exist_ok=True)
            os.environ["KITTENTTS_CACHE_DIR"] = str(cache_dir)
            
            # Find the best model path
            if self._model_name is None:
                self._model_name = self._find_model_path()
                logger.info(f"Auto-detected model path: {self._model_name}")
            
            logger.debug(f"Loading KittenTTS model: {self._model_name}")
            
            # Try multiple initialization strategies
            # Based on testing, default initialization works best
            init_strategies = [
                lambda: KittenTTS(),  # Try default first - this works!
                lambda: KittenTTS(self._model_name) if self._model_name else None,
                lambda: KittenTTS("KittenML/kitten-tts-nano-0.1"),
                lambda: KittenTTS("kitten-tts-nano-0.1"),
            ]
            
            model_loaded = False
            last_error = None
            
            for i, strategy in enumerate(init_strategies):
                try:
                    self._model = strategy()
                    logger.info(f"KittenTTS model loaded successfully using strategy {i+1}")
                    model_loaded = True
                    break
                except Exception as e:
                    last_error = e
                    logger.debug(f"Strategy {i+1} failed: {e}")
                    continue
            
            if not model_loaded:
                # If all strategies failed, try to download the model manually
                logger.warning("All initialization strategies failed. Attempting manual download...")
                
                # Run the fix script
                import subprocess
                fix_script = Path(__file__).parent / "fix_model_download.py"
                if fix_script.exists():
                    logger.info("Running model download fix script...")
                    result = subprocess.run([sys.executable, str(fix_script)], capture_output=True, text=True)
                    if result.returncode == 0:
                        logger.info("Model download script succeeded, retrying initialization...")
                        # Try one more time after download
                        self._model = KittenTTS("KittenML/kitten-tts-nano-0.1")
                        model_loaded = True
                    else:
                        logger.error(f"Model download script failed: {result.stderr}")
                
                if not model_loaded:
                    raise RuntimeError(f"Failed to initialize KittenTTS after all attempts. Last error: {last_error}")
            
            logger.info(f"KittenTTS initialized successfully with voice: {self._voice}")
            
        except Exception as e:
            logger.error(f"Failed to initialize KittenTTS model: {e}")
            logger.error("Please run: python server/fix_model_download.py")
            raise
    
    def can_generate_metrics(self) -> bool:
        return True
    
    def _generate_audio_sync(self, text: str, *, voice: Optional[str] = None) -> bytes:
        """Synchronously generate audio from text. This runs in a separate thread."""
        try:
            if self._init_future:
                self._init_future.result()  # Wait for initialization
                self._init_future = None

            if self._model is None:
                raise ValueError("Model not initialized")

            voice_to_use = voice or self._voice
            if voice and voice not in self._available_voices:
                logger.warning(
                    "Requested voice '%s' not in known voices; attempting generation anyway",
                    voice,
                )

            self._settings["voice"] = voice_to_use
            logger.debug(f"Generating audio for: {text}")

            # Generate audio using KittenTTS
            # KittenTTS returns a numpy array with audio samples
            audio_array = self._model.generate(text, voice=voice_to_use)
            
            if audio_array is None or len(audio_array) == 0:
                raise ValueError("No audio generated")
            
            # Ensure audio is 1D array
            if len(audio_array.shape) > 1:
                audio_array = audio_array.squeeze()
            
            # Normalize and convert to 16-bit PCM
            # KittenTTS typically returns normalized float32 audio
            if audio_array.dtype == np.float32 or audio_array.dtype == np.float64:
                # Clip to [-1, 1] range to avoid overflow
                audio_array = np.clip(audio_array, -1.0, 1.0)
                # Convert to 16-bit signed integer
                audio_int16 = (audio_array * 32767).astype(np.int16)
            else:
                # Already in int16 format
                audio_int16 = audio_array.astype(np.int16)
            
            audio_bytes = audio_int16.tobytes()

            logger.debug(f"Generated {len(audio_bytes)} bytes of audio")
            return audio_bytes

        except Exception as e:
            logger.error(f"Error generating audio: {e}")
            raise

    def synthesize(self, text: str, *, voice: Optional[str] = None) -> bytes:
        """Generate a WAV payload for the provided text.

        Args:
            text: Text that should be converted to speech.
            voice: Optional override for the configured voice.

        Returns:
            Bytes representing a 16-bit mono WAV file at the configured sample rate.
        """

        if not text or not text.strip():
            raise ValueError("Text to synthesize must be a non-empty string")

        logger.debug("Synthesizing TTS for %s characters", len(text))
        pcm_audio = self._generate_audio_sync(text, voice=voice)
        target_sample_rate = int(
            self._settings.get("sample_rate") or self.sample_rate or 24000
        )

        buffer = io.BytesIO()
        with wave.open(buffer, "wb") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)  # 16-bit audio
            wav_file.setframerate(target_sample_rate)
            wav_file.writeframes(pcm_audio)

        return buffer.getvalue()
    
    @traced_tts
    async def run_tts(self, text: str) -> AsyncGenerator[Frame, None]:
        """Generate speech from text using KittenTTS.
        
        Args:
            text: The text to convert to speech.
        
        Yields:
            Frame: Audio frames containing the synthesized speech and status frames.
        """
        logger.debug(f"{self}: Generating TTS [{text}]")
        
        try:
            await self.start_ttfb_metrics()
            await self.start_tts_usage_metrics(text)
            
            yield TTSStartedFrame()
            
            # Run audio generation in executor (separate thread) to avoid blocking
            loop = asyncio.get_event_loop()
            audio_bytes = await loop.run_in_executor(
                self._executor, self._generate_audio_sync, text
            )
            
            # Use the chunk_size from parent class for proper streaming
            # This ensures audio is streamed in manageable chunks
            CHUNK_SIZE = self.chunk_size
            
            await self.stop_ttfb_metrics()
            
            # Stream the audio in chunks
            for i in range(0, len(audio_bytes), CHUNK_SIZE):
                chunk = audio_bytes[i : i + CHUNK_SIZE]
                if len(chunk) > 0:
                    # Send audio chunk with proper sample rate and channel count
                    yield TTSAudioRawFrame(
                        audio=chunk,
                        sample_rate=self.sample_rate,
                        num_channels=1
                    )
                    # Small delay to prevent overwhelming the pipeline
                    await asyncio.sleep(0.001)
            
        except Exception as e:
            logger.error(f"Error in run_tts: {e}")
            yield ErrorFrame(error=str(e))
        finally:
            logger.debug(f"{self}: Finished TTS [{text}]")
            # Only call stop_tts_usage_metrics if it exists
            if hasattr(self, 'stop_tts_usage_metrics'):
                await self.stop_tts_usage_metrics()
            yield TTSStoppedFrame()
    
    async def __aenter__(self):
        """Async context manager entry."""
        await super().__aenter__()
        # Ensure model is initialized
        if self._model is None and self._init_future:
            await asyncio.get_event_loop().run_in_executor(None, self._init_future.result)
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        self._executor.shutdown(wait=True)
        await super().__aexit__(exc_type, exc_val, exc_tb)
