#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVER_DIR="$SCRIPT_DIR/server"

echo "🔧 KittenTTS Model Fix - Direct Solution"
echo "========================================"
echo ""

if [ ! -d "$SERVER_DIR" ]; then
    echo "Unable to locate server directory at $SERVER_DIR" >&2
    exit 1
fi

cd "$SERVER_DIR"

if [ -f "../venv/bin/activate" ]; then
    echo "Activating project virtual environment..."
    source ../venv/bin/activate
else
    echo "Virtual environment not found. Creating a temporary one..."
    python3 -m venv ../venv
    source ../venv/bin/activate
fi

echo "Installing dependencies..."
pip install -q kittentts huggingface_hub

echo ""
echo "Downloading and setting up KittenTTS model..."
if python fix_model_download.py; then
    FIX_STATUS=0
else
    FIX_STATUS=$?
fi

if [ $FIX_STATUS -ne 0 ]; then
    echo ""
    echo "Trying alternative download method..."

    mkdir -p ~/.cache/kittentts/KittenML/kitten-tts-nano-0.1

    echo "Downloading model.onnx..."
    curl -L "https://huggingface.co/KittenML/kitten-tts-nano-0.1/resolve/main/model.onnx" \
         -o ~/.cache/kittentts/KittenML/kitten-tts-nano-0.1/model.onnx

    echo "Downloading config.json..."
    curl -L "https://huggingface.co/KittenML/kitten-tts-nano-0.1/resolve/main/config.json" \
         -o ~/.cache/kittentts/KittenML/kitten-tts-nano-0.1/config.json

    echo "Downloading tokenizer.json..."
    curl -L "https://huggingface.co/KittenML/kitten-tts-nano-0.1/resolve/main/tokenizer.json" \
         -o ~/.cache/kittentts/KittenML/kitten-tts-nano-0.1/tokenizer.json

    echo ""
    echo "✓ Model files downloaded manually"
fi

echo ""
echo "Testing KittenTTS..."
python test_kittentts.py

echo ""
echo "========================================"
echo "✅ Setup complete!"
echo ""
echo "Now run: ./start.sh"
