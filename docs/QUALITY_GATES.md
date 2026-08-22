# Automated quality-gate policy

The runner applies only an **objective synthetic pre-gate**. A candidate is rejected when it is not reference-conditioned, clips, changes duration by over 0.5%, creates large adjacent-sample discontinuities, introduces long digital-zero runs, exceeds -3 dBFS, improves SI-SDR by less than 1 dB, or correlates with synthetic clean target by less than 0.8.

It reports peak/RMS, loudness delta, real-time factor, SI-SDR/SI-SDRi, waveform correlation, discontinuities, digital-silence runs, and analysis-band energy for 100–300 Hz, 300–1000 Hz, 1–3 kHz, and 3–8 kHz. Waveform correlation is not STOI and is labeled accordingly; install no licensing-sensitive metric by implication.

These inexpensive checks can detect clipping, timing errors, gross choppiness, and target destruction. They cannot reliably identify metallic, watery, robotic, phasey, muffled, crackling, or blown-speaker character. Therefore an automated pass is never a product acceptance. A human must listen to every scenario in `ACCEPTANCE_TESTS.md`, including private real recordings, and record the listening result outside version control.

Synthetic tones validate the harness but are not evidence of real speech quality. Put consented recordings under `fixtures/private/`; that directory is ignored by Git.

