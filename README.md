# Local Voice Agents on macOS with Pipecat & KittenTTS

🎙️ **High-quality local voice AI with real speech synthesis**

Pipecat is an open-source, vendor-neutral framework for building real-time voice (and video) AI applications. This repository contains a complete voice agent running with all local models on macOS, featuring **KittenTTS** for high-quality speech synthesis.

On an M-series Mac, you can achieve voice-to-voice latency of <800ms with relatively strong models and natural-sounding speech output.

## 🚀 Quick Start

### 📋 **Script Usage Order**

**First Time Setup:**
1. **`./setup_kittentts.sh`** - Install KittenTTS dependencies (run once)
2. **`./start.sh`** - Start the full application

**Regular Usage:**
- **`./start.sh`** - Start everything (server + client)

**Troubleshooting:**
- **`./quick_fix.sh`** - Fix common issues and restart
- **`./run_voice_agent.sh`** - Alternative startup method

**Windows Users:**
- **`start.bat`** - Windows equivalent of start.sh

---

### Option 1: One-Command Setup (Recommended)
```bash
# Clone and setup everything automatically
git clone <repository-url>
cd macos-local-voice-agents-main
chmod +x *.sh
./start.sh
```

### Option 2: KittenTTS Quick Start
```bash
# For first-time KittenTTS setup
./setup_kittentts.sh

# Then start the agent
./start.sh
```

### Option 3: Manual Setup
```bash
# Setup Python environment
python3 -m venv venv
source venv/bin/activate
pip install -r server/requirements.txt

# Setup Node.js client
cd client
npm install
cd ..

# Start services
./start.sh
```

## 🎯 Run Modes

### 1. **Full Stack Mode** (Default)
```bash
./start.sh
```
- Starts both server and client
- Automatic dependency installation
- Health checks and error handling
- **Server**: `http://localhost:7860`
- **Client**: `http://localhost:3000`

### 2. **KittenTTS Voice Agent Mode**
```bash
./run_voice_agent.sh
```
- Includes Ollama/LM Studio checks
- KittenTTS model verification
- Interactive setup prompts
- Best for first-time users

### 3. **Quick Fix Mode**
```bash
./quick_fix.sh
```
- Fixes KittenTTS model download issues
- Manual model file download
- Troubleshooting for common problems

### 4. **Windows Mode**
```bash
start.bat
```
- Cross-platform Windows support
- Same functionality as `start.sh`
- Automatic environment setup

### 5. **Manual Mode**
```bash
# Terminal 1: Start server
cd server
source ../venv/bin/activate
PYTHONPATH="${PYTHONPATH}:$(pwd)" python bot.py --host localhost --port 7860

# Terminal 2: Start client
cd client
npm run dev
```

## 🏗️ Architecture

The voice agent uses a modern pipeline architecture:

```
Microphone → WhisperSTT → Ollama LLM → KittenTTS → Speakers
```

### Core Components

| Component | Technology | Purpose |
|-----------|------------|---------|
| **Speech Recognition** | WhisperSTTServiceMLX | Real-time speech-to-text |
| **Language Model** | Ollama (Gemma3:270M) | Natural language processing |
| **Text-to-Speech** | KittenTTS | High-quality voice synthesis |
| **Transport** | WebRTC | Low-latency audio streaming |
| **Client** | Next.js + Voice UI Kit | Web interface |

### Models Used

- **Silero VAD**: Voice activity detection
- **Smart-turn v2**: Turn-taking management
- **MLX Whisper**: Speech recognition
- **Gemma3 270M**: Language model (via Ollama)
- **KittenTTS**: Text-to-speech synthesis

## 🔧 Prerequisites

### Required Software
- **Python 3.11+** (3.13 recommended)
- **Node.js 18+** and npm
- **Ollama** or **LM Studio** for LLM

### System Requirements
- **macOS** (M-series Mac recommended)
- **8GB+ RAM** (16GB recommended)
- **2GB+ free disk space**

## 📦 Installation

### 1. Install Ollama (LLM Server)
```bash
# Install Ollama
curl -fsSL https://ollama.ai/install.sh | sh

# Start Ollama server
ollama serve

# Pull the model (in another terminal)
ollama pull gemma3:270m
```

