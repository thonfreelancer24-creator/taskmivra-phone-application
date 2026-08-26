# TaskMivra Voice Engine v0.1

Independent TaskMivra-owned streaming microphone-processing milestone for TaskMivra Phone.

## Safety boundary

This project does **not** load, embed, download, or call WeSep, BSRNN-ECAPA, WeSpeaker, ClearerVoice, MossFormer, Krisp, or any other pretrained voice-processing model/API. The frozen Crystal Voice v0.4.0 branch remains an internal quality benchmark only.

## v0.1 scope

- 48 kHz mono streaming interface
- 20 ms analysis window / 10 ms hop
- DC/low-frequency cleanup
- adaptive minimum-statistics noise-floor tracking
- speech-preserving Wiener-style spectral suppression
- temporal/frequency gain smoothing
- conservative loudness recovery (max +3 dB, disabled by default until speech-aware gating is added)
- <= -3 dBFS output ceiling
- physical-microphone bypass/fail-safe
- latency/status reporting
- WAV test path through the same streaming engine
- no runtime package dependencies

## Run tests

```bash
npm test
```

## Process a 48 kHz PCM16 WAV

```bash
node tools/process_wav.js input.wav processed.wav
```

## Important release gate

v0.1 is the first owned DSP milestone, **not yet a replacement for the locked benchmark**. It must not be advertised as target-speaker isolation. The next milestone adds the TaskMivra-owned Voice Profile / target-speaker subsystem. Production replacement happens only after blind A/B parity against the frozen benchmark on quiet room, fan/AC, keyboard, traffic, TV/music, nearby competing speaker, and mixed-noise cases.
