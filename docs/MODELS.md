# Model provenance and integration status

No weights or upstream source code are redistributed by this milestone. The direct SpEx+ adapter refuses readiness unless the exact architecture, released YAML, and released checkpoint exist, hash successfully, and load strictly. Mixture and enrollment tensors are passed directly into the network; there is no blind separation or speaker selection stage.

| Adapter | Upstream | Code license reported by upstream | Checkpoint status | Milestone decision |
|---|---|---|---|---|
| Direct SpEx+ (`log_wsj0-2mix_speech_SpEx-plus_2spk`) | Architecture at `modelscope/ClearerVoice-Studio/train/target_speaker_extraction/models/SpEx_plus/SpEx_plus.py`; released model at `alibabasglab/log_wsj0-2mix_speech_SpEx-plus_2spk` | Apache-2.0 upstream license | Exact YAML and `last_best_checkpoint.pt` are downloaded and individually SHA-256 locked | 8 kHz isolation benchmark only; never final high-fidelity output |
| MossFormer2 speech SR | Released ClearerVoice `MossFormer2_SR_48K` | Upstream license and checkpoint must be recorded by the optional runtime | Optional candidate after direct SpEx+ | Must beat SpEx+ alone without artificial/metallic/distorted sound or identity regression |
| WeSep reference-conditioned TSE | `https://github.com/wenet-e2e/wesep` | Apache-2.0 repository license | Not vendored; checkpoint-specific provenance/license must be reviewed | Independent candidate adapter implemented; evaluation blocked until a reviewed local checkout and checkpoint are supplied |
| Same-take diagnostic | TaskMivra milestone source | Project source terms | No weights | Plumbing only; explicitly ineligible for acceptance |

## Evidence and blocker

On 2026-08-22 the cloud development environment could not reach GitHub or ModelScope. The target installer therefore downloads on the Intel Mac, locks the architecture repository commit, and writes individual SHA-256 values for `SpEx_plus.py`, `config_wsj0-2mix_speech_SpEx-plus_2spk.yaml`, and `last_best_checkpoint.pt`. Every later startup refuses readiness if name, size, or hash differs. The loader also verifies `audio_sr: 8000`, `ref_sr: 8000`, the presence of `checkpoint["model"]`, and strict state-dictionary compatibility before inference.

Repository licensing does **not** automatically establish permission to redistribute every checkpoint or dataset derivative. Before evaluation, record the upstream commit, checkpoint filename, SHA-256, download page, model-card license, training-data provenance, framework versions, sample rate, and command below in a local evaluation record.

## Intel macOS acquisition and launch

```bash
./scripts/start_crystal_voice_macos.sh
```

The launcher requires macOS x86_64 and Python 3.12 and uses a unique clean venv. It imports the direct upstream SpEx+ network, constructs it from the released YAML, strictly loads `checkpoint["model"]`, and runs a deterministic mixture/reference self-test before starting the UI. Exact errors remain in `runtime/crystal-voice.log`. It installs only NumPy, Torch, Torchaudio, PyYAML, and this application—not the ClearVoice training dependency stack.

The adapter explicitly converts microphone PCM from 48 kHz to the released model's 8 kHz rate with a 48-tap Hann-windowed sinc anti-aliasing filter, feeds mixture and 3–5 second reference tensors directly into SpEx+, and resamples the unnormalized extraction back to 48 kHz. It applies no spectral suppression or neural cleanup. Because information above 4 kHz is absent internally, this output is an isolation benchmark only.

Compare narrow-band extraction against the optional released 48 kHz restoration candidate with:

```bash
crystal-voice compare-restoration --output artifacts/restoration
```

The comparison rejects restoration for clipping, duration drift, machine artifact-gate failure, or target-correlation regression beyond 0.02. Human listening for artificial, metallic, distorted, or identity-changing sound remains mandatory.
