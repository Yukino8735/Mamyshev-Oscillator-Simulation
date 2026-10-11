#!/usr/bin/env python3
"""Explicit stages of the bounded V4.2 experiment, under the existing budget tool."""
import argparse
import json
from pathlib import Path
from mamyshev_ml.v42_experiment import freeze,compare,run_evaluation_safely

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    sub=parser.add_subparsers(dest='stage',required=True)
    for name in ('freeze','compare','evaluate'):sub.add_parser(name)
    pred=sub.add_parser('predict');pred.add_argument('--model',type=Path,required=True)
    pred.add_argument('--selection',type=Path,required=True);pred.add_argument('--design-json',required=True)
    args=parser.parse_args()
    if args.stage=='predict':
        from mamyshev_ml.v42_release import load_release_evaluator
        result=load_release_evaluator(args.model,args.selection).evaluate(json.loads(args.design_json))
    else:result={'freeze':freeze,'compare':compare,'evaluate':run_evaluation_safely}[args.stage]()
    print(json.dumps({k:v for k,v in result.items() if k not in ('candidates','data_hashes','sources','data_metadata')},indent=2,allow_nan=False))

if __name__=='__main__':main()
