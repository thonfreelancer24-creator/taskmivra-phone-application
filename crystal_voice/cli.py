from __future__ import annotations

import argparse
import json
from pathlib import Path

from crystal_voice.adapters import ADAPTERS
from crystal_voice.benchmark import compare_restoration, run_benchmark
from crystal_voice.server import serve


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="crystal-voice")
    sub = parser.add_subparsers(dest="action", required=True)
    benchmark = sub.add_parser("benchmark", help="run deterministic offline fixtures")
    benchmark.add_argument("--adapter", choices=ADAPTERS, required=True)
    benchmark.add_argument("--output", type=Path, default=Path("artifacts/benchmark"))
    ui = sub.add_parser("ui", help="start local one-take A/B lab")
    ui.add_argument("--adapter", choices=ADAPTERS, required=True)
    ui.add_argument("--host", default="127.0.0.1")
    ui.add_argument("--port", type=int, default=8765)
    compare = sub.add_parser("compare-restoration", help="compare 8 kHz SpEx+ alone against MossFormer2 48 kHz SR")
    compare.add_argument("--output", type=Path, default=Path("artifacts/restoration"))
    args = parser.parse_args(argv)
    if args.action == "benchmark":
        adapter = ADAPTERS[args.adapter]()
        report = run_benchmark(adapter, args.output)
        print(json.dumps({"accepted": report["accepted"], "report": str(args.output / "report.html")}, indent=2))
        return 0 if report["accepted"] else 2
    if args.action == "compare-restoration":
        report = compare_restoration(ADAPTERS["spexplus"](), ADAPTERS["spexplus-sr"](), args.output)
        print(json.dumps(report, indent=2))
        return 0 if report["accepted"] else 2
    adapter = ADAPTERS[args.adapter]()
    serve(adapter, args.host, args.port)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
