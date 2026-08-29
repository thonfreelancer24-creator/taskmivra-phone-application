# TaskMivra Voice — Crystal Reference Parity Gate

Date: 2026-08-30
Status: REQUIRED for every new owned-engine candidate

## Purpose

The frozen TaskMivra Crystal Voice v0.4.0 working baseline is the listening/quality benchmark for the TaskMivra-owned commercial engine.

Frozen benchmark:
- branch: `locked/crystal-voice-working-baseline-2026-08-23`
- commit: `53ee2a20481dbe17257058502aa2a996cc6d924f`

The frozen benchmark must never be modified and must never be used as production code, production weights, distillation targets, pseudo-labels, or training audio.

## Commercial ownership boundary

Production TaskMivra weights may train only on TaskMivra-owned or independently rights-cleared material accepted by `TRAINING_PROVENANCE.md`.

The frozen benchmark is used only for:
1. human A/B listening;
2. behavior/quality target definition;
3. independent evaluation notes.

## Primary acceptance order

1. Natural target voice preservation
2. Zero introduced static/crackle
3. No broken syllables or clipped word boundaries
4. No distant/thin/phasey/metallic/watery coloration
5. Stable loudness without auto-normalization
6. Background suppression
7. Target-speaker discrimination
8. Real-time latency

Noise reduction never overrides voice preservation.

## Clean-speech hard gate

A candidate fails immediately if clean target speech introduces any audible artifact that is absent from the raw input, including:
- static or crackle;
- metallic/watery/robotic texture;
- broken consonants;
- missing quiet syllables;
- word-start or word-end cuts;
- pumping;
- artificial distance/thinning;
- obvious phase smearing.

Clean input should remain perceptually near-pass-through before the approved post-separation tone shaping.

## Approved tone target

Post-separation only:
- +0.7 dB around 250 Hz
- -0.7 dB around 3 kHz
- -1.2 dB around 5.6 kHz
- limiter safety only
- no auto-level
- no normalization

## Required candidate listening package

Every candidate must include:
- clean raw reference;
- clean processed candidate;
- locked Crystal Voice benchmark output from the same evaluation take where available;
- fan/AC challenge;
- TV challenge;
- music challenge;
- nearby competing speaker challenge where rights allow;
- water/shower challenge;
- raw/candidate A/B files;
- objective metrics;
- checkpoint SHA-256;
- training manifest SHA-256;
- source commit SHA;
- explicit human listening decision.

## Rejection rule

If objective suppression improves but clean speech becomes less natural than the current accepted quality target, reject the candidate and keep working.
