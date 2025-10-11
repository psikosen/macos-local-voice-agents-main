#!/bin/bash

# Exit immediately on unbound variables
set -u

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Detect host operating system
OS_NAME="$(uname -s)"
IS_MAC=false
IS_LINUX=false
case "$OS_NAME" in
    Darwin)
        IS_MAC=true
        ;;
    Linux)
        IS_LINUX=true
        ;;
esac

SERVER_PID=""
CLIENT_PID=""

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to check if port is in use
port_in_use() {
    local port=$1
    if command_exists lsof; then
        lsof -i :"$port" >/dev/null 2>&1
    elif command_exists ss; then
        ss -ltn "sport = :$port" >/dev/null 2>&1
    else
        return 1
    fi
}

# Function to kill process on port
kill_port() {
    local port=$1
    if port_in_use "$port"; then
        print_warning "Port $port is in use. Attempting to kill existing process..."
        if command_exists lsof; then
            lsof -ti :"$port" | xargs kill -9 2>/dev/null || true
        elif command_exists fuser; then
            fuser -k "$port"/tcp 2>/dev/null || true
        fi
        sleep 2
    fi
}

# Function to setup Python virtual environment
setup_python_env() {
    local venv_dir="venv"
    
    if [ ! -d "$venv_dir" ]; then
        print_status "Creating Python virtual environment..."
        python3 -m venv "$venv_dir"
        print_success "Virtual environment created successfully"
    else
        print_status "Virtual environment already exists"
    fi
    
    print_status "Activating virtual environment..."
    source "$venv_dir/bin/activate"
    
    print_status "Upgrading pip and wheel..."
    pip install --upgrade pip wheel

    print_status "Installing Python dependencies..."
    if pip install -r server/requirements.txt; then
        print_success "Python dependencies installed successfully"
    else
        print_warning "Bulk install failed, retrying with common packages..."
        pip install python-dotenv fastapi uvicorn opencv-python nltk aiortc || true
        pip install -r server/requirements.txt || true
    fi

    if $IS_MAC; then
        print_status "Ensuring MLX runtime is available..."
        pip install "mlx>=0.25.0" "mlx-lm>=0.19.0,<0.24.0" mlx-audio==0.2.0 --no-deps \
            || print_warning "MLX packages installation failed; voice quality may be reduced"
    elif $IS_LINUX; then
        print_status "Ensuring Linux speech dependencies are available..."
        pip install "faster-whisper>=1.0.0" "ctranslate2>=4.3" || \
            print_warning "Could not install faster-whisper; install manually for best accuracy"
    fi

    print_success "Python environment setup complete"
}

# Function to setup Node.js environment
setup_node_env() {
    print_status "Installing Node.js dependencies..."
    cd client
    npm install
    cd ..
    print_success "Node.js environment setup complete"
}

# Ensure required models are downloaded and cached
ensure_models() {
    print_status "Ensuring required models are cached..."
    mkdir -p logs
    if python server/download_kittentts_model.py >> logs/model_download.log 2>&1; then
        print_success "Model cache ready"
    else
        print_warning "Model download failed; see logs/model_download.log"
    fi
}

# Function to start the server
start_server() {
    print_status "Starting server on port 7860..."
    cd server
    source ../venv/bin/activate
    
    # Check if the server can import required modules
    print_status "Checking server dependencies..."
    if ! PYTHONPATH="${PYTHONPATH}:$(pwd)" python -c "import kokoro_tts; print('Dependencies OK')" 2>/dev/null; then
        print_warning "Server dependencies have issues, but attempting to start anyway..."
    fi
    
    # Add current directory to Python path to fix import issues
    PYTHONPATH="${PYTHONPATH}:$(pwd)" python bot.py --host localhost --port 7860 &
    SERVER_PID=$!
    cd ..
    
    # Wait a moment and check if server is still running
    sleep 2
    if kill -0 $SERVER_PID 2>/dev/null; then
        print_success "Server started with PID: $SERVER_PID"
    else
        print_error "Server failed to start properly"
        return 1
    fi
}

# Function to start the client
start_client() {
    print_status "Starting client on port 3000..."
    cd client
    npm run dev &
    CLIENT_PID=$!
    cd ..
    
    # Wait a moment and check if client is still running
    sleep 3
    if kill -0 $CLIENT_PID 2>/dev/null; then
        print_success "Client started with PID: $CLIENT_PID"
    else
        print_error "Client failed to start properly"
        return 1
    fi
}

# Function to check service health
check_services() {
    print_status "Checking service health..."
    
    # Check if ports are responding
    local server_ok=false
    local client_ok=false
    
    # Wait up to 10 seconds for services to be ready
    for i in {1..10}; do
        if curl -s http://localhost:7860 >/dev/null 2>&1; then
            server_ok=true
        fi
        if curl -s http://localhost:3000 >/dev/null 2>&1; then
            client_ok=true
        fi
        
        if $server_ok && $client_ok; then
            break
        fi
        sleep 1
    done
    
    if $server_ok; then
        print_success "Server is responding on port 7860"
    else
        print_warning "Server may not be fully ready on port 7860"
    fi
    
    if $client_ok; then
        print_success "Client is responding on port 3000"
    else
        print_warning "Client may not be fully ready on port 3000"
    fi
}

# Function to cleanup on exit
cleanup() {
    print_status "Shutting down services..."
    if [ -n "${SERVER_PID}" ]; then
        kill "$SERVER_PID" 2>/dev/null || true
        print_status "Server stopped"
    fi
    if [ -n "${CLIENT_PID}" ]; then
        kill "$CLIENT_PID" 2>/dev/null || true
        print_status "Client stopped"
    fi
    exit 0
}

# Set trap to cleanup on script exit
trap cleanup SIGINT SIGTERM EXIT

# Main execution
main() {
    print_status "Starting macOS Local Voice Agents..."
    
    # Check if required tools are installed
    if ! command_exists python3; then
        print_error "Python 3 is not installed. Please install Python 3 first."
        exit 1
    fi
    
    if ! command_exists node; then
        print_error "Node.js is not installed. Please install Node.js first."
        exit 1
    fi
    
    if ! command_exists npm; then
        print_error "npm is not installed. Please install npm first."
        exit 1
    fi
    
    # Kill any existing processes on our ports
    kill_port 7860
    kill_port 3000
    
    # Setup environments
    setup_python_env
    setup_node_env

    # Ensure required models are downloaded
    ensure_models

    # Start services
    if start_server; then
        print_status "Server startup completed"
    else
        print_error "Server failed to start, but continuing with client..."
    fi
    
    # Wait a moment for server to initialize
    sleep 3
    
    if start_client; then
        print_status "Client startup completed"
    else
        print_error "Client failed to start"
        exit 1
    fi
    
    # Check service health
    check_services
    
    print_success "Application started successfully!"
    print_status "Server running at: http://localhost:7860"
    print_status "Client running at: http://localhost:3000"
    print_status "Press Ctrl+C to stop all services"
    
    # Wait for user to stop
    wait
}

# Run main function
main
