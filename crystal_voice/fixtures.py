"""Deterministic synthetic fixtures for plumbing and regression tests."""

from __future__ import annotations

import math
import random

from crystal_voice.audio import Audio


def _voice(duration: float, rate: int, fundamental: float, seed: int) -> Audio:
    rng = random.Random(seed)
    samples = []
    phase = 0.0
    for index in range(round(duration * rate)):
        time = index / rate
        syllables = 0.18 + 0.82 * max(0.0, math.sin(2 * math.pi * 2.7 * time)) ** 0.7
        jitter = 1 + 0.008 * rng.uniform(-1, 1)
        phase += 2 * math.pi * fundamental * jitter / rate
        sample = syllables * (0.24 * math.sin(phase) + 0.09 * math.sin(2 * phase) + 0.04 * math.sin(4 * phase))
        # Low-level consonant-like detail makes the 3–8 kHz retention metric
        # meaningful when comparing narrow-band extraction and 48 kHz SR.
        sample += syllables * 0.012 * math.sin(2 * math.pi * 5_500 * time)
        samples.append(sample)
    return Audio(tuple(samples), rate)


def synthetic_case(regime: str, duration: float = 1.5, rate: int = 48_000) -> tuple[Audio, Audio, Audio]:
    target = _voice(duration, rate, 137, 10)
    interferer = _voice(duration, rate, 211, 20)
    snr = {"speech_10db": 10, "speech_5db": 5, "speech_0db": 0, "speech_-5db": -5}.get(regime, 5)
    interference_gain = 10 ** (-snr / 20)
    rng = random.Random(30)
    mixture = []
    for index, (wanted, other) in enumerate(zip(target.samples, interferer.samples)):
        time = index / rate
        if regime in {"music", "music_noise"}:
            other = 0.18 * (math.sin(2 * math.pi * 330 * time) + math.sin(2 * math.pi * 440 * time))
        noise = rng.uniform(-0.025, 0.025) if regime == "music_noise" else 0.0
        mixture.append(wanted + interference_gain * other + noise)
    reference = _voice(4.0, rate, 137, 11)
    return reference, Audio(tuple(mixture), rate), target


REGIMES = ("speech_10db", "speech_5db", "speech_0db", "speech_-5db", "music", "music_noise")
