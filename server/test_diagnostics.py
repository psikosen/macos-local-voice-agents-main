import json
import types

import pytest

from server.diagnostics import (
    DiagnosticResult,
    collect_startup_diagnostics,
    format_report,
    has_failures,
)


class _FakeResponse:
    def __init__(self, status: int = 200, body: bytes | None = None):
        self.status = status
        self._body = body or b"{}"

    def read(self):
        return self._body

    def close(self):
        pass


@pytest.fixture
def fake_find_spec():
    def _find_spec(name: str):
        module = types.SimpleNamespace(origin=f"/tmp/{name.replace('.', '/')}.py")
        return module

    return _find_spec


@pytest.fixture
def fake_which():
    return lambda command: f"/usr/bin/{command}"


def test_collect_startup_diagnostics_success(fake_find_spec, fake_which):
    results = collect_startup_diagnostics(
        find_spec=fake_find_spec,
        command_resolver=fake_which,
        opener=lambda url, timeout=2.0: _FakeResponse(200, b"{\"models\": []}"),
        version_info=(3, 11, 4),
    )

    assert {result.name for result in results} >= {
        "python_version",
        "module::pipecat.pipeline.pipeline",
        "module::pipecat.services.whisper.stt",
        "module::kittentts_service",
        "module::kokoro_tts",
        "command::ollama",
        "ollama_http",
    }
    assert all(result.status == "ok" for result in results)
    assert not has_failures(results)


def test_collect_startup_diagnostics_handles_missing_dependencies(fake_which):
    def missing_spec(name: str):
        return None if "kittentts" in name else types.SimpleNamespace(origin="/mock.py")

    response = _FakeResponse(status=503, body=b"{}")
    results = collect_startup_diagnostics(
        find_spec=missing_spec,
        command_resolver=fake_which,
        opener=lambda url, timeout=2.0: response,
        version_info=(3, 10, 9),
    )

    statuses = {result.name: result.status for result in results}
    assert statuses["python_version"] == "error"
    assert statuses["module::kittentts_service"] == "error"
    assert statuses["ollama_http"] == "error"
    assert has_failures(results)


def test_format_report_serializes_results():
    sample = [
        DiagnosticResult(name="python_version", status="ok", detail="3.11"),
        DiagnosticResult(name="module::kittentts_service", status="error", detail="module not found"),
    ]

    report = format_report(sample)
    assert "Voice Agent Startup Diagnostics" in report
    assert "module::kittentts_service: error" in report

    payload = [result.to_dict() for result in sample]
    assert json.loads(json.dumps(payload))[0]["name"] == "python_version"
