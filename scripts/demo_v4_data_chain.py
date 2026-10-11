#!/usr/bin/env python3
"""Bounded synthetic scan demonstration and read-only import of one old real run."""
import argparse
import csv
import json
from pathlib import Path
import sys
import time
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from mamyshev_ml.v4_evaluators import FEATURES, ROOT, SyntheticEvaluator, RecordedEvaluator, import_safe_result
from mamyshev_ml.v4_scan import execute_scan, make_plan, plot_scan, read_saved_waveform, write_plan
from mamyshev_ml.v4_store import V4Store


def main():
    parser = argparse.ArgumentParser(); parser.add_argument("--out", type=Path, required=True); args = parser.parse_args()
    started = time.monotonic(); out = args.out; out.mkdir(parents=True, exist_ok=False)
    store = V4Store(out / "evaluations.sqlite"); evaluator = SyntheticEvaluator()
    one = make_plan(method="grid", axes={"pump_power_W": [3,4,5,6,7]}, fixed={"filter_offset_nm":10,"filter2_bw_nm":3,"gain_length_m":4})
    write_plan(one, out / "plan_1d.json")
    budget = {"max_new_attempts": 5, "total_wall_s": 60}; stop = out / "STOP_synthetic"
    cancelled = execute_scan(store, one, evaluator, scan_id="synthetic_1d", budget=budget, stop_path=stop, cancel_after=2)
    assert cancelled["status"] == "cancelled" and cancelled["new_attempts"] == 2
    # Explicit demonstration of operator-cleared between-design STOP. Never a live lock.
    stop.unlink()
    resumed = execute_scan(store, one, evaluator, scan_id="synthetic_1d", budget=budget, stop_path=stop)
    assert resumed["status"] == "completed" and resumed["new_attempts"] == 5 and resumed["spent_wall_s"] >= cancelled["spent_wall_s"]
    skipped = execute_scan(store, one, evaluator, scan_id="synthetic_1d", budget=budget, stop_path=stop)
    assert skipped["new_attempts_this_invocation"] == 0
    export1 = store.export_scan("synthetic_1d", out / "export_1d"); plots1 = plot_scan(store, one, "synthetic_1d", out / "plots_1d")
    two = make_plan(method="grid", axes={"filter_offset_nm":[8,10,12],"filter2_bw_nm":[2,3,4]}, fixed={"pump_power_W":4,"gain_length_m":4})
    write_plan(two, out / "plan_2d.json")
    result2 = execute_scan(store, two, evaluator, scan_id="synthetic_2d", budget={"max_new_attempts":9,"total_wall_s":60}, stop_path=stop)
    export2 = store.export_scan("synthetic_2d", out / "export_2d"); plots2 = plot_scan(store, two, "synthetic_2d", out / "plots_2d")
    four = make_plan(method="grid", axes={"pump_power_W":[3,4],"filter_offset_nm":[9,10],"filter2_bw_nm":[2,3],"gain_length_m":[3.9,4.]},fixed={})
    lhs = make_plan(method="lhs", count=5, seed=11, fixed={}); random = make_plan(method="random", count=5, seed=11, fixed={})
    for name, plan in (("grid4d",four),("lhs4d",lhs),("random4d",random)): write_plan(plan,out / ("plan_"+name+".json"))
    with (out / "candidates.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=FEATURES); writer.writeheader()
        writer.writerows([one["designs"][0]["design_config"], one["designs"][0]["design_config"], one["designs"][1]["design_config"]])
    imported_plan = make_plan(method="csv", csv_path=out / "candidates.csv"); write_plan(imported_plan,out / "plan_csv_deduplicated.json")
    assert imported_plan["duplicates_removed"] == 1
    old_path = ROOT / "reports/local/phase2/config_waveform_validation_001/config_waveform_001/final_result.json"
    old = import_safe_result(old_path); store.save_evaluation(old)
    recorded = RecordedEvaluator(store, old["identity"]).evaluate(old["design"])
    assert recorded["targets"] == old["targets"] and recorded["run_id"] == "config_waveform_001"
    waveform = read_saved_waveform(old, out / "historical_mat_read")
    no_waveform = read_saved_waveform(evaluator.evaluate(one["designs"][0]["design_config"]), out / "must_not_create_synthetic_waveform")
    assert no_waveform["status"] == "not_available" and not (out / "must_not_create_synthetic_waveform").exists()
    report = {"kind":"V4_synthetic_scan_and_read_only_import_demo", "cancelled":cancelled,"resumed":resumed,"second_resume":skipped,
              "grid2d":result2,"exports":[export1,export2],"plots":plots1+plots2,"historical_import":old,
              "historical_waveform_read":waveform,"synthetic_waveform":no_waveform,"full_gmmnlse_runs":0,
              "matlab_processes":0,"synthetic_logical_calls":evaluator.calls,"synthetic_unique_computations":evaluator.unique_computations,
              "planned_only":{"grid4d":four["unique_designs"],"lhs":lhs["unique_designs"],"random":random["unique_designs"],"csv":imported_plan["unique_designs"]},
              "database_counts":{name:store.db.execute(f"SELECT count(*) FROM {name}").fetchone()[0] for name in ("designs","evaluations","predictions","attempts")},
              "elapsed_s":time.monotonic()-started,"physical_state":"undetermined","eligible_as_validated_training_truth":False}
    (out / "demo_report.json").write_text(json.dumps(report,ensure_ascii=False,indent=2,allow_nan=False)+"\n")
    store.close(); print(json.dumps({"report":str(out / "demo_report.json"),"elapsed_s":report["elapsed_s"],"new_real_runs":0},indent=2))


if __name__ == "__main__": main()
