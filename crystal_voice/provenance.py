"""Runtime source/checkpoint hashing for locally acquired model assets."""

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


def write_clearervoice_report(checkout: Path) -> Path:
    roots = [checkout]
    for value in (
        os.environ.get("MODELSCOPE_CACHE", str(Path.home() / ".cache" / "modelscope")),
        os.environ.get("TORCH_HOME", str(Path.home() / ".cache" / "torch")),
    ):
        if value:
            path = Path(value).expanduser()
            if path.exists() and path not in roots:
                roots.append(path)
    assets = []
    suffixes = {".pt", ".pth", ".ckpt", ".bin", ".safetensors"}
    for root in roots:
        for path in root.rglob("*"):
            if path.is_file() and (path.suffix.lower() in suffixes or "spex" in path.name.lower()):
                assets.append({"path": str(path.resolve()), "bytes": path.stat().st_size, "sha256": sha256(path)})
    revision = subprocess.run(
        ["git", "-C", str(checkout), "rev-parse", "HEAD"], capture_output=True, text=True, check=True
    ).stdout.strip()
    licenses = []
    for name in ("LICENSE", "LICENSE.txt", "NOTICE"):
        path = checkout / name
        if path.exists():
            licenses.append({"path": str(path.resolve()), "sha256": sha256(path)})
    asset_identity = sorted(
        ({"name": Path(item["path"]).name, "bytes": item["bytes"], "sha256": item["sha256"]} for item in assets),
        key=lambda item: (item["name"], item["sha256"]),
    )
    lock_path = Path(os.environ.get("CRYSTAL_VOICE_CHECKPOINT_LOCK", "runtime/checkpoint-assets.lock.json"))
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    if lock_path.exists():
        expected = json.loads(lock_path.read_text())
        if expected != asset_identity:
            raise RuntimeError(
                f"Checkpoint verification failed: discovered assets differ from {lock_path}. "
                "Do not delete the lock until the replacement has been reviewed."
            )
        checkpoint_verified = True
    else:
        if not asset_identity:
            raise RuntimeError("SpEx+ loaded but no checkpoint asset was found to hash; refusing readiness")
        lock_path.write_text(json.dumps(asset_identity, indent=2))
        checkpoint_verified = False
    report = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "model": "SpEx_plus_TSE_16K",
        "source": "https://github.com/modelscope/ClearerVoice-Studio.git",
        "source_commit": revision,
        "source_license_files": licenses,
        "checkpoint_assets": assets,
        "checkpoint_lock": str(lock_path.resolve()),
        "checkpoint_verified_against_existing_lock": checkpoint_verified,
        "checkpoint_review_required": not checkpoint_verified,
    }
    destination = Path(os.environ.get("CRYSTAL_VOICE_PROVENANCE", "runtime/provenance.json"))
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(report, indent=2))
    return destination
