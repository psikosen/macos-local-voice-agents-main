#!/bin/bash
set -euo pipefail

OS_NAME="$(uname -s)"
if [[ "$OS_NAME" != "Linux" ]]; then
    echo "[ERROR] setup_linux.sh must be run on Linux. Detected: $OS_NAME" >&2
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
    local instructions="$2"
    if ! command -v "$cmd" >/dev/null 2>&1; then
        error "Missing required command: $cmd"
        echo "$instructions" >&2
        exit 1
    fi
}

install_apt_packages() {
    local packages=("$@")
    if command -v apt-get >/dev/null 2>&1; then
        local runner="apt-get"
        if command -v sudo >/dev/null 2>&1 && [[ $EUID -ne 0 ]]; then
            runner="sudo apt-get"
        elif [[ $EUID -ne 0 ]]; then
            warning "sudo is unavailable; attempting direct apt-get install may fail without privileges."
        fi
        info "Installing apt packages: ${packages[*]}"
        $runner update
        $runner install -y "${packages[@]}"
    else
        warning "apt-get not found. Please install the following packages manually: ${packages[*]}"
    fi
}

info "Detected Linux. Preparing environment in $PROJECT_ROOT"

require_command "python3" "Install Python 3 (3.11 or newer) via your distribution package manager."
require_command "pip" "Install pip for Python 3: python3 -m ensurepip --upgrade"
require_command "npm" "Install Node.js 18+ using your distro package manager or NodeSource binaries."

install_apt_packages python3-venv python3-dev build-essential ffmpeg sox portaudio19-dev libsndfile1

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

info "Installing Linux Whisper extras"
pip install "faster-whisper>=1.0.0" "ctranslate2>=4.3"

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

success "Linux setup complete. Start the stack with ./run_linux.sh"
