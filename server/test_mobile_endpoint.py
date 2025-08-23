import io
import sys
import types
import wave
from importlib import reload
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


def _sample_wav_bytes():
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(16000)
        wf.writeframes(b"\x00\x00" * 160)
    return buf.getvalue()


def _prepare_env(monkeypatch):
    token = "secret-token"
    monkeypatch.setenv("MOBILE_API_TOKEN", token)
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    kokoro = types.ModuleType("kokoro_tts")
    kokoro.KokoroTTSService = object
    sys.modules["kokoro_tts"] = kokoro
    sys.modules["kittentts_service"] = types.ModuleType("kittentts_service")
    sys.modules["kittentts_service"].KittenTTSService = object
    cv2_mod = types.ModuleType("cv2")
    cv2_mod.__spec__ = types.SimpleNamespace()
    sys.modules["cv2"] = cv2_mod

    def stub(name: str, attrs: dict | None = None):
        parts = name.split(".")
        parent = None
        module_name = ""
        for part in parts:
            module_name = f"{module_name}.{part}" if module_name else part
            mod = sys.modules.get(module_name)
            if mod is None:
                mod = types.ModuleType(module_name)
                sys.modules[module_name] = mod
                if parent:
                    setattr(parent, part, mod)
            parent = mod
        if attrs:
            for k, v in attrs.items():
                setattr(parent, k, v)

    stub("pipecat.audio.turn.smart_turn.base_smart_turn", {"SmartTurnParams": object})
    stub("pipecat.audio.turn.smart_turn.local_smart_turn_v2", {"LocalSmartTurnAnalyzerV2": object})
    stub("pipecat.audio.vad.silero", {"SileroVADAnalyzer": object})
    stub("pipecat.audio.vad.vad_analyzer", {"VADParams": object})
    stub("pipecat.pipeline.pipeline", {"Pipeline": object})
    stub("pipecat.pipeline.runner", {"PipelineRunner": object})
    stub("pipecat.pipeline.task", {"PipelineParams": object, "PipelineTask": object})
    stub("pipecat.processors.aggregators.openai_llm_context", {"OpenAILLMContext": object})
    stub("pipecat.services.openai.llm", {"OpenAILLMService": object})
    stub("pipecat.transports.base_transport", {"TransportParams": object})
    stub("pipecat.processors.frameworks.rtvi", {"RTVIConfig": object, "RTVIObserver": object, "RTVIProcessor": object})
    stub("pipecat.transports.network.small_webrtc", {"SmallWebRTCTransport": object})
    class _IceServer:
        def __init__(self, *args, **kwargs):
            pass

    stub(
        "pipecat.transports.network.webrtc_connection",
        {"IceServer": _IceServer, "SmallWebRTCConnection": object},
    )
    stub("pipecat.processors.aggregators.llm_response", {"LLMUserAggregatorParams": object})
    class _MLXModel:
        LARGE_V3_TURBO_Q4 = object()

    stub(
        "pipecat.services.whisper.stt",
        {"WhisperSTTServiceMLX": object, "MLXModel": _MLXModel},
    )
    import server.bot as bot  # noqa
    reload(bot)
    return token, bot


def test_mobile_endpoint_success(monkeypatch):
    token, bot = _prepare_env(monkeypatch)

    class FakeSTT:
        def transcribe(self, audio_bytes):
            return "hello"

    class FakeTTS:
        def synthesize(self, text):
            return b"audio-bytes"

    monkeypatch.setattr(bot, "WhisperSTTServiceMLX", lambda *a, **k: FakeSTT())
    monkeypatch.setattr(bot, "KittenTTSService", lambda *a, **k: FakeTTS())

    client = TestClient(bot.app)
    audio = _sample_wav_bytes()
    response = client.post(
        "/api/mobile",
        files={"file": ("sample.wav", audio, "audio/wav")},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    assert response.content == b"audio-bytes"


def test_mobile_endpoint_unauthorized(monkeypatch):
    token, bot = _prepare_env(monkeypatch)

    client = TestClient(bot.app)
    audio = _sample_wav_bytes()
    response = client.post(
        "/api/mobile",
        files={"file": ("sample.wav", audio, "audio/wav")},
    )
    assert response.status_code == 401
