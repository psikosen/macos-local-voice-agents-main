import importlib.util
import io
import sys
import types
import wave
from pathlib import Path

import numpy as np


def _load_test_service(monkeypatch):
    module_name = "server.kittentts_service_testdouble"
    module_path = Path(__file__).resolve().parent / "kittentts_service.py"
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    module = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, module_name, module)
    spec.loader.exec_module(module)
    return module


def test_synthesize_produces_wav_payload(monkeypatch):
    stub_module = types.ModuleType("kittentts")

    class _StubKittenTTS:
        last_call: tuple[str, str] | None = None

        def __init__(self, *_args, **_kwargs):
            pass

        def generate(self, text: str, voice: str = "expr-voice-2-f"):
            type(self).last_call = (text, voice)
            return np.array([0.0, 0.25, -0.25, 0.5, -0.5], dtype=np.float32)

    stub_module.KittenTTS = _StubKittenTTS
    monkeypatch.setitem(sys.modules, "kittentts", stub_module)

    module = _load_test_service(monkeypatch)
    service = module.KittenTTSService(sample_rate=16000)

    wav_bytes = service.synthesize("Hello world", voice="expr-voice-3-f")

    with wave.open(io.BytesIO(wav_bytes), "rb") as wav_file:
        assert wav_file.getnchannels() == 1
        assert wav_file.getsampwidth() == 2
        assert wav_file.getframerate() == 16000
        frames = wav_file.readframes(wav_file.getnframes())

    pcm = np.frombuffer(frames, dtype=np.int16)
    assert pcm.size > 0
    assert pcm.max() != 0 or pcm.min() != 0
    assert service._settings["sample_rate"] == 16000
    assert _StubKittenTTS.last_call == ("Hello world", "expr-voice-3-f")
