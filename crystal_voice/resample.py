"""Explicit band-limited resampling for microphone/model rate boundaries."""

from __future__ import annotations

import math

from crystal_voice.audio import Audio


def resample(audio: Audio, output_rate: int, taps: int = 48) -> Audio:
    """Windowed-sinc resampler with an anti-aliasing cutoff.

    This is deliberately a waveform-rate conversion stage, not a suppression
    mask.  A 48-tap Hann-windowed low-pass kernel is evaluated at every output
    sample and unity-normalized to avoid gain changes.
    """
    if audio.sample_rate == output_rate:
        return audio
    if output_rate < 8_000 or output_rate > 192_000 or taps < 16 or taps % 2:
        raise ValueError("Unsupported resampling configuration")
    ratio = output_rate / audio.sample_rate
    cutoff = min(1.0, ratio) * 0.94
    count = round(len(audio.samples) * ratio)
    radius = taps // 2
    result = []
    for output_index in range(count):
        source_position = output_index / ratio
        center = math.floor(source_position)
        total = weight_sum = 0.0
        for source_index in range(center - radius + 1, center + radius + 1):
            if not 0 <= source_index < len(audio.samples):
                continue
            distance = source_position - source_index
            scaled = cutoff * distance
            sinc = 1.0 if abs(scaled) < 1e-12 else math.sin(math.pi * scaled) / (math.pi * scaled)
            window_position = distance / radius
            window = 0.5 * (1 + math.cos(math.pi * window_position)) if abs(window_position) <= 1 else 0.0
            weight = cutoff * sinc * window
            total += audio.samples[source_index] * weight
            weight_sum += weight
        result.append(total / weight_sum if abs(weight_sum) > 1e-12 else 0.0)
    return Audio(tuple(result), output_rate)

