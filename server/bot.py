import argparse
import asyncio
import inspect
import json
import os
import platform
import sys
from contextlib import asynccontextmanager
from datetime import datetime
from functools import lru_cache
from typing import Dict, Optional
from threading import Lock

# Add local pipecat to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "pipecat", "src"))

from kokoro_tts import KokoroTTSService
import uvicorn
from dotenv import load_dotenv
from fastapi import (
    BackgroundTasks,
    FastAPI,
    File,
    Header,
    HTTPException,
    UploadFile,
    Response,
)
from loguru import logger

from pipecat.audio.turn.smart_turn.base_smart_turn import SmartTurnParams
from pipecat.audio.turn.smart_turn.local_smart_turn_v2 import LocalSmartTurnAnalyzerV2
from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.audio.vad.vad_analyzer import VADParams
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineParams, PipelineTask
from pipecat.processors.aggregators.openai_llm_context import OpenAILLMContext
from pipecat.services.openai.llm import OpenAILLMService
# from kokoro_tts import KokoroTTSService
from kittentts_service import KittenTTSService
# Pipecat Whisper services are platform specific. Import the module and
# introspect the available backends instead of importing symbols directly so
# we can gracefully degrade when MLX isn't present (e.g., on Linux).
try:
    from pipecat.services.whisper import stt as whisper_stt
except ImportError:  # pragma: no cover - handled at runtime
    whisper_stt = None

WhisperSTTServiceMLX = getattr(whisper_stt, "WhisperSTTServiceMLX", None) if whisper_stt else None
MLXModel = getattr(whisper_stt, "MLXModel", None) if whisper_stt else None
WhisperSTTService = getattr(whisper_stt, "WhisperSTTService", None) if whisper_stt else None
ModelSize = getattr(whisper_stt, "ModelSize", None) if whisper_stt else None
from pipecat.transports.base_transport import TransportParams
from pipecat.processors.frameworks.rtvi import RTVIConfig, RTVIObserver, RTVIProcessor
from pipecat.transports.network.small_webrtc import SmallWebRTCTransport
from pipecat.transports.network.webrtc_connection import IceServer, SmallWebRTCConnection
from pipecat.processors.aggregators.llm_response import LLMUserAggregatorParams


load_dotenv(override=True)

app = FastAPI()

pcs_map: Dict[str, SmallWebRTCConnection] = {}

# Token used to authorize mobile API requests
API_TOKEN = os.getenv("MOBILE_API_TOKEN")


def _preferred_model_size():
    """Select the best available Whisper model for the current platform."""
    if not ModelSize:
        return None

    for candidate in (
        "LARGE_V3_TURBO_Q4",
        "LARGE_V3_TURBO",
        "LARGE_V3",
        "LARGE_V2",
        "MEDIUM",
    ):
        if hasattr(ModelSize, candidate):
            return getattr(ModelSize, candidate)
    # Fall back to the smallest defined size if nothing matches our preferred list
    members = [name for name in dir(ModelSize) if name.isupper()]
    for member in sorted(members):
        attr = getattr(ModelSize, member, None)
        if attr is not None:
            return attr
    return None


def _build_mlx_stt():
    if not (WhisperSTTServiceMLX and MLXModel):
        return None

    if platform.system() != "Darwin":
        return None

    try:
        logger.info("Using MLX Whisper STT backend")
        return WhisperSTTServiceMLX(model=MLXModel.LARGE_V3_TURBO_Q4)
    except Exception as exc:  # pragma: no cover - depends on MLX runtime
        logger.warning(f"Unable to initialise MLX Whisper STT: {exc}")
        return None


def _build_generic_stt():
    if not (WhisperSTTService and ModelSize):
        return None

    model_size = _preferred_model_size()
    if not model_size:
        return None

    logger.info("Using Faster Whisper STT backend")
    return WhisperSTTService(model=model_size)


