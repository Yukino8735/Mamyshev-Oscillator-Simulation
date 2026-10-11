#!/usr/bin/env python3
"""Diagnose already observed V4 evidence; no training or oracle calls."""
import argparse
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from mamyshev_ml.v41_diagnostics import diagnose


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--snapshot", type=Path)
    args = parser.parse_args()
    result = diagnose(args.out, snapshot=args.snapshot)
    print(json.dumps({k: result[k] for k in ("status", "classification", "elapsed_s", "prediction_design_rows_across_four_routes")}, indent=2))
    return 0 if result["development_may_proceed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
