# Project Tasks

- [x] Review repository structure and existing documentation to understand current capabilities.
- [x] Capture current implementation status for voice pipeline and mobile endpoint.
- [x] Verify end-to-end voice agent startup on macOS/Linux, including Pipecat, Whisper, Ollama, and KittenTTS integration.
- [x] Expand automated test coverage for mobile audio endpoint and structured logging.
- [x] Document dependency versions and update installation instructions where necessary.

## Remake Tasks
- [x] Implement cached KittenTTS synthesis for the mobile endpoint with resilient error handling.
- [x] Add regression tests that validate KittenTTS WAV output and cache behavior.

## LlamaBridge Enhancements
- [x] Emit canonical structured logs with derived skepticism line from the Flutter bridge.
- [x] Support injectable HTTP clients and robust remote fallback handling in `LlamaBridge`.
- [x] Expand Flutter unit coverage for remote token streaming and HTTP error surfacing.

## Platform Scripts
- [x] Provide dedicated macOS setup/run scripts.
- [x] Provide dedicated Linux setup/run scripts.
