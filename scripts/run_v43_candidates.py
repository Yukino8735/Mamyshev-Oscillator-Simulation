#!/usr/bin/env python3
"""Two explicit stages of the finite frozen-model application, never BO."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))
from mamyshev_ml.v43_candidates import freeze_candidate_plan, confirm_candidates


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='stage', required=True)
    freeze = sub.add_parser('freeze')
    freeze.add_argument('--model', type=Path, required=True)
    freeze.add_argument('--selection', type=Path, required=True)
    freeze.add_argument('--out', type=Path, required=True)
    confirm = sub.add_parser('confirm')
    confirm.add_argument('--plan', type=Path, required=True)
    args = parser.parse_args()
    if args.stage == 'freeze':
        from mamyshev_ml.v43_adapter import load_application_evaluator
        model = load_application_evaluator(args.model, args.selection)
        value = freeze_candidate_plan(predictor=model, output=args.out)
        value = {k:v for k,v in value.items() if k not in ('predictions','sources','exclusions')}
    else:
        value = confirm_candidates(args.plan, deadline_s=90)
    print(json.dumps(value, indent=2, allow_nan=False))


if __name__ == '__main__':
    main()
