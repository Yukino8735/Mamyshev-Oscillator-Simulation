#!/usr/bin/env python3
"""Run the one explicitly authorized demo_10k_v1 synthetic experiment."""
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from mamyshev_ml.demo10k_experiment import run

if __name__ == "__main__":
    print(json.dumps(run(), indent=2))
