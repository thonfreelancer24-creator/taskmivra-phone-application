# TaskMivra Crystal Voice — Product Specification

## Objective
Create TaskMivra's own target-speaker isolation and speech-enhancement engine for TaskMivra Phone.

A user enrolls a short reference clip once. During a call or test, one microphone stream is processed so the enrolled user's voice remains natural and intelligible while competing sound is strongly suppressed.

## Required user flow
1. User records a 3–5 second clean **Target Voice Profile**.
2. The system stores a reusable speaker representation/profile.
3. User starts one microphone capture.
4. The exact same capture feeds both:
   - Raw comparison output
   - Crystal Voice processing path
5. The target-speaker model uses the saved profile as conditioning input during extraction.
6. Residual enhancement may run after extraction only if it improves measured quality.
7. Final audio is returned at safe level with headroom and no clipping.

## Must suppress
- Background music
- Television speech/music
- Nearby second speaker
- Fan / AC
- Keyboard / desk noise
- General room noise
- Moderate reverberant background energy

## Must preserve
- Full target speech continuity
- Natural timbre
- Consonants and sibilants
- Word endings
- Quiet syllables
- Breath and prosodic detail where useful
- No metallic, watery, robotic, phasey, muffled, slowed, choppy, or blown-speaker sound

## Core architecture
Use a model-adapter design so candidates can be benchmarked without rewriting the app.

Suggested candidate families:
- ClearerVoice-Studio SpEx+ target-speaker extraction
- WeSep target-speaker extraction variants where licensing/checkpoints are usable
- Other permissively licensed reference-conditioned target-speaker extraction models
- TaskMivra-trained model later

Do not treat blind source separation followed by speaker selection as the primary architecture.

## Output requirements
- Browser test output: WAV/PCM, no lossy re-encoding for benchmark artifacts
- Final telephony target: WebRTC-compatible 48 kHz output
- No digital clipping
- Peak target approximately -6 dBFS; never exceed -3 dBFS by default
- Avoid automatic gain boosts over +3 dB

## Quality priority
Priority order:
1. Target speech intelligibility and naturalness
2. Competing-speaker/music suppression
3. Stationary-noise suppression
4. Loudness consistency

If noise suppression damages speech, reject the configuration rather than accepting lower voice quality.

## Validation UI
Provide:
- Voice profile enrollment/status
- One challenge recording button
- Raw playback
- Processed playback
- Same-recording fingerprint/ID verification
- Peak and clipping indicators
- Model name/version shown
- Processing time / real-time factor
- Downloadable Raw and Processed WAV
- Optional residue output for engineering diagnostics only

## Production direction
After offline quality passes:
1. Chunked inference
2. Causal/streaming model evaluation
3. Real-time factor <= 1.0 on production target hardware
4. Jitter-safe streaming buffers
5. Web Audio / WebRTC MediaStream output
6. Carrier integration only after audio engine acceptance
