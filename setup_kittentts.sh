#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$SCRIPT_DIR"

echo "🎙️ Setting up KittenTTS dependencies from $PROJECT_ROOT"

cd "$PROJECT_ROOT"

if [ ! -d "venv" ]; then
    echo "Creating Python virtual environment..."
    python3 -m venv venv
fi

echo "Activating virtual environment..."
source venv/bin/activate

echo "Upgrading pip and wheel..."
pip install --upgrade pip wheel

echo "Installing KittenTTS and audio dependencies..."
pip install kittentts soundfile

echo "Installing project requirements..."
pip install -r server/requirements.txt

echo ""
echo "Testing KittenTTS installation..."
cd server
python test_kittentts.py

echo ""
echo "✅ Setup complete!"
echo ""
echo "To start the voice agent:"
echo "  1. Make sure Ollama or LM Studio is running on port 11434"
echo "  2. Run: ./start.sh"
echo ""
echo "Or start manually:"
echo "  Terminal 1: cd server && python bot.py"
echo "  Terminal 2: cd client && npm run dev"