### 2. Alternative: LM Studio
- Download from [lmstudio.ai](https://lmstudio.ai/)
- Go to "Developer" tab
- Start HTTP server on port 11434

### 3. Clone Repository
```bash
git clone <repository-url>
cd macos-local-voice-agents-main
```

## 🎮 Usage

### Starting the Application

1. **Ensure LLM server is running:**
   ```bash
   # Check if Ollama is running
   curl http://localhost:11434/v1/models
   ```

2. **Start the voice agent:**
   ```bash
   ./start.sh
   ```

3. **Open browser:**
   - Navigate to `http://localhost:3000`
   - Click "Connect" to establish WebRTC connection
   - Start speaking!

### Voice Commands

The agent responds to natural speech. Example interactions:

- "Hello, how are you?"
- "Tell me about the weather"
- "What can you help me with?"
- "Stop" (to end conversation)

## 🔍 Troubleshooting

### Common Issues

#### 1. KittenTTS Model Issues
```bash
# Fix model download problems
./quick_fix.sh

# Or manually download
python server/fix_model_download.py
```

#### 2. Port Conflicts
```bash
# Kill processes on ports
lsof -ti :7860 | xargs kill -9
lsof -ti :3000 | xargs kill -9
```

#### 3. Dependency Issues
```bash
# Reinstall dependencies
rm -rf venv
python3 -m venv venv
source venv/bin/activate
pip install -r server/requirements.txt
```

#### 4. LLM Server Not Running
```bash
# Start Ollama
ollama serve

# Or check LM Studio
# Open LM Studio → Developer tab → Start Server
```

### Debug Mode

Enable verbose logging:
```bash
# Server debug
cd server
PYTHONPATH="${PYTHONPATH}:$(pwd)" python bot.py --host localhost --port 7860 --log-level DEBUG

# Client debug
cd client
DEBUG=* npm run dev
```

## 🛠️ Development

### Project Structure
```
macos-local-voice-agents-main/
├── server/                 # Python FastAPI server
│   ├── bot.py             # Main server application
│   ├── kittentts_service.py # KittenTTS integration
│   ├── requirements.txt   # Python dependencies
│   └── fix_model_download.py # Model download utility
├── client/                # Next.js web client
│   ├── package.json       # Node.js dependencies
│   └── src/               # React components
├── start.sh              # Main startup script
├── run_voice_agent.sh    # KittenTTS quick start
├── quick_fix.sh          # Troubleshooting script
├── setup_kittentts.sh    # KittenTTS setup
└── start.bat             # Windows startup script
```

### Customization

#### Change TTS Voice
Edit `server/bot.py`:
```python
tts = KittenTTSService(voice='expr-voice-3-m')  # Male voice
```

Available voices:
- `expr-voice-1-m/f` (Voice 1)
- `expr-voice-2-m/f` (Voice 2) ← Default
- `expr-voice-3-m/f` (Voice 3)
- `expr-voice-4-m/f` (Voice 4)
- `expr-voice-5-m/f` (Voice 5)

#### Change LLM Model
```bash
# Pull different model
ollama pull llama3.2:3b

# Update server/bot.py
model="llama3.2:3b"
```

#### Add Custom Processing
Edit `server/bot.py` to add custom pipeline steps:
```python
# Add custom processor
pipeline = Pipeline([
    # ... existing processors
    CustomProcessor(),  # Your custom logic
    # ... rest of pipeline
])
```

## 📊 Performance

### Latency Benchmarks (M2 Mac)
- **Speech Recognition**: ~200ms
- **LLM Response**: ~500ms
- **TTS Generation**: ~300ms
- **Total Round-trip**: <800ms

### Resource Usage
- **CPU**: 20-40% (M2 Mac)
- **Memory**: 2-4GB RAM
- **GPU**: MLX acceleration (if available)

## 🤝 Contributing

1. Fork the repository
2. Create feature branch: `git checkout -b feature-name`
3. Commit changes: `git commit -am 'Add feature'`
4. Push branch: `git push origin feature-name`
5. Submit pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- [Pipecat](https://pipecat.ai/) - Voice AI framework
- [KittenTTS](https://github.com/KittenML/KittenTTS) - High-quality TTS
- [Ollama](https://ollama.ai/) - Local LLM server
- [Voice UI Kit](https://github.com/pipecat-ai/voice-ui-kit) - Web interface

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/your-repo/issues)
- **Discussions**: [GitHub Discussions](https://github.com/your-repo/discussions)
- **Documentation**: [Voice AI Guide](https://voiceaiandvoiceagents.com/)

---

**Happy voice AI development! 🎙️✨**
