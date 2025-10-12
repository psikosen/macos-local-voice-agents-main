#!/bin/bash
set -euo pipefail

OS_NAME="$(uname -s)"
if [[ "$OS_NAME" != "Darwin" ]]; then
    echo "[ERROR] run_mac.sh must be executed on macOS (Darwin). Detected: $OS_NAME" >&2
    exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$SCRIPT_DIR"
VENV_DIR="$PROJECT_ROOT/venv"
CLIENT_NODE_MODULES="$PROJECT_ROOT/client/node_modules"

if [[ ! -d "$VENV_DIR" ]]; then
    echo "[ERROR] Python virtual environment missing. Run ./setup_mac.sh first." >&2
    exit 1
fi

if [[ ! -d "$CLIENT_NODE_MODULES" ]]; then
    echo "[ERROR] Node.js dependencies missing. Run ./setup_mac.sh before starting." >&2
    exit 1
fi

source "$VENV_DIR/bin/activate"
trap 'deactivate >/dev/null 2>&1 || true' EXIT

if ! python -c "import kokoro_tts" >/dev/null 2>&1; then
    echo "[WARNING] kokoro_tts import check failed. Setup may be incomplete." >&2
fi

deactivate
trap - EXIT

exec "$PROJECT_ROOT/start.sh"
