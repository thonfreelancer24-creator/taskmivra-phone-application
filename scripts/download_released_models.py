"""Repository-aware acquisition; never guesses model asset URL locations."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil

from huggingface_hub import snapshot_download


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def unique(root: Path, filename: str) -> Path:
    matches = [path for path in root.rglob(filename) if path.is_file()]
    if len(matches) != 1:
        raise RuntimeError(f"Expected exactly one {filename} in repository snapshot, found {len(matches)}")
    return matches[0]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--destination", type=Path, required=True)
    parser.add_argument("--repo", default="alibabasglab/log_wsj0-2mix_speech_SpEx-plus_2spk")
    parser.add_argument("--revision", default="main")
    args = parser.parse_args()
    snapshot = Path(snapshot_download(repo_id=args.repo, revision=args.revision, repo_type="model"))
    args.destination.mkdir(parents=True, exist_ok=True)
    names = ("config_wsj0-2mix_speech_SpEx-plus_2spk.yaml", "last_best_checkpoint.pt")
    records = []
    for name in names:
        source = unique(snapshot, name)
        destination = args.destination / name
        shutil.copyfile(source, destination)
        records.append({
            "filename": name,
            "repository_path": str(source.relative_to(snapshot)),
            "bytes": destination.stat().st_size,
            "sha256": digest(destination),
        })
    (args.destination / "repository-download.json").write_text(json.dumps({
        "repository": args.repo,
        "requested_revision": args.revision,
        "resolved_revision": snapshot.name,
        "snapshot": str(snapshot),
        "assets": records,
    }, indent=2))


if __name__ == "__main__":
    main()
