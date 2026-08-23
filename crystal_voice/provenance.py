"""Exact source/config/checkpoint verification for direct SpEx+ inference."""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_spex_assets(architecture: Path, config: Path, checkpoint: Path) -> Path:
    assets = [
        {"role": "architecture", "path": str(architecture.resolve()), "bytes": architecture.stat().st_size, "sha256": sha256(architecture)},
        {"role": "configuration", "path": str(config.resolve()), "bytes": config.stat().st_size, "sha256": sha256(config)},
        {"role": "checkpoint", "path": str(checkpoint.resolve()), "bytes": checkpoint.stat().st_size, "sha256": sha256(checkpoint)},
    ]
    identity = [{key: item[key] for key in ("role", "bytes", "sha256")} for item in assets]
    lock = Path(os.environ.get("CRYSTAL_VOICE_CHECKPOINT_LOCK", "runtime/spex-assets.lock.json"))
    lock.parent.mkdir(parents=True, exist_ok=True)
    if lock.exists():
        if json.loads(lock.read_text()) != identity:
            raise RuntimeError(f"SpEx+ asset verification failed against {lock}; refusing model readiness")
        verified = True
    else:
        lock.write_text(json.dumps(identity, indent=2))
        verified = False
    checkout = architecture
    while checkout != checkout.parent and not (checkout / ".git").exists():
        checkout = checkout.parent
    revision = None
    license_assets = []
    if (checkout / ".git").exists():
        revision = subprocess.run(["git", "-C", str(checkout), "rev-parse", "HEAD"], capture_output=True, text=True, check=True).stdout.strip()
        for name in ("LICENSE", "LICENSE.txt", "NOTICE"):
            path = checkout / name
            if path.exists():
                license_assets.append({"path": str(path.resolve()), "sha256": sha256(path)})
    report = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "model": "SpEx+ WSJ0-2mix 2-speaker, direct architecture",
        "model_repository": "alibabasglab/log_wsj0-2mix_speech_SpEx-plus_2spk",
        "architecture_repository": "modelscope/ClearerVoice-Studio",
        "architecture_commit": revision,
        "license": "Apache-2.0 (verify included upstream license before redistribution)",
        "license_assets": license_assets,
        "assets": assets,
        "lock": str(lock.resolve()),
        "verified_against_existing_lock": verified,
        "review_required": not verified,
    }
    destination = Path(os.environ.get("CRYSTAL_VOICE_PROVENANCE", "runtime/provenance.json"))
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(report, indent=2))
    return destination
