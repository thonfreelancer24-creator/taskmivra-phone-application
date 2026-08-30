# TaskMivra Voice v7 — Commercial-safe hybrid

Status: **standalone listening candidate; not connected to TaskMivra Phone until human approval**.

## What changed

- The frozen Crystal Voice v0.4 remains quality/listening reference only.
- Environment/noise suppression is split from competing-speech handling instead of forcing one model to solve every interference class.
- `TaskMivraFastProfileComplex` checkpoints are used only as **magnitude control** in the v7 phase-safe path. The microphone phase is preserved.
- Frequencies above 8 kHz remain on the original 48 kHz microphone path.
- Clean/quiet classification can return exact core bypass.
- Environmental cleanup can use pinned Xiph RNNoise under its BSD-style commercial license; if unavailable or if its native call fails, the core falls back to conservative TaskMivra-written/SciPy Wiener cleanup without dropping microphone audio.
- No auto-normalization is allowed in the suppression core.
- The approved soft tone is a separate post-core polish and is not part of the separator.

## Checkpoints

The production installer supplies two **TaskMivra-owned** checkpoint roles outside Git:

1. environment/general specialist — current accepted TaskMivra v1.1 owned checkpoint;
2. speech/TV specialist — v7 fine-tune trained only from TaskMivra-owned clean speech and deterministic synthetic speaker/TV-like transforms.

Private recordings and checkpoint binaries stay outside Git under `TRAINING_PROVENANCE.md`.

## Current listening-package hashes

- v1.1 owned checkpoint SHA-256: `8d73acc8e5312efb2fab28889a0d0ad0734a35302ec63b5a766dc50fde0cfd76`
- v7 TV-safe owned checkpoint SHA-256: `45a0ee075b74688b3415da376251cf04faf277aa32efdd20d73589a2cd322502`
- listening ZIP SHA-256: `7a25768ab38abeef47b60c332b6388d552e1bc6aa08c55f4abecfefcad4ffa0b`

Real TV and close-music recordings were evaluation-only and were not used to train the v7 checkpoint.

## Hard commercial boundary

Do not bundle or load WeSep, BSRNN-ECAPA/WeSpeaker, MossFormer/ClearerVoice, SpEx+ released checkpoints, Krisp technology, or the frozen Crystal Voice v0.4 implementation in the shipping engine.

## Hard listening gate

Reject for any introduced static/crackle, broken syllables, metallic/watery/robotic texture, thin/distant speech, pumping, missing consonants, word-boundary cuts, clipping, or obvious identity change. Stronger suppression never overrides natural speech.
