# Locked-Baseline Parity Gate

The TaskMivra-owned engine is not allowed to replace the frozen v0.4.0 benchmark merely because it reduces noise.

For every candidate, use the same source recording to produce:

1. raw microphone reference
2. frozen v0.4.0 benchmark output
3. TaskMivra-owned candidate output

Mandatory listening cases: quiet room, fan/AC, keyboard/desk noise, traffic, music, television speech/music, nearby competing speaker, mixed noise, quiet speaker, loud speaker, microphone-distance changes, speech starts/stops, consonants, sustained vowels.

Hard failures: clipping; processing-added crackle/static; metallic/watery/robotic tone; obvious slowing/time stretch; cut word boundaries; lost quiet syllables; severe muffling/consonant loss; unstable pumping; fake loudness-only improvement; remote-party audio processing.

The new engine passes only when its target-user speech naturalness, intelligibility, interference reduction, level stability, and practical call latency are equal to or better than the frozen benchmark in blind listening, with no prohibited production dependency.
