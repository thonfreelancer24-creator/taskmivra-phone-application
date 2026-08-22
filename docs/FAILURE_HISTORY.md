# Crystal Voice Failure History — Do Not Repeat

This file records observed failures from earlier TaskMivra experiments so Codex does not rediscover the same bad paths.

## Browser denoise iterations
- Hard/strong gating caused words and syllables to cut out.
- Stacking multiple neural denoisers caused choppy/slowed voice and CPU overload.
- Simple denoising reduced stationary noise but did not remove music or competing voices while the target was speaking.
- A speech-safe configuration preserved naturalness better, but music remained audible.

## Blind separation iterations
A two-source separator was tested, then a saved voice profile was used to choose whichever separated stream looked more like the enrolled speaker.

This was the wrong architecture because the voice profile did not condition the separator itself. Do not repeat this design as the primary solution.

## Profile-conditioned Vanta experiment
A reference-conditioned target-speaker model was then tested.
Observed problems:
- Background music still leaked into the final output.
- Output quality could sound rough / blown-speaker-like.
- Early playback normalization pushed extracted audio too hard and made artifacts sound worse.
- Removing clipping/normalization did not eliminate the core artifacts.

The model's own published limitations were consistent with what we heard: incomplete target-energy capture, preserved room acoustics, and relatively weak perceptual quality for this product target.

Conclusion: do not use this model as the final TaskMivra engine merely because it is profile-conditioned.

## Residual FFT masking experiment
A handcrafted residual-aware spectral mask was added after target extraction.
Observed result:
- More metallic / musical-noise artifacts.
- Voice detail suffered.

Do not use custom FFT masking unless objective and listening tests prove it improves both suppression and speech quality.

## Neural cleanup after weak extraction
A neural denoise stage after the weak target extractor reduced some high-frequency content but did not adequately remove the music leakage.
Observed result:
- Muffled / rough voice
- Loss of 3–8 kHz clarity/consonant energy
- Remaining music still audible

Conclusion: a post-denoiser cannot rescue a fundamentally weak target extraction result.

## Gain / clipping lesson
One failed output was measured with a safe peak around -6 dBFS and zero clipped samples, yet still sounded distorted. Therefore:
- Do not assume harshness is always clipping.
- Inspect the separated waveform and model artifacts before adjusting gain.

## Dependency lessons from Intel macOS
- macOS x86_64 + Python 3.12 had limited PyTorch wheel availability; Torch 2.2.2 / Torchaudio 2.2.2 worked.
- NumPy 2.x created compatibility warnings with Torch 2.2.2.
- DeepFilterLib attempted a Rust/Cargo source build and failed because Cargo was not installed.
- Avoid unnecessary dependencies and source builds for the validation package.
- Do not reuse an old contaminated virtual environment.

## Startup / packaging lessons
- Unique port per build.
- Visible build/version in UI.
- Unique cache tags.
- Browser must not open until required model assets are verified and backend is ready.
- Exact backend/model startup errors must be visible to the user.
- Never depend on hidden first-request model initialization if it makes the first recording fail.

## Current strategic conclusion
The next engine must begin with a stronger target-speaker extraction model and benchmark multiple candidates before any DSP polish. Voice fidelity is not a post-processing problem if the extractor itself damages speech.
