#!/usr/bin/env python3
"""Explicit V4.1 stages; run inside existing run_v4_budget.py category monitor."""
import argparse
import json
from mamyshev_ml.v41_experiment import freeze, develop, evaluate

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='stage', required=True)
    sub.add_parser('freeze').add_argument('--diagnosis', required=True)
    sub.add_parser('develop')
    sub.add_parser('evaluate')
    args = parser.parse_args()
    result = freeze(args.diagnosis) if args.stage == 'freeze' else develop() if args.stage == 'develop' else evaluate()
    print(json.dumps({k:v for k,v in result.items() if k not in ('candidates','sources','metrics_protocol')}, indent=2))

if __name__ == '__main__': main()
