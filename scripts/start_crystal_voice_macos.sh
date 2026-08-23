#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
"$ROOT/scripts/install_macos.sh"
VENV="$ROOT/runtime/venv-macos-x86_64-py312"
export CRYSTAL_VOICE_CLEARERVOICE_HOME="$ROOT/runtime/ClearerVoice-Studio"
export CRYSTAL_VOICE_PROVENANCE="$ROOT/runtime/provenance.json"
export CRYSTAL_VOICE_CHECKPOINT_LOCK="$ROOT/runtime/checkpoint-assets.lock.json"
export MODELSCOPE_CACHE="$ROOT/runtime/model-cache"
export TORCH_HOME="$ROOT/runtime/torch-cache"
PORT="${CRYSTAL_VOICE_PORT:-8765}"
LOG="$ROOT/runtime/crystal-voice.log"

"$VENV/bin/crystal-voice" ui --adapter spexplus --port "$PORT" >"$LOG" 2>&1 &
PID=$!
trap 'kill "$PID" 2>/dev/null || true' EXIT INT TERM
echo "Loading SpEx+ and verifying checkpoint; this can take several minutes on first run…"
for _ in $(seq 1 600); do
  if ! kill -0 "$PID" 2>/dev/null; then
    echo "ERROR: Crystal Voice failed to start:" >&2
    cat "$LOG" >&2
    exit 4
  fi
  if curl -fsS "http://127.0.0.1:$PORT/api/status" >/dev/null 2>&1; then
    echo "Model ready. Provenance: $CRYSTAL_VOICE_PROVENANCE"
    open "http://127.0.0.1:$PORT"
    wait "$PID"
    exit $?
  fi
  sleep 1
done
echo "ERROR: model did not become ready in 10 minutes. See $LOG" >&2
exit 5
