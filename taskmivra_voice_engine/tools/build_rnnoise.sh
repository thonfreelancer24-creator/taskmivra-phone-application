#!/usr/bin/env bash
set -euo pipefail

# Pinned commercial-safe RNNoise source. Its BSD-style COPYING file must ship
# with any TaskMivra binary that redistributes this library.
RNNOISE_COMMIT="6cbfd53eb348a8d394e0757b4025c6ded34eb2b6"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DST="$ROOT/third_party/rnnoise"
SRC="$DST/src"
PREFIX="$DST/runtime"

rm -rf "$SRC" "$PREFIX"
mkdir -p "$DST"
git clone https://github.com/xiph/rnnoise.git "$SRC"
git -C "$SRC" checkout --detach "$RNNOISE_COMMIT"
ACTUAL="$(git -C "$SRC" rev-parse HEAD)"
[[ "$ACTUAL" == "$RNNOISE_COMMIT" ]] || { echo "STOP: RNNoise commit mismatch"; exit 2; }
cp "$SRC/COPYING" "$DST/COPYING"
(
  cd "$SRC"
  ./autogen.sh
  ./configure --prefix="$PREFIX" --disable-examples --disable-doc
  make -j2
  make install
)
echo "$RNNOISE_COMMIT" > "$DST/PINNED-COMMIT.txt"
echo "RNNoise built at $PREFIX"
echo "Set TASKMIVRA_RNNOISE_LIB to the produced librnnoise path if auto-discovery does not find it."
