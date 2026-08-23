"""Startup proof that the real released SpEx+ graph/checkpoint can infer."""

from __future__ import annotations

from datetime import datetime, timezone
import json
import math
import os
from pathlib import Path

from crystal_voice.adapters.clearervoice import ClearerVoiceSpExPlusAdapter
from crystal_voice.audio import Audio, apply_headroom, clipped_samples, peak_dbfs


def _known_voice(rate: int, seconds: float, frequency: float) -> Audio:
    samples = tuple(
        0.12 * (0.35 + 0.65 * max(0, math.sin(2 * math.pi * 2.4 * index / rate)))
        * (math.sin(2 * math.pi * frequency * index / rate) + 0.25 * math.sin(4 * math.pi * frequency * index / rate))
        for index in range(round(rate * seconds))
    )
    return Audio(samples, rate)


def run_startup_self_test(adapter: ClearerVoiceSpExPlusAdapter) -> dict:
    reference = _known_voice(48_000, 4.0, 143)
    target = _known_voice(48_000, 1.25, 143)
    other = _known_voice(48_000, 1.25, 217)
    mixture = Audio(tuple(a + 0.45 * b for a, b in zip(target.samples, other.samples)), 48_000)
    result = adapter.extract(mixture, adapter.enroll(reference))
    safe, attenuation = apply_headroom(result.audio)
    finite = bool(safe.samples) and all(math.isfinite(sample) for sample in safe.samples)
    duration_ratio = safe.duration / mixture.duration
    report = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "passed": finite and clipped_samples(safe) == 0 and 0.98 <= duration_ratio <= 1.02,
        "nonempty_finite": finite,
        "clipped_samples": clipped_samples(safe),
        "duration_ratio": duration_ratio,
        "peak_dbfs": peak_dbfs(safe),
        "safety_attenuation_db": attenuation,
        "asset_provenance": str(adapter.provenance_path),
    }
    destination = Path(os.environ.get("CRYSTAL_VOICE_SELFTEST_REPORT", "runtime/startup-self-test.json"))
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(report, indent=2))
    if not report["passed"]:
        raise RuntimeError(f"Real SpEx+ startup self-test failed; inspect {destination}")
    return report
