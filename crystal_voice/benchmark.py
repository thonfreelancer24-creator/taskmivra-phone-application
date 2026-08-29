"""Reproducible runner producing same-take WAV, JSON, and HTML reports."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import html
import json
from pathlib import Path
import time

from crystal_voice.adapters.base import TargetSpeakerExtractor
from crystal_voice.audio import apply_headroom, encode_wav, fingerprint
from crystal_voice.fixtures import REGIMES, synthetic_case
from crystal_voice.metrics import score


@dataclass
class CaseResult:
    regime: str
    status: str
    accepted: bool
    raw_sha256: str
    processed_sha256: str
    attenuation_db: float
    metrics: dict
    error: str | None = None


def run_benchmark(adapter: TargetSpeakerExtractor, output_directory: Path) -> dict:
    output_directory.mkdir(parents=True, exist_ok=True)
    adapter.load()
    cases = []
    for regime in REGIMES:
        reference, mixture, target = synthetic_case(regime)
        raw_bytes = encode_wav(mixture)
        try:
            profile = adapter.enroll(reference)
            started = time.perf_counter()
            extraction = adapter.extract(mixture, profile)
            elapsed = time.perf_counter() - started
            safe, attenuation = apply_headroom(extraction.audio)
            processed_bytes = encode_wav(safe)
            metrics = score(safe, mixture, target, elapsed)
            accepted = bool(
                adapter.eligible_for_acceptance
                and extraction.metadata.get("conditioned_by_reference") is True
                and metrics["passes_machine_artifact_gate"]
                and metrics["peak_dbfs"] <= -3.0
                and metrics.get("si_sdri_db", -999) >= 1.0
                and metrics.get("target_waveform_correlation", 0) >= 0.8
            )
            case = CaseResult(regime, "completed", accepted, fingerprint(raw_bytes), fingerprint(processed_bytes), attenuation, metrics)
            (output_directory / f"{regime}-raw.wav").write_bytes(raw_bytes)
            (output_directory / f"{regime}-processed.wav").write_bytes(processed_bytes)
            (output_directory / f"{regime}-target.wav").write_bytes(encode_wav(target))
        except Exception as exc:
            case = CaseResult(regime, "error", False, fingerprint(raw_bytes), "", 0, {}, str(exc))
        cases.append(asdict(case))
    report = {
        "schema_version": 1,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "model": {"name": adapter.name, "version": adapter.version, "eligible_for_acceptance": adapter.eligible_for_acceptance},
        "accepted": all(case["accepted"] for case in cases),
        "acceptance_scope": "synthetic objective pre-gate only; mandatory human scenarios remain required",
        "cases": cases,
    }
    (output_directory / "report.json").write_text(json.dumps(report, indent=2, allow_nan=False).replace("Infinity", "1e999"))
    rows = "".join(
        f"<tr><td>{html.escape(c['regime'])}</td><td>{c['status']}</td><td>{'PASS' if c['accepted'] else 'REJECT'}</td>"
        f"<td>{html.escape(c.get('error') or str(round(c.get('metrics', {}).get('si_sdri_db', 0), 2)))}</td>"
        f"<td><audio controls src='{c['regime']}-raw.wav'></audio></td><td><audio controls src='{c['regime']}-processed.wav'></audio></td></tr>"
        for c in cases
    )
    (output_directory / "report.html").write_text(
        "<!doctype html><meta charset=utf-8><title>Crystal Voice benchmark</title>"
        "<style>body{font:16px system-ui;margin:2rem;background:#07131f;color:#e8f4ff}table{border-collapse:collapse}td,th{padding:.6rem;border:1px solid #365}</style>"
        f"<h1>Crystal Voice benchmark — {html.escape(adapter.name)}</h1><p>Overall: {'PASS' if report['accepted'] else 'NOT ACCEPTED'}</p>"
        "<p>Human listening across all mandatory real scenarios is still required.</p><table><tr><th>Regime</th><th>Run</th><th>Gate</th><th>Error / SI-SDRi</th><th>Raw</th><th>Processed</th></tr>" + rows + "</table>"
    )
    return report


def compare_restoration(plain: TargetSpeakerExtractor, restored: TargetSpeakerExtractor, output_directory: Path) -> dict:
    plain_report = run_benchmark(plain, output_directory / "spexplus-alone")
    restored_report = run_benchmark(restored, output_directory / "spexplus-mossformer2-sr")
    comparisons = []
    for baseline, candidate in zip(plain_report["cases"], restored_report["cases"]):
        base_metrics, candidate_metrics = baseline.get("metrics", {}), candidate.get("metrics", {})
        identity_delta = candidate_metrics.get("target_waveform_correlation", -1) - base_metrics.get("target_waveform_correlation", -1)
        accepted = bool(
            candidate["status"] == "completed"
            and candidate_metrics.get("passes_machine_artifact_gate")
            and candidate_metrics.get("clipped_samples") == 0
            and 0.995 <= candidate_metrics.get("duration_ratio", 0) <= 1.005
            and identity_delta >= -0.02
        )
        comparisons.append({"regime": baseline["regime"], "restoration_accepted": accepted, "identity_correlation_delta": identity_delta})
    report = {
        "accepted": all(item["restoration_accepted"] for item in comparisons),
        "human_artifact_listening_required": ["artificial", "metallic", "distorted", "identity change"],
        "comparisons": comparisons,
    }
    (output_directory / "restoration-comparison.json").write_text(json.dumps(report, indent=2))
    return report
