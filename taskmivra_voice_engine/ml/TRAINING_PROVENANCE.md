# TaskMivra Voice Engine — Training Provenance Rules

## Production-weight boundary

The production-training path is fail-closed. Every audio field in a manifest must carry an approved rights basis before it can be loaded.

Allowed labels:
- `taskmivra-owned`
- `public-domain`
- `cc0-1.0`
- `explicit-commercial-training-license`
- `recorded-with-explicit-training-consent`

Any unknown or missing rights label is rejected.

## Private recordings

Customer/user enrollment audio, private challenge recordings, generated mixtures, and trained checkpoints must remain outside Git. Store only code, provenance rules, and reproducible recipes in the repository.

## Prohibited training material

Do not train production weights on:
- output from the frozen/locked benchmark engine;
- distillation targets derived from the benchmark engine;
- third-party pretrained speech/voice weights with unclear or incompatible rights;
- commercial music or television recordings without explicit commercial model-training rights;
- proprietary competitor output.

The locked Crystal Voice benchmark may be used only for evaluation and listening comparison.

## Same-mixture profile contrast

For target-speaker training, a precomputed `mixture` may be paired with multiple `profile_clean` / `target_clean` combinations. This is intentional: the exact same mixture must produce a different target when a different enrolled profile is supplied. This prevents a separator from succeeding while ignoring enrollment.

## Synthetic auxiliary identities

TaskMivra may create deterministic synthetic auxiliary speaker-like signals or transformations from TaskMivra-owned/cleared material to force profile discrimination. Such data must not depend on pretrained voice-cloning or speaker-generation weights unless those weights separately satisfy TaskMivra's commercial provenance standard.

## Acceptance rule

Training loss is not an acceptance criterion. A checkpoint must pass:
- profile-switch verification;
- SI-SDR/SI-SDRi synthetic gates;
- clipping/headroom checks;
- speech-band preservation checks;
- mandatory human Raw vs Processed listening.

A checkpoint that improves music but fails TV, competing speech, naturalness, or any locked hard gate remains rejected and must not be promoted to production.

## 2026-08-27 development checkpoint

The local owned-model training round reached a profile-conditioned checkpoint that materially improved a loud-music synthetic challenge, but the held-out TV challenge remained below the locked +1 dB SI-SDRi minimum. That checkpoint is therefore **development-only / rejected for production**. No private audio or checkpoint weights are committed here.
