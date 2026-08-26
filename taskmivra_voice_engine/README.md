# TaskMivra Voice Engine v0.2

Independent TaskMivra-controlled local microphone-processing milestone for TaskMivra Phone.

## Safety boundary

This project does **not** load, embed, download, or call WeSep, BSRNN-ECAPA, WeSpeaker, ClearerVoice, MossFormer, Krisp, or any other pretrained voice-processing model/API. The frozen Crystal Voice v0.4.0 branch remains an internal quality benchmark only.

## v0.2 scope

- everything from the v0.1 48 kHz streaming DSP core
- 3–5 second local TaskMivra Voice Profile enrollment
- derived profile representation only; raw enrollment PCM is not stored in the profile object
- TaskMivra-designed spectral-distribution and pitch-range speaker scoring
- soft frame-by-frame target confidence with attack/release smoothing
- profile-conditioned spectral/harmonic suppression with no hard gate
- `setVoiceProfile()`, `clearVoiceProfile()`, and profile status reporting
- physical-microphone bypass/fail-safe remains intact
- no runtime package dependencies
- no pretrained model or external voice-processing service

## Run tests

```bash
npm test
```

## Process a normal 48 kHz PCM16 WAV

```bash
node tools/process_wav.js input.wav processed.wav
```

## Process with a TaskMivra Voice Profile

```bash
node tools/process_profiled_wav.js voice-profile.wav challenge.wav processed.wav profile.json
```

The optional `profile.json` contains the derived local profile representation, not the raw enrollment audio.

## Important release gate

v0.2 is an owned target-speaker control milestone, not yet declared equivalent to the frozen v0.4.0 neural benchmark. Synthetic tests prove that the profile can distinguish and attenuate deliberately mismatched synthetic speakers while preserving target-like speech, but that is not evidence of full real-world overlapping-speaker separation.

Production replacement happens only after blind A/B parity against the frozen benchmark on quiet room, fan/AC, keyboard, traffic, TV/music, nearby competing speaker, and mixed-noise cases. If v0.2 does not match the frozen output in those recordings, the next step is a TaskMivra-owned trainable separation/enhancement model and TaskMivra-controlled weights—not a third-party checkpoint.
