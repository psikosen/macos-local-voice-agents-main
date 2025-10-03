"""Startup diagnostics for the voice agent pipeline."""

from __future__ import annotations

import importlib.util
import json
import shutil
import sys
from dataclasses import dataclass
from typing import Callable, Iterable, Sequence
from urllib import error as urllib_error
from urllib import request as urllib_request


@dataclass(frozen=True)
class DiagnosticResult:
    """Single diagnostic outcome."""

    name: str
    status: str
    detail: str

    def to_dict(self) -> dict:
        return {"name": self.name, "status": self.status, "detail": self.detail}


def _check_python_version(version_info: Sequence[int] | None = None) -> DiagnosticResult:
    info = version_info or sys.version_info
    version_str = ".".join(str(part) for part in info[:3])
    status = "ok" if tuple(info[:3]) >= (3, 11, 0) else "error"
    detail = f"Detected Python {version_str}; require >= 3.11"
    return DiagnosticResult(name="python_version", status=status, detail=detail)


def _check_module(module_name: str, find_spec: Callable[[str], object]) -> DiagnosticResult:
    spec = find_spec(module_name)
    if spec is None:
        return DiagnosticResult(name=f"module::{module_name}", status="error", detail="module not found")
    origin = getattr(spec, "origin", "namespace package")
    return DiagnosticResult(name=f"module::{module_name}", status="ok", detail=str(origin))


def _check_command(command: str, resolver: Callable[[str], str | None]) -> DiagnosticResult:
    path = resolver(command)
    if path:
        return DiagnosticResult(name=f"command::{command}", status="ok", detail=path)
    return DiagnosticResult(name=f"command::{command}", status="error", detail="executable not found")


def _check_ollama(
    url: str,
    opener: Callable[[str, float], object],
    timeout: float = 2.0,
) -> DiagnosticResult:
    try:
        response = opener(url, timeout=timeout)
    except urllib_error.URLError as exc:
        return DiagnosticResult(name="ollama_http", status="warning", detail=str(exc.reason))
    except Exception as exc:  # pragma: no cover - defensive guard for unexpected transports
        return DiagnosticResult(name="ollama_http", status="warning", detail=str(exc))

    try:
        status = getattr(response, "status", None)
        if status is None and hasattr(response, "getcode"):
            status = response.getcode()
        body = response.read() if hasattr(response, "read") else b""
        detail = json.dumps({"status": status, "body": body.decode(errors="ignore")[:200]})
    finally:
        if hasattr(response, "close"):
            response.close()

    ok = status is not None and 200 <= status < 400
    return DiagnosticResult(name="ollama_http", status="ok" if ok else "error", detail=detail)


def collect_startup_diagnostics(
    ollama_url: str = "http://127.0.0.1:11434/v1/models",
    *,
    find_spec: Callable[[str], object] = importlib.util.find_spec,
    command_resolver: Callable[[str], str | None] = shutil.which,
    opener: Callable[[str, float], object] | None = None,
    version_info: Sequence[int] | None = None,
) -> list[DiagnosticResult]:
    """Gather diagnostics for verifying the voice agent pipeline."""

    open_fn = opener or (lambda url, timeout=2.0: urllib_request.urlopen(url, timeout=timeout))
    results: list[DiagnosticResult] = []
    results.append(_check_python_version(version_info))

    for module in (
        "pipecat.pipeline.pipeline",
        "pipecat.services.whisper.stt",
        "kittentts_service",
        "kokoro_tts",
    ):
        results.append(_check_module(module, find_spec))

    for command in ("ollama",):
        results.append(_check_command(command, command_resolver))

    results.append(_check_ollama(ollama_url, open_fn))
    return results


def has_failures(results: Iterable[DiagnosticResult]) -> bool:
    return any(result.status == "error" for result in results)


def format_report(results: Iterable[DiagnosticResult]) -> str:
    lines = ["Voice Agent Startup Diagnostics"]
    for result in results:
        lines.append(f"- {result.name}: {result.status} ({result.detail})")
    return "\n".join(lines)


__all__ = [
    "DiagnosticResult",
    "collect_startup_diagnostics",
    "format_report",
    "has_failures",
]
