#!/bin/bash

# KittenTTS Quick Setup Script
echo "🎙️ Setting up KittenTTS for macOS Voice Agents..."

# Navigate to project directory
cd /Users/raymondgonzalez/Downloads/macos-local-voice-agents-main

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip

# Install KittenTTS and dependencies
echo "Installing KittenTTS and dependencies..."
pip install kittentts soundfile

# Install other requirements
echo "Installing project requirements..."
pip install -r server/requirements.txt

# Test KittenTTS
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
