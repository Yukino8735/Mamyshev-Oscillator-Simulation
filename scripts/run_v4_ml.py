#!/usr/bin/env python3
"""V4 selection, frozen evaluation and four-input prediction CLI."""
import argparse
import json
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from mamyshev_ml.v4_ml import select, final_evaluate, predict_design

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='action', required=True)
    train = sub.add_parser('select'); train.add_argument('--out', type=Path, required=True)
    train.add_argument('--deadline-s', type=float, default=300.)
    evaluate = sub.add_parser('evaluate'); evaluate.add_argument('--out', type=Path, required=True)
    evaluate.add_argument('--model', type=Path, required=True); evaluate.add_argument('--selection', type=Path, required=True)
    evaluate.add_argument('--authorize-final-evaluation', action='store_true')
    predict = sub.add_parser('predict'); predict.add_argument('--model', type=Path, required=True)
    predict.add_argument('--selection', type=Path, required=True); predict.add_argument('--design-json', type=Path, required=True)
    args = parser.parse_args()
    if args.action == 'select':
        result = select(args.out, args.deadline_s)
    elif args.action == 'evaluate':
        result = final_evaluate(args.model, args.selection, args.out, args.authorize_final_evaluation)
    else:
        result = predict_design(args.model, args.selection, json.loads(args.design_json.read_text()))
    print(json.dumps(result, indent=2, allow_nan=False))

if __name__ == '__main__':
    main()
