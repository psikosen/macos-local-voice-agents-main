#!/bin/bash

echo "🔧 KittenTTS Model Fix - Direct Solution"
echo "========================================"
echo ""

# Navigate to server directory
cd /Users/raymondgonzalez/Downloads/macos-local-voice-agents-main/server

# Activate virtual environment
source ../venv/bin/activate

# Install dependencies if needed
echo "Installing dependencies..."
pip install -q kittentts huggingface_hub

# Run the model download fix
echo ""
echo "Downloading and setting up KittenTTS model..."
python fix_model_download.py

# If that doesn't work, try alternative approach
if [ $? -ne 0 ]; then
    echo ""
    echo "Trying alternative download method..."
    
    # Create cache directory
    mkdir -p ~/.cache/kittentts/KittenML/kitten-tts-nano-0.1
    
    # Download model files directly
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

# Test the setup
echo ""
echo "Testing KittenTTS..."
python test_kittentts.py

echo ""
echo "========================================"
echo "✅ Setup complete!"
echo ""
echo "Now run: ./start.sh"
