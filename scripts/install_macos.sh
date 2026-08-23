#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
RUNTIME="$ROOT/runtime"
SPEX_HOME="$RUNTIME/spex-plus"
SOURCE="$SPEX_HOME/ClearerVoice-Studio"
VENV="$RUNTIME/venv-macos-x86_64-py312"
SOURCE_LOCK="$RUNTIME/clearervoice-source.lock"
SOURCE_REMOTE="https://github.com/modelscope/ClearerVoice-Studio.git"
SOURCE_REVISION="6b3774dc79c46ae8bed2a4fa5f706f0ac8c75c61"
CONFIG_NAME="config_wsj0-2mix_speech_SpEx-plus_2spk.yaml"
SR_CHECKPOINT_DIR="$RUNTIME/checkpoints/MossFormer2_SR_48K"
SR_REPO="alibabasglab/MossFormer2_SR_48K"
SR_REVISION="main"

[[ "$(uname -s)" == Darwin ]] || { echo "ERROR: this installer is for macOS." >&2; exit 2; }
[[ "$(uname -m)" == x86_64 ]] || { echo "ERROR: expected Intel macOS x86_64, got $(uname -m)." >&2; exit 2; }
command -v python3.12 >/dev/null || { echo "ERROR: Python 3.12 is required." >&2; exit 2; }
command -v git >/dev/null || { echo "ERROR: git is required." >&2; exit 2; }
mkdir -p "$SPEX_HOME" "$SR_CHECKPOINT_DIR"

if [[ ! -d "$SOURCE/.git" ]]; then git clone --filter=blob:none "$SOURCE_REMOTE" "$SOURCE"; fi
if [[ -s "$SOURCE_LOCK" ]]; then
  REVISION="$(cat "$SOURCE_LOCK")"
else
  REVISION="$SOURCE_REVISION"
  printf '%s\n' "$REVISION" > "$SOURCE_LOCK"
fi
git -C "$SOURCE" fetch origin "$REVISION"
git -C "$SOURCE" checkout --detach "$REVISION"
ARCH="$SOURCE/train/target_speaker_extraction/models/SpEx_plus/SpEx_plus.py"
NETWORKS="$SOURCE/train/target_speaker_extraction/networks.py"
[[ -f "$SOURCE/LICENSE" && -f "$ARCH" && -f "$NETWORKS" ]] || { echo "ERROR: Apache license or direct SpEx+ source missing." >&2; exit 3; }

python3.12 -m venv "$VENV"
"$VENV/bin/python" -m pip install --upgrade 'pip==24.3.1' 'setuptools==75.6.0' 'wheel==0.45.1'
"$VENV/bin/python" -m pip install -c "$ROOT/scripts/macos-constraints.txt" \
  'numpy==1.26.4' 'torch==2.2.2' 'torchaudio==2.2.2' 'torchvision==0.17.2' \
  'PyYAML==6.0.2' 'huggingface_hub==0.27.1'
# Install the upstream inference package with its declared dependencies while keeping
# our Intel-macOS foundation pinned by constraints.
"$VENV/bin/python" -m pip install -c "$ROOT/scripts/macos-constraints.txt" "$SOURCE/clearvoice"
"$VENV/bin/python" -m pip install -e "$ROOT"

if [[ ! -s "$SPEX_HOME/$CONFIG_NAME" || ! -s "$SPEX_HOME/last_best_checkpoint.pt" ]]; then
  "$VENV/bin/python" "$ROOT/scripts/download_released_models.py" --destination "$SPEX_HOME"
fi

# Fetch only inference assets required by ClearVoice; do not download training discriminator weights.
if [[ ! -s "$SR_CHECKPOINT_DIR/last_best_checkpoint" || ! -s "$SR_CHECKPOINT_DIR/last_best_checkpoint_m.pt" || ! -s "$SR_CHECKPOINT_DIR/last_best_checkpoint_g.pt" ]]; then
  "$VENV/bin/python" - <<PY
from huggingface_hub import hf_hub_download
from pathlib import Path
repo = "$SR_REPO"
revision = "$SR_REVISION"
destination = Path("$SR_CHECKPOINT_DIR")
destination.mkdir(parents=True, exist_ok=True)
for name in ("last_best_checkpoint", "last_best_checkpoint_m.pt", "last_best_checkpoint_g.pt"):
    source = hf_hub_download(repo_id=repo, filename=name, revision=revision)
    target = destination / name
    target.write_bytes(Path(source).read_bytes())
PY
fi

export CRYSTAL_VOICE_SPEX_HOME="$SPEX_HOME"
export CRYSTAL_VOICE_CHECKPOINT_LOCK="$RUNTIME/spex-assets.lock.json"
export CRYSTAL_VOICE_PROVENANCE="$RUNTIME/provenance.json"
export CRYSTAL_VOICE_SELFTEST_REPORT="$RUNTIME/startup-self-test.json"
export CRYSTAL_VOICE_SR_HOME="$SOURCE"
export CRYSTAL_VOICE_SR_CHECKPOINT_DIR="$SR_CHECKPOINT_DIR"
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
echo "Direct SpEx+ and 48 kHz restoration installed and verified. See $RUNTIME/provenance.json"
