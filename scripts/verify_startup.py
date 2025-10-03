#!/usr/bin/env python3
"""CLI utility to verify voice agent runtime dependencies."""

from __future__ import annotations

import argparse
import json
import sys

from server.diagnostics import collect_startup_diagnostics, format_report, has_failures


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Verify voice agent startup dependencies")
    parser.add_argument(
        "--ollama-url",
        default="http://127.0.0.1:11434/v1/models",
        help="HTTP endpoint used to validate Ollama availability (default: %(default)s)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit machine-readable JSON instead of a human formatted report",
    )
    parser.add_argument(
        "--fail-on-warning",
        action="store_true",
        help="Return a non-zero exit code when any warning is produced",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    results = collect_startup_diagnostics(args.ollama_url)

    if args.json:
        payload = [result.to_dict() for result in results]
        print(json.dumps(payload, indent=2))
    else:
        print(format_report(results))

    errors_present = has_failures(results)
    warnings_present = any(result.status == "warning" for result in results)
    if errors_present or (args.fail_on_warning and warnings_present):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
