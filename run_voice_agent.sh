#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$SCRIPT_DIR"

echo "🎉 KittenTTS Voice Agent - Quick Start"
echo "======================================"
echo ""

cd "$PROJECT_ROOT"

if [ ! -f ~/.kittentts_config ]; then
    echo "First time setup detected. Installing KittenTTS..."
    if [ -f "venv/bin/activate" ]; then
        source venv/bin/activate
    else
        python3 -m venv venv
        source venv/bin/activate
    fi
    cd server
    python setup_kittentts_properly.py
    cd ..
else
    echo "✓ KittenTTS already configured"
fi

if command -v curl >/dev/null 2>&1; then
    if ! curl -s http://localhost:11434/v1/models > /dev/null 2>&1; then
        echo ""
        echo "⚠️  Ollama is not running!"
        echo "Please start Ollama in another terminal:"
        echo "  ollama serve"
        echo ""
        echo "Or use LM Studio:"
        echo "  Open LM Studio > Developer tab > Start Server"
        echo ""
        read -p "Press Enter when an LLM server is running..."
    fi
else
    echo "curl not found. Skipping Ollama availability check."
fi

echo ""
echo "Starting Voice Agent..."
"$PROJECT_ROOT"/start.sh
