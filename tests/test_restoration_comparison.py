import json

import crystal_voice.benchmark as benchmark


def report(correlation, artifact_gate=True):
    return {"cases": [{
        "regime": "known",
        "status": "completed",
        "metrics": {
            "target_waveform_correlation": correlation,
            "passes_machine_artifact_gate": artifact_gate,
            "clipped_samples": 0,
            "duration_ratio": 1.0,
        },
    }]}


def test_restoration_is_rejected_when_identity_correlation_regresses(monkeypatch, tmp_path):
    reports = iter((report(0.91), report(0.86)))
    monkeypatch.setattr(benchmark, "run_benchmark", lambda *_: next(reports))
    result = benchmark.compare_restoration(object(), object(), tmp_path)
    assert result["accepted"] is False
    assert result["comparisons"][0]["identity_correlation_delta"] < -0.02
    assert json.loads((tmp_path / "restoration-comparison.json").read_text())["accepted"] is False


def test_restoration_survives_machine_gate_without_identity_regression(monkeypatch, tmp_path):
    reports = iter((report(0.91), report(0.90)))
    monkeypatch.setattr(benchmark, "run_benchmark", lambda *_: next(reports))
    assert benchmark.compare_restoration(object(), object(), tmp_path)["accepted"] is True
