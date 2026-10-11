#!/usr/bin/env python3
"""Plan-first V4 scan CLI. No command defaults to execution."""
import argparse
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from mamyshev_ml.v4_evaluators import GMMNLSEEvaluator, RecordedEvaluator, SurrogateEvaluator, SyntheticEvaluator, import_safe_result
from mamyshev_ml.v4_scan import execute_scan, make_plan, plot_scan, read_saved_waveform, write_plan
from mamyshev_ml.v4_store import V4Store


def load_frozen_surrogate(model_path, selection_path, model_identity=None):
    """Verify the local freeze before enabling its class imports or deserializing."""
    from mamyshev_ml.v4_roles import PACKAGE, verify_frozen
    frozen = verify_frozen(model_path, selection_path)
    identity = dict(model_identity) if model_identity is not None else {
        "model_id": f"v4_{frozen['model_family']}_n{frozen['n_train']}_order{frozen['production_order']}",
        "sha256": frozen["model_sha256"]}
    if not identity.get("model_id") or identity.get("sha256") != frozen["model_sha256"]:
        raise ValueError("Prediction model identity does not match the verified frozen weights")
    reference = (PACKAGE / "reference").resolve()
    loaded_class_module = sys.modules.get("models_v4")
    if loaded_class_module is not None and Path(loaded_class_module.__file__).resolve() != reference / "models_v4.py":
        raise ValueError("models_v4 was loaded from an unexpected, unverified location")
    if str(reference) not in sys.path:
        sys.path.insert(0, str(reference))
    import joblib
    return SurrogateEvaluator(joblib.load(Path(model_path).resolve()), identity)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    plan = sub.add_parser("plan"); plan.add_argument("--spec", type=Path, required=True); plan.add_argument("--out", type=Path, required=True)
    run = sub.add_parser("run"); run.add_argument("--plan", type=Path, required=True); run.add_argument("--db", type=Path, required=True)
    run.add_argument("--scan-id", required=True); run.add_argument("--evaluator", choices=["synthetic", "recorded", "surrogate", "gmmnlse"], required=True)
    run.add_argument("--execute", action="store_true"); run.add_argument("--execute-real", action="store_true")
    run.add_argument("--max-new-attempts", type=int, default=0); run.add_argument("--total-wall-s", type=float, default=60)
    run.add_argument("--stop", type=Path, required=True); run.add_argument("--identity", type=Path)
    run.add_argument("--authorization", type=Path); run.add_argument("--batch-dir", type=Path)
    run.add_argument("--trusted-model", type=Path); run.add_argument("--model-identity", type=Path)
    run.add_argument("--selection", type=Path, help="Required frozen selection JSON for surrogate execution")
    run.add_argument("--matlab", default="/Applications/MATLAB_R2025a.app/bin/matlab")
    for command in ("export", "plot"):
        p = sub.add_parser(command); p.add_argument("--db", type=Path, required=True); p.add_argument("--scan-id", required=True); p.add_argument("--out", type=Path, required=True)
        if command == "plot": p.add_argument("--plan", type=Path, required=True)
    imp = sub.add_parser("import-final"); imp.add_argument("--db", type=Path, required=True); imp.add_argument("--final", type=Path, required=True)
    wave = sub.add_parser("waveform"); wave.add_argument("--final", type=Path, required=True); wave.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "plan":
        value = make_plan(**json.loads(args.spec.read_text())); write_plan(value, args.out)
    elif args.command == "waveform":
        value = read_saved_waveform(import_safe_result(args.final), args.out)
    else:
        if args.command == "run":
            plan = json.loads(args.plan.read_text())
            if not args.execute:
                print(json.dumps({"action": "plan_only", "plan": plan, "execute_real": False}, indent=2)); return
        store = V4Store(args.db)
        try:
            if args.command == "import-final":
                record = import_safe_result(args.final); value = {"evaluation_id": store.save_evaluation(record), "record": record}
            elif args.command == "export": value = store.export_scan(args.scan_id, args.out)
            elif args.command == "plot": value = plot_scan(store, json.loads(args.plan.read_text()), args.scan_id, args.out)
            else:
                authorization = json.loads(args.authorization.read_text()) if args.authorization else {}
                if args.evaluator == "synthetic": evaluator = SyntheticEvaluator()
                elif args.evaluator == "recorded":
                    if not args.identity: parser.error("recorded requires --identity exact identity JSON")
                    evaluator = RecordedEvaluator(store, json.loads(args.identity.read_text()))
                elif args.evaluator == "surrogate":
                    if not args.trusted_model or not args.selection: parser.error("surrogate requires explicit trusted model and frozen --selection")
                    identity = json.loads(args.model_identity.read_text()) if args.model_identity else None
                    evaluator = load_frozen_surrogate(args.trusted_model, args.selection, identity)
                else:
                    if not args.authorization or not args.batch_dir: parser.error("gmmnlse requires separate authorization JSON and batch directory")
                    evaluator = GMMNLSEEvaluator(plan=plan, authorization=authorization, batch_dir=args.batch_dir, execute_real=args.execute_real, matlab=args.matlab)
                value = execute_scan(store, plan, evaluator, scan_id=args.scan_id,
                    budget={"max_new_attempts": args.max_new_attempts, "total_wall_s": args.total_wall_s},
                    stop_path=args.stop, authorization=authorization)
        finally:
            store.close()
    print(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
