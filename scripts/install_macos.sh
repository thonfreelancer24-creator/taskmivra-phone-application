#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
RUNTIME="$ROOT/runtime"
SPEX_HOME="$RUNTIME/spex-plus"
SOURCE="$SPEX_HOME/ClearerVoice-Studio"
VENV="$RUNTIME/venv-macos-x86_64-py312"
SOURCE_LOCK="$RUNTIME/clearervoice-source.lock"
SOURCE_REMOTE="https://github.com/modelscope/ClearerVoice-Studio.git"
CONFIG_NAME="config_wsj0-2mix_speech_SpEx-plus_2spk.yaml"

[[ "$(uname -s)" == Darwin ]] || { echo "ERROR: this installer is for macOS." >&2; exit 2; }
[[ "$(uname -m)" == x86_64 ]] || { echo "ERROR: expected Intel macOS x86_64, got $(uname -m)." >&2; exit 2; }
command -v python3.12 >/dev/null || { echo "ERROR: Python 3.12 is required." >&2; exit 2; }
command -v git >/dev/null || { echo "ERROR: git is required." >&2; exit 2; }
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

python3.12 -m venv "$VENV"
"$VENV/bin/python" -m pip install --upgrade 'pip==24.3.1' 'setuptools==75.6.0' 'wheel==0.45.1'
# Direct inference dependencies only; no ClearVoice training requirements file.
"$VENV/bin/python" -m pip install -c "$ROOT/scripts/macos-constraints.txt" \
  'numpy==1.26.4' 'torch==2.2.2' 'torchaudio==2.2.2' 'PyYAML==6.0.2' 'huggingface_hub==0.24.7'
# Released MossFormer2_SR_48K inference runtime only (not training requirements).
"$VENV/bin/python" -m pip install 'modelscope==1.20.0' 'scipy==1.13.1' 'soundfile==0.12.1' 'librosa==0.10.2.post1' 'kaldiio==2.18.0'
"$VENV/bin/python" -m pip install -e "$ROOT"
if [[ ! -s "$SPEX_HOME/$CONFIG_NAME" || ! -s "$SPEX_HOME/last_best_checkpoint.pt" ]]; then
  "$VENV/bin/python" "$ROOT/scripts/download_released_models.py" --destination "$SPEX_HOME"
fi

export CRYSTAL_VOICE_SPEX_HOME="$SPEX_HOME"
export CRYSTAL_VOICE_CHECKPOINT_LOCK="$RUNTIME/spex-assets.lock.json"
export CRYSTAL_VOICE_PROVENANCE="$RUNTIME/provenance.json"
export CRYSTAL_VOICE_SELFTEST_REPORT="$RUNTIME/startup-self-test.json"
export CRYSTAL_VOICE_SR_HOME="$SOURCE"
export MODELSCOPE_CACHE="$RUNTIME/model-cache"
export CRYSTAL_VOICE_SR_LOCK="$RUNTIME/mossformer2-sr-assets.lock.json"
export CRYSTAL_VOICE_SR_PROVENANCE="$RUNTIME/mossformer2-sr-provenance.json"
"$VENV/bin/python" - <<'PY'
from crystal_voice.adapters.restoration import SpExPlusMossFormerSRAdapter
from crystal_voice.selftest import run_startup_self_test
adapter = SpExPlusMossFormerSRAdapter()
adapter.load()
report = run_startup_self_test(adapter)
print("Real SpEx+ plus MossFormer2_SR_48K startup self-test passed:", report)
PY
echo "Direct SpEx+ installed and verified. See $RUNTIME/provenance.json"
