# TaskMivra Crystal Voice — Model Benchmark Plan

## Goal
Select the strongest target-speaker extraction backbone for TaskMivra Phone before spending time on DSP polish or telephony integration.

## Required architecture
Implement a common adapter interface such as:

```python
class TargetSpeakerExtractor:
    name: str
    version: str
    sample_rate: int

    def load(self) -> None: ...
    def enroll(self, reference_wav) -> object: ...
    def extract(self, mixture_wav, profile) -> np.ndarray: ...
```

Adapters must return un-normalized floating-point target speech plus metadata. Loudness/output safety is a separate stage.

## Candidate priority
Evaluate, in this order where feasible and properly licensed:

1. **ClearerVoice-Studio / SpEx+**
   - Reference-speech-conditioned target extraction.
   - Strong published WSJ0-2mix separation benchmark.
   - Verify exact checkpoint license and redistribution terms before production use.

2. **WeSep / Real-TSE models**
   - Evaluate only checkpoints with clear provenance/license and a reproducible local inference path.
   - Prefer causal models later for streaming evaluation.

3. **Other permissively licensed target-speaker extraction models**
   - Must accept a reference/enrollment signal as conditioning.
   - Record repo, commit/tag, model/checkpoint hash, license, sample rate, architecture, and runtime requirements.

4. **TaskMivra-trained model**
   - Longer-term option after benchmark harness exists.

Do not use proprietary competitor services to extract training data, weights, embeddings, or hidden behavior.

## Benchmark fixtures
Create version-controlled synthetic fixture recipes and a local `fixtures/private/` path for human recordings that is gitignored.

Synthetic fixtures should combine:
- target speech
- second speaker
- music
- stationary noise
- room impulse responses
- varying target/interference SNR

Required test regimes:
- target 10 dB above interferer
- target 5 dB above interferer
- equal-level target/interferer
- target 5 dB below interferer (stress/out-of-distribution flag allowed)
- target + music
- target + music + stationary noise

## Metrics
When ground truth exists, compute:
- SI-SDR and SI-SDR improvement
- STOI
- signal peak and clipped samples
- band-energy retention
- runtime / real-time factor
- memory usage where practical

Optional metrics where dependencies/licensing are safe:
- PESQ
- DNSMOS or other perceptual estimator

Use an independent speaker-embedding model for target similarity if practical, but do not optimize solely to that metric.

## Quality ranking
Do not rank on suppression alone.

Recommended composite gate:
1. Hard reject if clipping/artifact rules fail.
2. Hard reject if speech intelligibility drops beyond threshold.
3. Among survivors, rank target-speaker separation and interference suppression.
4. Human listening is final tie-breaker.

## Post-processing policy
Start with **no post-processing** beyond safe resampling and output headroom.

Add a denoiser, dereverberator, equalizer, compressor, or limiter only when an A/B benchmark proves it improves the final result.

Any post-stage must be individually switchable in the benchmark harness so its contribution can be measured.

## Deliverables from first Codex milestone
- reproducible Python environment
- adapter interface
- at least two model adapters attempted, or a documented blocker with evidence
- CLI benchmark runner
- generated HTML/JSON benchmark report
- A/B WAV artifacts
- simple local browser UI for enrollment + one-take Raw/Processed playback
- README with exact setup commands for Linux and Intel macOS where supported
- model provenance/license table

## Stop condition
Do not begin WebRTC streaming implementation until at least one model meets the offline acceptance tests on the real music/TV/second-speaker scenario.
