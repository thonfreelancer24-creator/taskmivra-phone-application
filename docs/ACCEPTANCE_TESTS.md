# TaskMivra Crystal Voice — Acceptance Tests

A model/build is not accepted because it starts or removes some noise. It must preserve the enrolled user's speech while suppressing interference.

## Mandatory real listening scenarios
Run each with the same enrolled speaker profile:

1. Quiet-room baseline
2. Music several feet away while user speaks
3. TV speech/music while user speaks
4. Nearby second person speaking while target speaks
5. Fan/AC while target speaks
6. Keyboard/desk noise while target speaks
7. Mixed challenge: music + fan + target speech

## Hard-fail conditions
Reject a build if any occurs:
- Any clipped samples in final PCM output
- Audible crackle/static introduced by processing
- Metallic/watery/robotic texture that was not present in raw input
- Noticeable time stretching or slowing
- Word starts/endings cut
- Quiet syllables disappear
- Strong muffling or loss of consonants
- Final output is louder only because of aggressive normalization
- Raw and processed audio are not derived from the exact same microphone take
- Voice profile is used only to choose among blindly separated outputs instead of conditioning extraction

## Objective checks
Track at minimum:
- Peak dBFS
- Clipped sample count
- RMS / loudness delta between raw and processed
- Processing real-time factor
- Speech-band energy retention by bands: 100–300 Hz, 300–1000 Hz, 1–3 kHz, 3–8 kHz
- Target-speaker similarity before/after using a speaker embedding model independent of the extractor where practical
- SI-SDR / SI-SDRi when synthetic ground truth exists
- STOI or comparable intelligibility measure when ground truth exists
- PESQ/POLQA-equivalent research metric where licensing permits

## Guardrails
- Final peak target: about -6 dBFS
- Hard default ceiling: <= -3 dBFS
- Automatic gain boost: <= +3 dB unless a test demonstrates a safe reason
- No hard gate as the primary suppression method
- High-frequency speech detail must not collapse merely to hide noise

## Comparison rule
Every candidate must be compared with:
- Raw microphone
- Current best accepted baseline
- At least one alternative model/configuration

## Pass rule
A candidate passes only when:
1. Target voice is judged natural and intelligible in all mandatory scenarios.
2. Music/TV/competing speech is substantially reduced without voice damage.
3. No hard-fail condition occurs.
4. Objective metrics show no major speech-quality regression versus the quiet-room baseline.

If suppression and naturalness conflict, preserve natural speech and continue model work rather than shipping a damaged voice.
