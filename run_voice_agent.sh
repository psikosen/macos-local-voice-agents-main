#!/bin/bash

echo "🎉 KittenTTS Voice Agent - Quick Start"
echo "======================================"
echo ""

cd /Users/raymondgonzalez/Downloads/macos-local-voice-agents-main

# Check if setup is needed
if [ ! -f ~/.kittentts_config ]; then
    echo "First time setup detected. Installing KittenTTS..."
    source venv/bin/activate
    cd server
    python setup_kittentts_properly.py
    cd ..
else
    echo "✓ KittenTTS already configured"
fi

# Check if Ollama is running
if ! curl -s http://localhost:11434/v1/models > /dev/null 2>&1; then
    echo ""
    echo "⚠️  Ollama is not running!"
    echo "Please start Ollama in another terminal:"
    echo "  ollama serve"
    echo ""
    echo "Or use LM Studio:"
    echo "  Open LM Studio > Developer tab > Start Server"
    echo ""
    read -p "Press Enter when LLM server is running..."
fi

# Start the application
echo ""
echo "Starting Voice Agent..."
./start.sh
