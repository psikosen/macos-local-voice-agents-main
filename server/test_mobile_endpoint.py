import io
import json
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

    class _ModelSize:
        LARGE_V3_TURBO_Q4 = object()

    stub(
        "pipecat.services.whisper.stt",
        {
            "WhisperSTTServiceMLX": object,
            "MLXModel": _MLXModel,
            "WhisperSTTService": object,
            "ModelSize": _ModelSize,
        },
    )
    import server.bot as bot  # noqa
    reload(bot)
    if hasattr(bot._get_cached_tts_service, "cache_clear"):
        bot._get_cached_tts_service.cache_clear()
    return token, bot


def test_mobile_endpoint_success(monkeypatch):
    token, bot = _prepare_env(monkeypatch)

    class FakeSTT:
        def transcribe(self, audio_bytes):
            return "hello"

    class FakeTTS:
        def synthesize(self, text):
            return b"audio-bytes"

    monkeypatch.setattr(bot, "_create_stt_service", lambda: FakeSTT())
    monkeypatch.setattr(bot, "_get_cached_stt_service", lambda: FakeSTT())
    monkeypatch.setattr(bot, "_get_cached_tts_service", lambda: FakeTTS())

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


def test_mobile_endpoint_logs_success_flow(monkeypatch):
    token, bot = _prepare_env(monkeypatch)

    class FakeSTT:
        def transcribe(self, audio_bytes):
            return "hello"

    class FakeTTS:
        def synthesize(self, text):
            return b"audio-bytes"

    monkeypatch.setattr(bot, "_create_stt_service", lambda: FakeSTT())
    monkeypatch.setattr(bot, "_get_cached_stt_service", lambda: FakeSTT())
    monkeypatch.setattr(bot, "_get_cached_tts_service", lambda: FakeTTS())

    events = []

    def _capture(message):
        events.append(message)

    handler_id = bot.logger.add(_capture, format="{message}")
    client = TestClient(bot.app)
    try:
        response = client.post(
            "/api/mobile",
            files={"file": ("sample.wav", _sample_wav_bytes(), "audio/wav")},
            headers={"Authorization": f"Bearer {token}"},
        )
    finally:
        bot.logger.remove(handler_id)

    assert response.status_code == 200

    structured = []
    derived_lines = []
    for message in events:
        text = message.record["message"]
        if text.startswith("{") and "\"system_section\"" in text:
            structured.append(json.loads(text))
        if text.startswith("[Continuous skepticism (Sherlock Protocol)]"):
            derived_lines.append(text)

    assert {entry["message"] for entry in structured} == {
        "received_audio",
        "transcribed_audio",
        "generated_audio",
    }
    assert all(entry["method"] == "POST" for entry in structured)
    assert all(isinstance(entry["line_num"], int) for entry in structured)
    assert len(derived_lines) >= 3


def test_mobile_endpoint_logs_unauthorized(monkeypatch):
    token, bot = _prepare_env(monkeypatch)

    events = []

    def _capture(message):
        events.append(message)

    handler_id = bot.logger.add(_capture, format="{message}")
    client = TestClient(bot.app)
    try:
        response = client.post(
            "/api/mobile",
            files={"file": ("sample.wav", _sample_wav_bytes(), "audio/wav")},
        )
    finally:
        bot.logger.remove(handler_id)

    assert response.status_code == 401

    structured = []
    derived = []
    for message in events:
        text = message.record["message"]
        if text.startswith("{") and "\"error\"" in text:
            structured.append(json.loads(text))
        if text.startswith("[Continuous skepticism (Sherlock Protocol)]"):
            derived.append(text)

    assert any(entry["message"] == "unauthorized" and entry["error"] == "unauthorized" for entry in structured)
    assert any("error=unauthorized" in line for line in derived)


def test_cached_tts_service_reuses_instance(monkeypatch):
    token, bot = _prepare_env(monkeypatch)

    created_instances = []

    class _FakeTTS:
        pass

    def _factory():
        instance = _FakeTTS()
        created_instances.append(instance)
        return instance

    bot._get_cached_tts_service.cache_clear()
    monkeypatch.setattr(bot, "KittenTTSService", _factory)

    first = bot._get_cached_tts_service()
    second = bot._get_cached_tts_service()

    assert first is second
    assert len(created_instances) == 1