def _create_stt_service():
    """Instantiate an STT service compatible with the current platform."""

    stt_instance = _build_mlx_stt()
    if stt_instance:
        return stt_instance

    stt_instance = _build_generic_stt()
    if stt_instance:
        return stt_instance

    raise RuntimeError(
        "No compatible Whisper STT backend available. "
        "Install pipecat-ai with either the mlx-whisper extra (macOS) or "
        "the faster-whisper extra (Linux/Windows)."
    )


@lru_cache(maxsize=1)
def _get_cached_stt_service():
    """Return a cached STT service for reuse in synchronous endpoints."""

    return _create_stt_service()


_STT_TRANSCRIBE_LOCK = Lock()


def _log_event(function: str, message: str, method: str, error: str | None = None) -> None:
    """Emit structured log events and derived human-readable line."""
    record = {
        "filename": __file__,
        "timestamp": datetime.utcnow().isoformat(),
        "classname": "MobileAPI",
        "function": function,
        "system_section": "api",
        "line_num": inspect.currentframe().f_back.f_lineno,
        "error": error,
        "db_phase": "none",
        "method": method,
        "message": message,
    }
    logger.info(json.dumps(record))
    logger.info("The 17 Commandments of Quality Code")

ice_servers = [
    IceServer(
        urls="stun:stun.l.google.com:19302",
    )
]


SYSTEM_INSTRUCTION = """
"You are Pipecat, a friendly, helpful chatbot.

Your input is text transcribed in realtime from the user's voice. There may be transcription errors. Adjust your responses automatically to account for these errors.

Your output will be converted to audio so don't include special characters in your answers and do not use any markdown or special formatting.

Respond to what the user said in a creative and helpful way. Keep your responses brief unless you are explicitly asked for long or detailed responses. Normally you should use one or two sentences at most. Keep each sentence short. Prefer simple sentences. Try not to use long sentences with multiple comma clauses.

Start the conversation by saying, "Hello, I'm Pipecat!" Then stop and wait for the user.
"""


async def run_bot(webrtc_connection):
    transport = SmallWebRTCTransport(
        webrtc_connection=webrtc_connection,
        params=TransportParams(
            audio_in_enabled=True,
            audio_out_enabled=True,
            vad_analyzer=SileroVADAnalyzer(params=VADParams(stop_secs=0.2)),
            turn_analyzer=LocalSmartTurnAnalyzerV2(
                smart_turn_model_path="",  # Download from HuggingFace
                params=SmartTurnParams(),
            ),
        ),
    )

    try:
        stt = _create_stt_service()
    except RuntimeError as exc:
        logger.error(str(exc))
        raise

    #tts = KokoroTTSService(model="prince-canuma/Kokoro-82M", voice="af_heart", sample_rate=24000)
    # Process-isolated version to avoid Metal assertion failures (now refactored to use standalone worker)
    tts = KittenTTSService()

    llm = OpenAILLMService(
        api_key="not-needed",  # Ollama doesn't require API key
        model="gemma3:270m",  # Medium-sized model. Uses ~8.5GB of RAM.
        # model="mlx-community/Qwen3-235B-A22B-Instruct-2507-3bit-DWQ", # Large model. Uses ~110GB of RAM!
        base_url="http://127.0.0.1:11434/v1",  # Ollama OpenAI-compatible endpoint
        max_tokens=4096,
    )

    context = OpenAILLMContext(
        [
            {
                "role": "user",
                "content": SYSTEM_INSTRUCTION,
            }
        ],
    )
    context_aggregator = llm.create_context_aggregator(
        context,
        # Whisper local service isn't streaming, so it delivers the full text all at
        # once, after the UserStoppedSpeaking frame. Set aggregation_timeout to a
        # a de minimus value since we don't expect any transcript aggregation to be
        # necessary.
        user_params=LLMUserAggregatorParams(aggregation_timeout=0.05),
    )

    #
    # RTVI events for Pipecat client UI
    #
    rtvi = RTVIProcessor(config=RTVIConfig(config=[]))

    pipeline = Pipeline(
        [
            transport.input(),
            stt,
            rtvi,
            context_aggregator.user(),
            llm,
            tts,
            transport.output(),
            context_aggregator.assistant(),
        ]
    )

    task = PipelineTask(
        pipeline,
        params=PipelineParams(
            enable_metrics=True,
            enable_usage_metrics=True,
        ),
        observers=[RTVIObserver(rtvi)],
    )

    @rtvi.event_handler("on_client_ready")
    async def on_client_ready(rtvi):
        await rtvi.set_bot_ready()
        # Kick off the conversation
        await task.queue_frames([context_aggregator.user().get_context_frame()])

    @transport.event_handler("on_first_participant_joined")
    async def on_first_participant_joined(transport, participant):
        print(f"Participant joined: {participant}")
        await transport.capture_participant_transcription(participant["id"])

    @transport.event_handler("on_participant_left")
    async def on_participant_left(transport, participant, reason):
        print(f"Participant left: {participant}")
        await task.cancel()

    runner = PipelineRunner(handle_sigint=False)

    await runner.run(task)


