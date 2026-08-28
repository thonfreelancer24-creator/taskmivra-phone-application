"""Fail-closed training-data rights validation for TaskMivra Voice Engine."""
from __future__ import annotations
import json
from pathlib import Path

ALLOWED_RIGHTS = {
    "taskmivra-owned",
    "public-domain",
    "cc0-1.0",
    "explicit-commercial-training-license",
    "recorded-with-explicit-training-consent",
}
AUDIO_FIELDS = (
    "mixture",
    "target_clean",
    "profile_clean",
    "negative_profile_clean",
    "interference",
    "noise",
)


def load_manifest(path: str | Path):
    rows = []
    for line_no, line in enumerate(Path(path).read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        row = json.loads(line)
        rights = row.get("rights", {})
        for field in AUDIO_FIELDS:
            value = row.get(field)
            if value in (None, ""):
                continue
            basis = rights.get(field)
            if basis not in ALLOWED_RIGHTS:
                raise ValueError(
                    f"line {line_no}: {field} has prohibited/unclear training rights: {basis!r}"
                )
        if row.get("derived_from_benchmark_output"):
            raise ValueError(
                f"line {line_no}: benchmark/distilled output is prohibited as training material"
            )
        rows.append(row)
    if not rows:
        raise ValueError("training manifest contains no approved examples")
    return rows
