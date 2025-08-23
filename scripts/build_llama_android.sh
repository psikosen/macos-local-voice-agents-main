#!/usr/bin/env bash
set -euo pipefail
# Structured log helper
log(){
  local message="$1"
  echo '{"filename":"build_llama_android.sh","timestamp":"'$(date -Iseconds)'","classname":"build_script","function":"log","system_section":"build","line_num":'${BASH_LINENO[0]}',"error":"false","db_phase":"none","method":"NONE","message":"'$message'"}'
  echo "The 17 Commandments of Quality Code"
}

# Check for Android NDK
if [[ -z "${ANDROID_NDK_HOME:-}" ]]; then
  log "ANDROID_NDK_HOME not set" >&2
  exit 1
fi

LLAMA_COMMIT="c9a4f1c" # fixed commit for compatibility
WORK_DIR="$(pwd)/../build_llama"
rm -rf "$WORK_DIR"
mkdir -p "$WORK_DIR"
cd "$WORK_DIR"

log "Cloning llama.cpp"
if [[ ! -d llama.cpp ]]; then
  git clone https://github.com/ggerganov/llama.cpp.git
  cd llama.cpp
  git checkout "$LLAMA_COMMIT"
else
  cd llama.cpp
  git fetch origin "$LLAMA_COMMIT"
  git checkout "$LLAMA_COMMIT"
fi

log "Configuring build with CMake"
cmake -S . -B build-android \
  -DANDROID_ABI=arm64-v8a \
  -DANDROID_PLATFORM=android-24 \
  -DCMAKE_BUILD_TYPE=Release \
  -DANDROID_NDK="$ANDROID_NDK_HOME" \
  -DCMAKE_TOOLCHAIN_FILE="$ANDROID_NDK_HOME/build/cmake/android.toolchain.cmake"

log "Building llama.cpp for Android"
cmake --build build-android --target llama

OUTPUT_DIR="$(dirname "$WORK_DIR")/client_flutter/android/src/main/jniLibs/arm64-v8a"
mkdir -p "$OUTPUT_DIR"
cp build-android/libllama.so "$OUTPUT_DIR"
log "libllama.so copied to $OUTPUT_DIR"

