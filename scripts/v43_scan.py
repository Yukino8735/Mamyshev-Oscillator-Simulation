#!/usr/bin/env python3
"""Explicit frozen V4.2 Prediction routing through the existing V4 scan/store."""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from mamyshev_ml.v43_adapter import load_application_evaluator
from mamyshev_ml.v4_scan import execute_scan, make_plan, plot_scan, write_plan
from mamyshev_ml.v4_store import V4Store


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    predict = sub.add_parser("predict")
    predict.add_argument("--input", type=Path, required=True)
    predict.add_argument("--out", type=Path, required=True)
    plan = sub.add_parser("plan")
    plan.add_argument("--spec", type=Path, required=True)
    plan.add_argument("--out", type=Path, required=True)
    run = sub.add_parser("run")
    run.add_argument("--plan", type=Path, required=True)
    run.add_argument("--db", type=Path, required=True)
    run.add_argument("--scan-id", required=True)
    run.add_argument("--execute", action="store_true")
    run.add_argument("--max-new-attempts", type=int, default=0)
    run.add_argument("--total-wall-s", type=float, default=60)
    run.add_argument("--stop", type=Path, required=True)
    for command in (predict, run):
        command.add_argument("--model", type=Path, required=True)
        command.add_argument("--selection", type=Path, required=True)
    for command in ("export", "plot"):
        child = sub.add_parser(command)
        child.add_argument("--db", type=Path, required=True)
        child.add_argument("--scan-id", required=True)
        child.add_argument("--out", type=Path, required=True)
        if command == "plot":
            child.add_argument("--plan", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "plan":
        value = make_plan(**json.loads(args.spec.read_text()))
        write_plan(value, args.out)
    elif args.command == "predict":
        evaluator = load_application_evaluator(args.model, args.selection)
        designs = json.loads(args.input.read_text())
        value = evaluator.evaluate_many(designs) if isinstance(designs, list) else evaluator.evaluate(designs)
        args.out.parent.mkdir(parents=True, exist_ok=True)
        with args.out.open("x") as stream:
            stream.write(json.dumps(value, indent=2, allow_nan=False) + "\n")
    else:
        if args.command == "run":
            plan = json.loads(args.plan.read_text())
            if not args.execute:
                print(json.dumps({"action": "plan_only", "plan": plan,
                    "model": str(args.model), "selection": str(args.selection), "execute_real": False}, indent=2))
                return
        store = V4Store(args.db)
        try:
            if args.command == "export":
                value = store.export_scan(args.scan_id, args.out)
            elif args.command == "plot":
                value = plot_scan(store, json.loads(args.plan.read_text()), args.scan_id, args.out,
                    source_title="Repository-guided synthetic surrogate prediction",
                    limitation_note="Diagnostic intervals limited: overall 1936/2048; near_slice 216/256. No physics or safety guarantee.")
            else:
                evaluator = load_application_evaluator(args.model, args.selection)
                before = store.db.execute("SELECT COUNT(*) FROM evaluations").fetchone()[0]
                value = execute_scan(store, plan, evaluator, scan_id=args.scan_id,
                    budget={"max_new_attempts": args.max_new_attempts, "total_wall_s": args.total_wall_s},
                    stop_path=args.stop)
                after = store.db.execute("SELECT COUNT(*) FROM evaluations").fetchone()[0]
                if before != after:
                    raise RuntimeError("Prediction scan unexpectedly changed Evaluation count")
                value.update(evaluations_before=before, evaluations_after=after,
                    prediction_rows=evaluator.prediction_rows, execute_real=False)
        finally:
            store.close()
    print(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
