import json

from crystal_voice.adapters.diagnostic import SameTakeDiagnosticAdapter
from crystal_voice.benchmark import run_benchmark


def test_diagnostic_benchmark_produces_ab_but_cannot_pass(tmp_path):
    report = run_benchmark(SameTakeDiagnosticAdapter(), tmp_path)
    assert report["accepted"] is False
    assert len(report["cases"]) == 6
    assert (tmp_path / "report.html").exists()
    assert (tmp_path / "speech_0db-raw.wav").read_bytes() == (tmp_path / "speech_0db-processed.wav").read_bytes()
    parsed = json.loads((tmp_path / "report.json").read_text())
    assert parsed["model"]["eligible_for_acceptance"] is False

