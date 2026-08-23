#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
RUNTIME="$ROOT/runtime"
CHECKOUT="$RUNTIME/ClearerVoice-Studio"
VENV="$RUNTIME/venv-macos-x86_64-py312"
LOCK="$RUNTIME/clearervoice-source.lock"
REMOTE="https://github.com/modelscope/ClearerVoice-Studio.git"

[[ "$(uname -s)" == Darwin ]] || { echo "ERROR: this installer is for macOS; use the documented manual Linux path." >&2; exit 2; }
[[ "$(uname -m)" == x86_64 ]] || { echo "ERROR: expected Intel macOS x86_64, got $(uname -m)." >&2; exit 2; }
command -v git >/dev/null || { echo "ERROR: git is required." >&2; exit 2; }
command -v python3.12 >/dev/null || { echo "ERROR: Python 3.12 is required. Install the python.org Intel universal2 build." >&2; exit 2; }
mkdir -p "$RUNTIME"

if [[ ! -d "$CHECKOUT/.git" ]]; then
  echo "Downloading ClearerVoice-Studio source…"
  git clone --filter=blob:none "$REMOTE" "$CHECKOUT"
fi

if [[ -s "$LOCK" ]]; then
  REVISION="$(cat "$LOCK")"
  git -C "$CHECKOUT" fetch origin "$REVISION"
  git -C "$CHECKOUT" checkout --detach "$REVISION"
else
  git -C "$CHECKOUT" fetch origin main
  git -C "$CHECKOUT" checkout --detach origin/main
  git -C "$CHECKOUT" rev-parse HEAD > "$LOCK"
  echo "Locked reviewed source commit $(cat "$LOCK")"
fi

[[ -f "$CHECKOUT/LICENSE" ]] || { echo "ERROR: upstream LICENSE is missing; refusing installation." >&2; exit 3; }
python3.12 -m venv "$VENV"
"$VENV/bin/python" -m pip install --upgrade 'pip==24.3.1' 'setuptools==75.6.0' 'wheel==0.45.1'
"$VENV/bin/python" -m pip install 'numpy==1.26.4' 'torch==2.2.2' 'torchaudio==2.2.2'
if [[ -f "$CHECKOUT/requirements.txt" ]]; then
  "$VENV/bin/python" -m pip install -c "$ROOT/scripts/macos-constraints.txt" -r "$CHECKOUT/requirements.txt"
fi
"$VENV/bin/python" -m pip install -e "$ROOT"

COMMIT="$(git -C "$CHECKOUT" rev-parse HEAD)"
LICENSE_SHA="$($VENV/bin/python -c 'import hashlib,sys;print(hashlib.sha256(open(sys.argv[1],"rb").read()).hexdigest())' "$CHECKOUT/LICENSE")"
cat > "$RUNTIME/source-provenance.json" <<EOF
{"repository":"$REMOTE","commit":"$COMMIT","license_path":"$CHECKOUT/LICENSE","license_sha256":"$LICENSE_SHA"}
EOF
echo "ClearerVoice runtime installed. Source provenance: $RUNTIME/source-provenance.json"
