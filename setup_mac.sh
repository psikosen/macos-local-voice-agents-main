#!/bin/bash
set -euo pipefail

OS_NAME="$(uname -s)"
if [[ "$OS_NAME" != "Darwin" ]]; then
    echo "[ERROR] setup_mac.sh must be run on macOS (Darwin). Detected: $OS_NAME" >&2
    exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$SCRIPT_DIR"
VENV_DIR="$PROJECT_ROOT/venv"
LOG_DIR="$PROJECT_ROOT/logs"

info() { echo "[INFO] $1"; }
success() { echo "[SUCCESS] $1"; }
warning() { echo "[WARNING] $1"; }
error() { echo "[ERROR] $1" >&2; }

require_command() {
    local cmd="$1"
    local install_hint="$2"
    if ! command -v "$cmd" >/dev/null 2>&1; then
        error "Missing required command: $cmd"
        echo "$install_hint" >&2
        exit 1
    fi
}

ensure_brew_package() {
    local package="$1"
    if brew list "$package" >/dev/null 2>&1; then
        info "brew package '$package' already installed"
    else
        info "Installing brew package '$package'"
        brew install "$package"
    fi
}

info "Detected macOS. Preparing environment in $PROJECT_ROOT"

require_command "brew" "Install Homebrew from https://brew.sh before running this script."
require_command "python3" "Install Python 3 (3.11 or newer) via Homebrew: brew install python@3.11"
require_command "npm" "Install Node.js 18+: brew install node"

BREW_PACKAGES=(ffmpeg sox portaudio)
for pkg in "${BREW_PACKAGES[@]}"; do
    ensure_brew_package "$pkg"
done

if [[ ! -d "$VENV_DIR" ]]; then
    info "Creating Python virtual environment"
    python3 -m venv "$VENV_DIR"
else
    info "Python virtual environment already exists"
fi

source "$VENV_DIR/bin/activate"
trap 'deactivate >/dev/null 2>&1 || true' EXIT

info "Upgrading pip and wheel"
pip install --upgrade pip wheel

info "Installing Python dependencies"
pip install -r "$PROJECT_ROOT/server/requirements.txt"

info "Installing macOS MLX extras"
pip install "mlx>=0.25.0" "mlx-lm>=0.19.0,<0.24.0" mlx-audio==0.2.0

deactivate
trap - EXIT

info "Installing Node.js dependencies"
(cd "$PROJECT_ROOT/client" && npm install)

mkdir -p "$LOG_DIR"
info "Downloading required KittenTTS models (logs: $LOG_DIR/model_download.log)"
source "$VENV_DIR/bin/activate"
python "$PROJECT_ROOT/server/download_kittentts_model.py" >>"$LOG_DIR/model_download.log" 2>&1 || \
    warning "Model download encountered issues. Review $LOG_DIR/model_download.log"
deactivate

success "macOS setup complete. Start the stack with ./run_mac.sh"
