# Model provenance and integration status

No weights or upstream source code are redistributed by this milestone. The laboratory refuses to describe a model as ready unless the operator explicitly configures its local inference command. Each command must receive **mixture**, **reference**, and **output** paths; this mechanically prevents an accidentally unconditioned inference path.

| Adapter | Upstream | Code license reported by upstream | Checkpoint status | Milestone decision |
|---|---|---|---|---|
| ClearerVoice-Studio SpEx+ (`SpEx_plus_TSE_16K`) | `https://github.com/modelscope/ClearerVoice-Studio` | Apache-2.0 repository license | Downloaded by upstream on first load; every discovered checkpoint asset is SHA-256 recorded | Persistent in-process adapter and Intel installer implemented; mandatory target-machine listening remains |
| WeSep reference-conditioned TSE | `https://github.com/wenet-e2e/wesep` | Apache-2.0 repository license | Not vendored; checkpoint-specific provenance/license must be reviewed | Independent candidate adapter implemented; evaluation blocked until a reviewed local checkout and checkpoint are supplied |
| Same-take diagnostic | TaskMivra milestone source | Project source terms | No weights | Plumbing only; explicitly ineligible for acceptance |

## Evidence and blocker

On 2026-08-22 the cloud development environment could not reach GitHub: `git ls-remote` returned `CONNECT tunnel failed, response 403`. The target-machine installer therefore acquires upstream directly, writes its resolved commit to `runtime/clearervoice-source.lock`, and checks out that exact commit on all later runs. `runtime/source-provenance.json` records source and license SHA-256; after model construction, `runtime/provenance.json` records the commit and hashes every discovered `.pt`, `.pth`, `.ckpt`, `.bin`, `.safetensors`, or SpEx-named asset in the checkout and model caches. First acquisition writes `runtime/checkpoint-assets.lock.json`; every later startup compares exact names, sizes, and SHA-256 values and refuses readiness on any mismatch. The first report remains marked `checkpoint_review_required` until that lock has been inspected; subsequent matching runs are marked verified.

Repository licensing does **not** automatically establish permission to redistribute every checkpoint or dataset derivative. Before evaluation, record the upstream commit, checkpoint filename, SHA-256, download page, model-card license, training-data provenance, framework versions, sample rate, and command below in a local evaluation record.

## Intel macOS acquisition and launch

```bash
./scripts/start_crystal_voice_macos.sh
```

The launcher requires macOS x86_64 and Python 3.12, uses a unique clean venv, and does not open the UI until `ClearVoice(task="target_speaker_extraction", model_names=["SpEx_plus_TSE_16K"])` has returned. Exact startup/download/import errors remain in `runtime/crystal-voice.log` and are printed if the process exits. Delete `runtime/` only when intentionally acquiring and reviewing a new source revision.

The adapter explicitly converts microphone PCM from 48 kHz to 16 kHz with a 48-tap Hann-windowed sinc anti-aliasing filter, feeds both the mixture and 3–5 second reference WAVs into SpEx+, and resamples the unnormalized extraction back to the capture rate. It applies no spectral suppression or neural post-stack.
