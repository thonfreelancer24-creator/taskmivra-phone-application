# TaskMivra Crystal Voice — SpEx+ offline milestone

This repository is an offline target-speaker extraction laboratory, not a shipped isolation engine. It provides a strict adapter contract, deterministic fixtures, objective pre-gates, same-take A/B artifacts, and a local enrollment/test UI. It contains no v3/v4 DSP, spectral mask, hard gate, denoiser stack, WebRTC, or carrier integration.

## Clean setup

Linux and Intel macOS use the dependency-free default path (only tests require pytest). Always create a fresh environment:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e . pytest==9.0.2
pytest -q
```

The core uses Python's standard library and requires no Rust/Cargo build. Model-specific PyTorch environments belong in reviewed upstream checkouts; for the known Intel Mac path, start with Torch/Torchaudio 2.2.2 and NumPy below 2 only after confirming wheels are still available for that machine.

## Run the reproducible laboratory

First validate all mechanics with the deliberately non-extracting diagnostic adapter:

```bash
crystal-voice benchmark --adapter diagnostic --output artifacts/diagnostic
open artifacts/diagnostic/report.html  # macOS; use xdg-open on Linux
```

Exit status 2 and `NOT ACCEPTED` are expected: a passthrough must never be mistaken for Crystal Voice quality. Six regimes produce Raw, Processed, and clean-target WAV files plus JSON/HTML reports.

After installing a real model as described in `docs/MODELS.md`:

```bash
crystal-voice benchmark --adapter spexplus --output artifacts/spexplus
crystal-voice benchmark --adapter wesep --output artifacts/wesep
```

## Local one-take UI

The server loads the selected adapter **before** announcing readiness and exposes exact errors if model startup or inference fails. It uses the unique milestone port 8765 and does not open a browser automatically:

On Intel macOS, the complete real-model path is one command:

```bash
./scripts/start_crystal_voice_macos.sh
```

It checks the host and Python version, creates a clean model-specific environment, acquires and locks the ClearerVoice source commit, installs pinned binary-friendly foundations, loads/downloads SpEx+, hashes source/license/checkpoint assets, waits for model readiness, and only then opens the browser. Subsequent runs verify and reuse the locked commit. Runtime records are written under ignored `runtime/`.

For plumbing inspection, `--adapter diagnostic` works but displays that its output is not reference-conditioned. The browser records PCM/WAV with browser audio enhancement disabled, uploads one challenge WAV once, and the server persists those exact bytes as Raw before processing. Both source IDs shown in results are the upload's SHA-256.

## Acceptance state and limitations

**No candidate is accepted by the cloud run yet.** The real persistent SpEx+ path is implemented, but this cloud's outbound tunnel prevented acquisition/execution of the upstream source and checkpoint. The Intel launcher solves acquisition on the target machine and writes exact runtime hashes. Mandatory music, TV, competing-speaker, fan/AC, keyboard, mixed-challenge listening and independent speaker-embedding/STOI/PESQ measurement must be run there. See `docs/QUALITY_GATES.md` for the distinction between machine rejection and human acceptance.

Do not begin streaming/WebRTC work until a reviewed, licensed model passes both synthetic pre-gates and every mandatory real listening scenario.
