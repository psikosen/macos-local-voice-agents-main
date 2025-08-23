@echo off
setlocal enabledelayedexpansion

REM Colors for output (Windows doesn't support ANSI colors by default, but we'll use them for modern terminals)
set "RED=[91m"
set "GREEN=[92m"
set "YELLOW=[93m"
set "BLUE=[94m"
set "NC=[0m"

REM Function to print colored output
:print_status
echo %BLUE%[INFO]%NC% %~1
goto :eof

:print_success
echo %GREEN%[SUCCESS]%NC% %~1
goto :eof

:print_warning
echo %YELLOW%[WARNING]%NC% %~1
goto :eof

:print_error
echo %RED%[ERROR]%NC% %~1
goto :eof

REM Function to check if command exists
:command_exists
where %1 >nul 2>&1
if %errorlevel% equ 0 (
    set "exists=1"
) else (
    set "exists=0"
)
goto :eof

REM Function to check if port is in use
:port_in_use
netstat -an | find ":%1 " >nul 2>&1
if %errorlevel% equ 0 (
    set "port_in_use=1"
) else (
    set "port_in_use=0"
)
goto :eof

REM Function to kill process on port
:kill_port
call :port_in_use %1
if !port_in_use! equ 1 (
    call :print_warning "Port %1 is in use. Attempting to kill existing process..."
    for /f "tokens=5" %%a in ('netstat -aon ^| find ":%1 "') do (
        taskkill /f /pid %%a >nul 2>&1
    )
    timeout /t 2 /nobreak >nul
)
goto :eof

REM Function to setup Python virtual environment
:setup_python_env
set "venv_dir=venv"

if not exist "%venv_dir%" (
    call :print_status "Creating Python virtual environment..."
    python -m venv "%venv_dir%"
    call :print_success "Virtual environment created successfully"
) else (
    call :print_status "Virtual environment already exists"
)

call :print_status "Activating virtual environment..."
call "%venv_dir%\Scripts\activate.bat"

call :print_status "Upgrading pip..."
python -m pip install --upgrade pip

call :print_status "Installing core dependencies first..."
pip install numpy>=2.0.0 torch

call :print_status "Installing Python dependencies..."
pip install -r server\requirements.txt
if %errorlevel% neq 0 (
    call :print_warning "Some dependencies failed, trying alternative approach..."
    pip install python-dotenv fastapi uvicorn opencv-python nltk aiortc
)

call :print_status "Installing mlx packages with compatible versions..."
pip install "mlx>=0.25.0" "mlx-lm>=0.19.0,<0.24.0"

call :print_status "Installing mlx-audio (may show warnings)..."
pip install mlx-audio==0.2.0 --no-deps
if %errorlevel% neq 0 (
    call :print_warning "mlx-audio installation failed, server may not work fully"
)
call :print_success "Python environment setup complete"
goto :eof

REM Function to setup Node.js environment
:setup_node_env
call :print_status "Installing Node.js dependencies..."
cd client
call npm install
cd ..
call :print_success "Node.js environment setup complete"
goto :eof

REM Function to start the server
:start_server
call :print_status "Starting server on port 7860..."
cd server
call ..\venv\Scripts\activate.bat
set "PYTHONPATH=%PYTHONPATH%;%CD%"
start /b python bot.py --host localhost --port 7860
set "SERVER_PID=%errorlevel%"
cd ..
call :print_success "Server started"
goto :eof

REM Function to start the client
:start_client
call :print_status "Starting client on port 3000..."
cd client
start /b npm run dev
set "CLIENT_PID=%errorlevel%"
cd ..
call :print_success "Client started"
goto :eof

REM Main execution
call :print_status "Starting macOS Local Voice Agents..."

REM Check if required tools are installed
call :command_exists python
if %exists% equ 0 (
    call :print_error "Python is not installed. Please install Python first."
    exit /b 1
)

call :command_exists node
if %exists% equ 0 (
    call :print_error "Node.js is not installed. Please install Node.js first."
    exit /b 1
)

call :command_exists npm
if %exists% equ 0 (
    call :print_error "npm is not installed. Please install npm first."
    exit /b 1
)

REM Kill any existing processes on our ports
call :kill_port 7860
call :kill_port 3000

REM Setup environments
call :setup_python_env
call :setup_node_env

REM Start services
call :start_server

REM Wait a moment for server to initialize
timeout /t 3 /nobreak >nul

call :start_client

call :print_success "Application started successfully!"
call :print_status "Server running at: http://localhost:7860"
call :print_status "Client running at: http://localhost:3000"
call :print_status "Press Ctrl+C to stop all services"

REM Wait for user to stop
pause
