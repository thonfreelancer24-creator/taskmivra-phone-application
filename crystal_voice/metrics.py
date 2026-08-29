"""Objective safety, fidelity, and separation metrics for offline evaluation."""

from __future__ import annotations

import math

from crystal_voice.audio import Audio, clipped_samples, peak_dbfs, rms_dbfs

BANDS = ((100, 300), (300, 1000), (1000, 3000), (3000, 8000))


def _dot(a: tuple[float, ...], b: tuple[float, ...]) -> float:
    return sum(x * y for x, y in zip(a, b))


def si_sdr(estimate: Audio, reference: Audio) -> float:
    n = min(len(estimate.samples), len(reference.samples))
    est, ref = estimate.samples[:n], reference.samples[:n]
    ref_energy = _dot(ref, ref)
    if not n or ref_energy < 1e-12:
        return float("-inf")
    scale = _dot(est, ref) / ref_energy
    target = tuple(scale * x for x in ref)
    error = tuple(x - y for x, y in zip(est, target))
    ratio = _dot(target, target) / max(_dot(error, error), 1e-12)
    return 10 * math.log10(max(ratio, 1e-12))


def correlation(estimate: Audio, reference: Audio) -> float:
    n = min(len(estimate.samples), len(reference.samples))
    a, b = estimate.samples[:n], reference.samples[:n]
    denominator = math.sqrt(_dot(a, a) * _dot(b, b))
    return _dot(a, b) / denominator if denominator else 0.0


def _goertzel_energy(audio: Audio, frequency: float, limit: int = 96_000) -> float:
    samples = audio.samples[:limit]
    if not samples or frequency >= audio.sample_rate / 2:
        return 0.0
    coefficient = 2 * math.cos(2 * math.pi * frequency / audio.sample_rate)
    s1 = s2 = 0.0
    for sample in samples:
        current = sample + coefficient * s1 - s2
        s2, s1 = s1, current
    return max(0.0, s1 * s1 + s2 * s2 - coefficient * s1 * s2) / len(samples)


def band_energies(audio: Audio) -> dict[str, float]:
    result = {}
    for low, high in BANDS:
        frequencies = (low, (low + high) / 2, high - 1)
        result[f"{low}-{high}"] = sum(_goertzel_energy(audio, f) for f in frequencies) / 3
    return result


def artifact_checks(output: Audio, mixture: Audio) -> dict[str, bool | float | int]:
    duration_ratio = output.duration / mixture.duration if mixture.duration else 0.0
    jumps = sum(abs(b - a) > 0.65 for a, b in zip(output.samples, output.samples[1:]))
    zero_runs = 0
    run = 0
    for value in output.samples:
        run = run + 1 if abs(value) < 1e-7 else 0
        zero_runs = max(zero_runs, run)
    return {
        "clipped_samples": clipped_samples(output),
        "duration_ratio": duration_ratio,
        "discontinuity_jumps": jumps,
        "longest_digital_silence_ms": 1000 * zero_runs / output.sample_rate,
        "passes_machine_artifact_gate": (
            clipped_samples(output) == 0
            and 0.995 <= duration_ratio <= 1.005
            and jumps == 0
            and zero_runs / output.sample_rate < 0.25
        ),
    }


def score(output: Audio, mixture: Audio, target: Audio | None, elapsed: float) -> dict:
    raw_bands, out_bands = band_energies(mixture), band_energies(output)
    metrics: dict = {
        "peak_dbfs": peak_dbfs(output),
        "rms_dbfs": rms_dbfs(output),
        "rms_delta_db": rms_dbfs(output) - rms_dbfs(mixture),
        "real_time_factor": elapsed / mixture.duration if mixture.duration else float("inf"),
        "band_energy_retention": {
            key: out_bands[key] / max(raw_bands[key], 1e-12) for key in raw_bands
        },
        **artifact_checks(output, mixture),
    }
    if target:
        metrics["si_sdr_db"] = si_sdr(output, target)
        metrics["raw_si_sdr_db"] = si_sdr(mixture, target)
        metrics["si_sdri_db"] = metrics["si_sdr_db"] - metrics["raw_si_sdr_db"]
        metrics["target_waveform_correlation"] = correlation(output, target)
        target_bands = band_energies(target)
        metrics["target_band_retention"] = {
            key: out_bands[key] / max(target_bands[key], 1e-12) for key in out_bands
        }
    return metrics