@app.post("/api/offer")
async def offer(request: dict, background_tasks: BackgroundTasks):
    pc_id = request.get("pc_id")

    if pc_id and pc_id in pcs_map:
        pipecat_connection = pcs_map[pc_id]
        logger.info(f"Reusing existing connection for pc_id: {pc_id}")
        await pipecat_connection.renegotiate(
            sdp=request["sdp"],
            type=request["type"],
            restart_pc=request.get("restart_pc", False),
        )
    else:
        pipecat_connection = SmallWebRTCConnection(ice_servers)
        await pipecat_connection.initialize(sdp=request["sdp"], type=request["type"])

        @pipecat_connection.event_handler("closed")
        async def handle_disconnected(webrtc_connection: SmallWebRTCConnection):
            logger.info(f"Discarding peer connection for pc_id: {webrtc_connection.pc_id}")
            pcs_map.pop(webrtc_connection.pc_id, None)

        # Run example function with SmallWebRTC transport arguments.
        background_tasks.add_task(run_bot, pipecat_connection)

    answer = pipecat_connection.get_answer()
    # Updating the peer connection inside the map
    pcs_map[answer["pc_id"]] = pipecat_connection

    return answer


@app.post("/api/mobile")
async def mobile_endpoint(
    file: UploadFile = File(...),
    authorization: Optional[str] = Header(default=None),
):
    """Accept raw audio and return synthesized audio for mobile clients."""
    if API_TOKEN and authorization != f"Bearer {API_TOKEN}":
        _log_event("mobile_endpoint", "unauthorized", "POST", error="unauthorized")
        raise HTTPException(status_code=401, detail="Unauthorized")

    audio_bytes = await file.read()
    _log_event("mobile_endpoint", "received_audio", "POST")

    try:
        stt = _get_cached_stt_service()
    except RuntimeError as exc:
        _log_event("mobile_endpoint", "stt_unavailable", "POST", error=str(exc))
        raise HTTPException(status_code=503, detail=str(exc))
    loop = asyncio.get_running_loop()

    def _run_transcribe():
        with _STT_TRANSCRIBE_LOCK:
            return stt.transcribe(audio_bytes)

    transcript = await loop.run_in_executor(None, _run_transcribe)
    _log_event("mobile_endpoint", "transcribed_audio", "POST")

    response_text = f"You said: {transcript}"

    tts = KittenTTSService()
    audio_out = await loop.run_in_executor(None, tts.synthesize, response_text)
    _log_event("mobile_endpoint", "generated_audio", "POST")

    return Response(content=audio_out, media_type="audio/wav")


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield  # Run app
    coros = [pc.disconnect() for pc in pcs_map.values()]
    await asyncio.gather(*coros)
    pcs_map.clear()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Pipecat Bot Runner")
    parser.add_argument(
        "--host", default="localhost", help="Host for HTTP server (default: localhost)"
    )
    parser.add_argument(
        "--port", type=int, default=7860, help="Port for HTTP server (default: 7860)"
    )
    args = parser.parse_args()

    uvicorn.run(app, host=args.host, port=args.port)
