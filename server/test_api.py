import io
import numpy as np
import soundfile as sf
from fastapi.testclient import TestClient

from bot import app

client = TestClient(app)


def _tone_wav():
    sr = 16000
    t = np.linspace(0, 1, sr, False)
    tone = (np.sin(2 * np.pi * 440 * t) * 0.3).astype(np.float32)
    buf = io.BytesIO()
    sf.write(buf, tone, sr, format="WAV")
    buf.seek(0)
    return buf


def test_tts_endpoint():
    response = client.post("/api/tts", json={"text": "hello"})
    assert response.status_code == 200
    assert response.headers["content-type"] == "audio/wav"
    assert len(response.content) > 0


def test_transcribe_endpoint():
    buf = _tone_wav()
    files = {"file": ("tone.wav", buf, "audio/wav")}
    response = client.post("/api/transcribe", files=files)
    assert response.status_code == 200
    body = response.json()
    assert "text" in body
