#!/usr/bin/env python3
"""Run the frozen synthetic-only V4 search; never starts MATLAB."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--package", type=Path, default=ROOT / "mamyshev_accuracy_v4")
    parser.add_argument("--output", type=Path, default=ROOT / "reports/local/accuracy_v4_001/search")
    parser.add_argument("--wall-seconds", type=float, default=350)
    args = parser.parse_args()
    from threadpoolctl import threadpool_limits
    from mamyshev_ml.v4_evaluators import SyntheticEvaluator
    from mamyshev_ml.v4_search import run_search
    with threadpool_limits(limits=2):
        result = run_search(package=args.package, output=args.output,
                            evaluator=SyntheticEvaluator(seed=0), wall_seconds=args.wall_seconds)
    print(json.dumps(result, indent=2, allow_nan=False))
    return 0 if result["status"] == "completed" else 2


if __name__ == "__main__":
    raise SystemExit(main())
