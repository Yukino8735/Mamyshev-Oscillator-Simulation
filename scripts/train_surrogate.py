#!/usr/bin/env python3
"""Train a separate source-emulation model from explicit data and grouped splits.

No command generates labels, starts MATLAB, or changes a frozen Demo model.
Joblib prediction requires an explicit trust decision for the supplied local model.
"""
import argparse
import json
from pathlib import Path
import sqlite3
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from mamyshev_ml.v4_evaluators import FEATURES, TARGETS, validate_design
from mamyshev_ml.v4_training import (export_records, fit_model, load_model, make_split,
                                    read_records)


def write(path, value):
    with Path(path).open("x") as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write("\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    identities = sub.add_parser("identities", help="List exact available DB identities; no auto-selection")
    identities.add_argument("--db", type=Path, required=True)
    identities.add_argument("--out", type=Path, required=True)
    for command in ("export", "split", "fit"):
        p = sub.add_parser(command)
        source = p.add_mutually_exclusive_group(required=True)
        source.add_argument("--db", type=Path)
        source.add_argument("--csv", type=Path)
        p.add_argument("--identity", type=Path, required=True, help="One exact identity object, not the inventory list")
        p.add_argument("--out", type=Path, required=True)
        if command == "split":
            p.add_argument("--seed", type=int, default=0)
            p.add_argument("--development-fraction", type=float, default=.2)
        if command == "fit":
            p.add_argument("--split", type=Path, required=True)
            p.add_argument("--model-id", required=True)
    predict = sub.add_parser("predict")
    predict.add_argument("--model-dir", type=Path, required=True)
    predict.add_argument("--trusted-local", action="store_true")
    predict.add_argument("--design", type=Path, required=True)
    predict.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "identities":
        with sqlite3.connect(args.db.resolve().as_uri() + "?mode=ro", uri=True) as db:
            values = {}
            for encoded, in db.execute("SELECT record_json FROM evaluations"):
                identity = json.loads(encoded)["identity"]
                key = json.dumps(identity, sort_keys=True)
                values[key] = identity
        result = {"identities": [values[key] for key in sorted(values)],
                  "instruction": "Select exactly one identity object into a separate JSON file; never mix sources."}
        write(args.out, result)
    elif args.command == "predict":
        design = validate_design(json.loads(args.design.read_text()))
        model, metadata = load_model(args.model_dir, trusted_local=args.trusted_local)
        values = model.predict([[design[key] for key in FEATURES]])[0]
        result = {"kind": "Prediction", "design": design, "model_id": metadata["model_id"],
                  "targets": dict(zip(TARGETS, values.tolist())), "units": metadata["units"],
                  "training_source_identity": metadata["source_identity"],
                  "eligible_as_validated_training_truth": False}
        write(args.out, result)
    else:
        identity = json.loads(args.identity.read_text())
        records, audit = read_records(identity=identity, db=args.db, csv_path=args.csv)
        if not records:
            raise ValueError("No task-qualified records for this exact identity: " + json.dumps(audit))
        if args.command == "export":
            result = export_records(records, args.out, identity=identity)
            result["selection_audit"] = audit
        elif args.command == "split":
            result = make_split(records, seed=args.seed, development_fraction=args.development_fraction)
            write(args.out, result)
        else:
            result = fit_model(records, json.loads(args.split.read_text()), args.out,
                               identity=identity, model_id=args.model_id)
            result["selection_audit"] = audit
    print(json.dumps(result, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
