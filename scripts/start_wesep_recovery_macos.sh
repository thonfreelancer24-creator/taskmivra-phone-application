#!/usr/bin/env bash
set -euo pipefail

ROOT="${TASKMIVRA_ROOT:-$(cd "$(dirname "$0")/.." && pwd)}"
VENV="$ROOT/runtime/venv-macos-x86_64-py312"
WESEP_HOME="$ROOT/runtime/wesep"
WESEP_REVISION="99eca54b60300d39b9353d93cf285a14bba37854"
WESEP_REMOTE="https://github.com/wenet-e2e/wesep.git"
WESPEAKER_HOME="$ROOT/runtime/wespeaker"
WESPEAKER_REVISION="58071902625ae6b072befda2932a38e9b38d5f26"
WESPEAKER_REMOTE="https://github.com/wenet-e2e/wespeaker.git"
RECOVERY_BASE="https://raw.githubusercontent.com/thonfreelancer24-creator/taskmivra-phone-application/codex/crystal-voice-wesep-quality-gate"
PORT="${CRYSTAL_VOICE_PORT:-8768}"
LOG="$ROOT/runtime/crystal-voice-wesep.log"

[[ "$(uname -s)" == Darwin ]] || { echo "ERROR: this recovery launcher is for macOS." >&2; exit 2; }
[[ -x "$VENV/bin/python" ]] || { echo "ERROR: Crystal Voice environment is missing in $ROOT/runtime. Use the working folder 4." >&2; exit 2; }
command -v git >/dev/null || { echo "ERROR: git is required." >&2; exit 2; }
command -v curl >/dev/null || { echo "ERROR: curl is required." >&2; exit 2; }
mkdir -p "$ROOT/crystal_voice/adapters" "$ROOT/runtime"

# Patch only the recovery adapter registry into the already-working folder.
curl -fsSL "$RECOVERY_BASE/crystal_voice/adapters/wesep_native.py" -o "$ROOT/crystal_voice/adapters/wesep_native.py"
curl -fsSL "$RECOVERY_BASE/crystal_voice/adapters/__init__.py" -o "$ROOT/crystal_voice/adapters/__init__.py"

if [[ ! -d "$WESEP_HOME/.git" ]]; then
  rm -rf "$WESEP_HOME"
  git clone --filter=blob:none "$WESEP_REMOTE" "$WESEP_HOME"
fi
git -C "$WESEP_HOME" fetch origin "$WESEP_REVISION"
git -C "$WESEP_HOME" checkout --detach "$WESEP_REVISION"

if [[ ! -d "$WESPEAKER_HOME/.git" ]]; then
  rm -rf "$WESPEAKER_HOME"
  git clone --filter=blob:none "$WESPEAKER_REMOTE" "$WESPEAKER_HOME"
fi
git -C "$WESPEAKER_HOME" fetch origin "$WESPEAKER_REVISION"
git -C "$WESPEAKER_HOME" checkout --detach "$WESPEAKER_REVISION"

# WeSep only needs wespeaker.models.* for its embedded speaker encoder. The
# upstream wespeaker package initializer imports the diarization CLI, which
# unnecessarily requires umap/hdbscan. Neutralize that top-level side effect
# while leaving the model source itself untouched.
printf '%s\n' '# TaskMivra Crystal Voice recovery: model-only WeSpeaker import surface.' > "$WESPEAKER_HOME/wespeaker/__init__.py"

# Keep the already verified Intel-Mac torch/torchaudio foundation. Install only
# the runtime pieces required by the released WeSep BSRNN-ECAPA path.
"$VENV/bin/python" -m pip install \
  'kaldiio==2.18.0' 'silero-vad==5.1.2' 'soundfile==0.12.1'
"$VENV/bin/python" -m pip install --no-deps -e "$WESPEAKER_HOME"
"$VENV/bin/python" -m pip install --no-deps -e "$WESEP_HOME"
"$VENV/bin/python" -m pip install -e "$ROOT"

# Fail here with a focused model-load message rather than later in the server.
"$VENV/bin/python" - <<'PY'
from wespeaker.models.speaker_model import get_speaker_model
import wesep
assert callable(get_speaker_model)
model = wesep.load_model("english")
model.set_device("cpu")
model.set_vad(False)
model.set_output_norm(False)
print("WeSep English BSRNN-ECAPA model ready with model-only WeSpeaker.")
PY

"$VENV/bin/crystal-voice" ui --adapter wesep-native --port "$PORT" >"$LOG" 2>&1 &
PID=$!
trap 'kill "$PID" 2>/dev/null || true' EXIT INT TERM

echo "Starting Crystal Voice recovery gate with WeSep on http://127.0.0.1:$PORT"
for _ in $(seq 1 600); do
  if ! kill -0 "$PID" 2>/dev/null; then
    echo "ERROR: WeSep recovery server failed to start:" >&2
    cat "$LOG" >&2
    exit 4
  fi
  if curl -fsS "http://127.0.0.1:$PORT/api/status" >/dev/null 2>&1; then
    echo "WeSep recovery model ready."
    open "http://127.0.0.1:$PORT"
    wait "$PID"
    exit $?
  fi
  sleep 1
done

echo "ERROR: WeSep model did not become ready in 10 minutes. See $LOG" >&2
exit 5
