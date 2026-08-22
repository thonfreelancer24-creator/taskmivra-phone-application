# TaskMivra Phone - Codex Engineering Instructions

## Project goal
Build **TaskMivra Crystal Voice**, an owned voice-isolation and speech-enhancement engine for TaskMivra Phone.

The product requirement is simple but strict:

> Keep the enrolled TaskMivra user's voice natural, clear, full, and stable while aggressively suppressing music, TV, competing speakers, fan/AC, keyboard, room noise, and reverberant background energy.

Audio quality and speaker isolation are equal priorities. Never improve suppression by destroying voice quality.

## Read first
Before changing code, read:
- `docs/PRODUCT_SPEC.md`
- `docs/ACCEPTANCE_TESTS.md`
- `docs/FAILURE_HISTORY.md`
- `docs/MODEL_BENCHMARK_PLAN.md`

These files are the source of truth.

## Non-negotiable engineering rules
1. **One recording only.** Raw and processed outputs must come from the exact same microphone capture. Never ask the user to record a second challenge take.
2. **Profile-conditioned extraction.** The 3-5 second enrollment/reference clip must condition the extraction model itself. Do not blindly separate sources and choose a speaker afterward.
3. **Do not normalize toward 0 dBFS.** Never peak-normalize isolated speech to 90-100% full scale. Preserve natural level and headroom.
4. **No hard gates that clip words.** Do not solve noise by cutting quiet syllables, consonants, word endings, breaths, or low-level speech.
5. **No hand-made spectral suppression unless benchmarked.** FFT masks can create musical noise/metallic artifacts. Any such stage must beat the baseline on objective tests and listening checks or be removed.
6. **No uncontrolled neural stacking.** Multiple denoisers/separators may cause choppy, slowed, phasey, muffled, or metallic speech. Each stage must have measured benefit.
7. **Benchmark models before committing to one.** Implement a model-adapter interface and compare candidates on the same fixtures.
8. **No proprietary copying.** Do not decompile, extract, distill, or copy proprietary model weights/code. Use permissively licensed open-source models, public research, or TaskMivra-trained components. Record license/provenance for every model.
9. **No runtime vendor dependency required for the core.** The target is a TaskMivra-owned deployable stack, not a mandatory per-minute third-party SDK.
10. **No secrets in the repo.** Use environment variables and sample config files only.

## Development order
Build in this order:
1. Reproducible offline quality laboratory and benchmark harness.
2. Profile enrollment and target-speaker extraction adapters.
3. Automatic objective scoring and candidate ranking.
4. Listening UI: same-take Raw vs Processed A/B.
5. High-fidelity residual enhancement only after extraction.
6. Streaming/chunked architecture after offline quality passes.
7. WebRTC/MediaStream integration only after streaming quality passes.

Do not jump to telephony integration until the isolation engine passes acceptance tests.

## Target environments
- Development/CI: Linux CPU first; GPU acceleration optional.
- User validation machine: **macOS x86_64 (Intel), Python 3.12 currently installed**.
- Final browser/call path: 48 kHz WebRTC/Opus compatible.
- Model internal sample rate may be 16/32/48 kHz, but all resampling must be explicit and high quality.

For the Intel Mac validation package:
- pin compatible dependencies;
- prefer binary wheels;
- do not require Rust/Cargo compilation for the default path;
- do not reuse contaminated virtual environments;
- use a unique visible build version and unique local port;
- show exact startup/model errors in the UI;
- do not open the browser until required models are actually ready.

## Audio safety rules
- Output must never clip.
- Default final peak ceiling: **<= -3 dBFS**; target around **-6 dBFS** unless justified by loudness measurements.
- Automatic gain may attenuate freely but should not boost more than **+3 dB** without explicit justification and tests.
- Preserve intelligibility and high-frequency consonant information; do not low-pass speech merely to hide noise.
- Preserve speech continuity; zero cut words, zero obvious time-stretch/slowdown, zero buffer underrun clicks.

## Testing discipline
For every meaningful model/DSP change:
- run the benchmark suite;
- report target preservation, interference suppression, clipping/headroom, and runtime;
- save A/B WAV artifacts for inspection;
- reject the change if suppression improves but voice-quality thresholds regress beyond limits in `docs/ACCEPTANCE_TESTS.md`.

Synthetic tests are necessary but not sufficient. The real acceptance scenario includes music and TV playing several feet away while the enrolled user speaks.

## Delivery standard
Do not present a build as successful because it launches. A build is successful only when the audio output passes the quality gates.

When finishing a task, report:
- what changed;
- models and exact versions/weights used;
- license/provenance;
- benchmark results before/after;
- commands/tests run;
- known limitations;
- exact files or artifacts produced.
