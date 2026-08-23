#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
RUNTIME="$ROOT/runtime"
SPEX_HOME="$RUNTIME/spex-plus"
SOURCE="$SPEX_HOME/ClearerVoice-Studio"
VENV="$RUNTIME/venv-macos-x86_64-py312"
SOURCE_LOCK="$RUNTIME/clearervoice-source.lock"
SOURCE_REMOTE="https://github.com/modelscope/ClearerVoice-Studio.git"
MODEL_BASE="https://www.modelscope.cn/models/alibabasglab/log_wsj0-2mix_speech_SpEx-plus_2spk/resolve/master"
CONFIG_NAME="config_wsj0-2mix_speech_SpEx-plus_2spk.yaml"

[[ "$(uname -s)" == Darwin ]] || { echo "ERROR: this installer is for macOS." >&2; exit 2; }
[[ "$(uname -m)" == x86_64 ]] || { echo "ERROR: expected Intel macOS x86_64, got $(uname -m)." >&2; exit 2; }
command -v python3.12 >/dev/null || { echo "ERROR: Python 3.12 is required." >&2; exit 2; }
command -v git >/dev/null || { echo "ERROR: git is required." >&2; exit 2; }
command -v curl >/dev/null || { echo "ERROR: curl is required." >&2; exit 2; }
mkdir -p "$SPEX_HOME"

if [[ ! -d "$SOURCE/.git" ]]; then git clone --filter=blob:none "$SOURCE_REMOTE" "$SOURCE"; fi
if [[ -s "$SOURCE_LOCK" ]]; then
  REVISION="$(cat "$SOURCE_LOCK")"
  git -C "$SOURCE" fetch origin "$REVISION"
  git -C "$SOURCE" checkout --detach "$REVISION"
else
  git -C "$SOURCE" fetch origin main
  git -C "$SOURCE" checkout --detach origin/main
  git -C "$SOURCE" rev-parse HEAD > "$SOURCE_LOCK"
fi
ARCH="$SOURCE/train/target_speaker_extraction/models/SpEx_plus/SpEx_plus.py"
[[ -f "$SOURCE/LICENSE" && -f "$ARCH" ]] || { echo "ERROR: Apache license or direct SpEx+ architecture missing." >&2; exit 3; }

download() {
  local name="$1" destination="$2"
  [[ -s "$destination" ]] && return
  echo "Downloading released $name…"
  curl --fail --location --retry 3 --output "$destination.part" "$MODEL_BASE/$name"
  mv "$destination.part" "$destination"
}
download "$CONFIG_NAME" "$SPEX_HOME/$CONFIG_NAME"
download "last_best_checkpoint.pt" "$SPEX_HOME/last_best_checkpoint.pt"

python3.12 -m venv "$VENV"
"$VENV/bin/python" -m pip install --upgrade 'pip==24.3.1' 'setuptools==75.6.0' 'wheel==0.45.1'
# Direct inference dependencies only; no ClearVoice training requirements file.
"$VENV/bin/python" -m pip install -c "$ROOT/scripts/macos-constraints.txt" \
  'numpy==1.26.4' 'torch==2.2.2' 'torchaudio==2.2.2' 'PyYAML==6.0.2'
"$VENV/bin/python" -m pip install -e "$ROOT"

export CRYSTAL_VOICE_SPEX_HOME="$SPEX_HOME"
export CRYSTAL_VOICE_CHECKPOINT_LOCK="$RUNTIME/spex-assets.lock.json"
export CRYSTAL_VOICE_PROVENANCE="$RUNTIME/provenance.json"
export CRYSTAL_VOICE_SELFTEST_REPORT="$RUNTIME/startup-self-test.json"
"$VENV/bin/python" - <<'PY'
from crystal_voice.adapters.clearervoice import ClearerVoiceSpExPlusAdapter
from crystal_voice.selftest import run_startup_self_test
adapter = ClearerVoiceSpExPlusAdapter()
adapter.load()
report = run_startup_self_test(adapter)
print("Real direct SpEx+ startup self-test passed:", report)
PY
echo "Direct SpEx+ installed and verified. See $RUNTIME/provenance.json"
