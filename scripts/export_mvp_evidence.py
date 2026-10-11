#!/usr/bin/env python3
"""Export saved evidence only: no project/model/oracle imports or predictions.

The fixed closeout destination is exclusive. Original results, figures, labels,
weights and ledgers are only read. Run through the existing closeout budget.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports/local/mvp_closeout_001/evidence"
V4 = "reports/local/accuracy_v4_001"
V41 = "reports/local/accuracy_v4_1_001"
V42 = "reports/local/accuracy_v4_2_001"
V43 = "reports/local/application_v4_3_001"
MODEL_SHA = "c236c2d2dd6cb5b59e32bd5ab4f8c3823f7fefc10d7571108a3d6339ee46b2e0"
TARGETS = ("compressed_energy_nJ", "compressed_duration_fs", "compressed_peak_power_MW")
SOURCES: dict[str, dict] = {}


def source(path: str) -> Path:
    p = ROOT / path
    raw = p.read_bytes()
    SOURCES[path] = {"sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw)}
    return p


def read(path: str):
    return json.loads(source(path).read_text())


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def close(a: float, b: float) -> bool:
    return math.isfinite(a) and math.isfinite(b) and math.isclose(a, b, rel_tol=1e-12, abs_tol=1e-12)


def write(path: Path, value) -> None:
    with path.open("x") as f:
        json.dump(value, f, ensure_ascii=False, indent=2, allow_nan=False)
        f.write("\n")


def coverage(saved: dict) -> dict:
    count = round(saved["n"] * saved["joint_coverage"])
    require(close(count / saved["n"], saved["joint_coverage"]), "noninteger coverage")
    return {"covered": count, "n": saved["n"], "fraction": saved["joint_coverage"],
            "wilson95": saved["joint_wilson95"]}


def render_tables(summary: dict) -> str:
    a, b, c = (summary[k] for k in ("A_v42_supervised_accuracy", "B_v4_cold_start_search", "C_v43_frozen_application"))
    rows = ["<!-- Generated from evidence_summary.json by scripts/export_mvp_evidence.py. -->",
            "### A. Frozen V4.2 supervised accuracy (saved synthetic evaluation)", "",
            f"{a['training_designs']} training designs; {a['test_designs']} new test designs in the fixed stratified mixture. "
            "All saved test points met the stated tolerances; this is not zero error or real-solver accuracy.", "",
            "| Target | MAE | P95 absolute error | P95 relative error | Tolerance |",
            "|---|---:|---:|---:|---|"]
    for name, m in a["targets"].items():
        t = a["tolerances"][name]
        rows.append(f"| {name} | {m['mae']:.9g} {m['unit']} | {m['absolute_error_quantiles']['P95']:.9g} {m['unit']} | "
                    f"{100*m['P95_relative_error']:.6g}% | max({t['absolute']:g} {m['unit']}, {100*t['relative']:g}% of truth) |")
    rows += ["", "Intervals remain **limited**: saved empirical joint coverage is "
             + "; ".join(f"{group} {item['covered']}/{item['n']} ({100*item['fraction']:.6g}%)"
                         for group, item in a["interval_coverage"].items())
             + ". They are not physical safety guarantees.", "",
             "### B. Historical V4 cold-start GP/random comparison", "",
             "A separate experiment: 4 scenarios × 3 paired seeds × 2 strategies × 64 logical evaluations. "
             "The first 16 evaluations were initial exploration. This did not use the V4.2 trained model.", "",
             "| Scenario / objective | GP final best, seeds 11 / 22 / 33 | Random final best, seeds 11 / 22 / 33 |",
             "|---|---|---|"]
    for group in b["by_scenario"]:
        vals = {m: " / ".join(f"{v['best_actual_feasible']['value']:.9g}" for v in group[m]) for m in ("gp", "random")}
        rows.append(f"| {group['scenario_id']} ({group['unit']}, {group['direction']}) | {vals['gp']} | {vals['random']} |")
    rows += ["", f"Saved accounting: {b['logical_events']} logical events, {b['unique_computations']} unique computations, "
             f"{b['cache_hits']} cache hits. Three seeds support a finite descriptive comparison, not general superiority.", "",
             "### C. V4.3 frozen-model application with a 1024-design training prior", "",
             "Each method received 8 confirmations per scenario, with the same known T2 incumbent. "
             "64 events / 63 new designs / 1 cache hit; one seed, no significance claim. "
             "Values below are analytic synthetic evaluations, not MATLAB or experimental measurements.", "",
             "| Scenario | Method | Unit | Shared T2 incumbent | Best new confirmed point | Final best including incumbent | Improvement |",
             "|---|---|---|---:|---:|---:|---:|"]
    for r in c["comparisons"]:
        rows.append(f"| {r['scenario_id']} | {r['method']} | {r['unit']} | {r['incumbent']['value']:.9g} | "
                    f"{r['best_new']['value']:.9g} | {r['final_including_incumbent']['value']:.9g} | {r['improvement_percent']:.6f}% |")
    rows += ["", "Improvement uses only the shared known T2 incumbent as denominator, with the objective's direction. "
             "The random method retains its incumbent; weaker new samples did not make its final best worse. "
             "S1–S3 maximize peak power; S4 minimizes duration. Neither the full candidate pool nor the continuous domain was exhaustively evaluated.", "",
             "**Real-solver generalization error and real-simulation savings: not measured (`null`).** "
             "The current model does not emulate a validated full GMMNLSE response.", ""]
    return "\n".join(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--update-readme", action="store_true",
                        help="Replace only the existing MVP_RESULTS_START/END block with the generated saved-result tables")
    args = parser.parse_args()
    require(not OUT.exists(), "Evidence output already exists; do not overwrite or choose another batch.")
    readme = ROOT / "README.md"
    before = readme.read_text() if args.update_readme else None
    start, end = "<!-- MVP_RESULTS_START -->", "<!-- MVP_RESULTS_END -->"
    if args.update_readme:
        require(before.count(start) == 1 and before.count(end) == 1,
                "README must contain exactly one existing results marker pair")
        require(before.index(start) < before.index(end), "README results markers reversed")
    release = read(f"{V42}/release/selection.json")
    source(f"{V42}/release/model.joblib")
    protocol = read(f"{V42}/protocol.json")
    final = read(f"{V42}/evaluation/final_metrics.json")
    v42 = read(f"{V42}/summary.json")
    for path, expected in ((f"{V42}/release/model.joblib", MODEL_SHA),
                           (f"{V42}/protocol.json", release["protocol_sha256"]),
                           (f"{V42}/evaluation/final_metrics.json", release["final_metrics_sha256"]),
                           (f"{V42}/summary.json", release["evaluation_summary_sha256"])):
        require(SOURCES[path]["sha256"] == expected, f"Frozen identity changed: {path}")
    require(release["n_train"] == 1024 and final["metrics"]["n"] == 2048, "V4.2 scope changed")
    a = {"model_id": release["selected"], "model_sha256": MODEL_SHA,
         "protocol_id": protocol["protocol_id"], "protocol_sha256": release["protocol_sha256"],
         "source_kind": release["source_kind"], "training_designs": release["n_train"],
         "test_designs": final["metrics"]["n"], "distribution_weights": final["distribution_weights"],
         "targets": final["metrics"]["targets"], "joint_passed": final["metrics"]["joint_passed"],
         "tolerance_rule": protocol["metrics_protocol"]["tolerance_rule"],
         "tolerances": protocol["metrics_protocol"]["tolerances"],
         "interval_status": "limited", "interval_coverage": {
             "overall": coverage(final["intervals"]),
             "near_slice": coverage(final["group_intervals"]["near_slice"]),
             "core": coverage(final["group_intervals"]["reference_core"])},
         "scope": final["scope"], "test_rescored": False}
    a["evidence_paths"] = [f"{V42}/release/selection.json", f"{V42}/release/model.joblib",
                           f"{V42}/protocol.json", f"{V42}/evaluation/final_metrics.json", f"{V42}/summary.json"]

    old = read(f"{V4}/search/search_summary.json")
    oldplan = read(f"{V4}/search/frozen_search_protocol.json")
    experiments = read(f"{V4}/search/experiment_summaries.json")
    require(len(experiments) == 24 and all(e["logical_queries"] == 64 and e["status"] == "completed" for e in experiments), "Old search scope changed")
    b = {"source_kind": old["source"], "protocol": oldplan["schema_version"],
         "protocol_sha256": SOURCES[f"{V4}/search/frozen_search_protocol.json"]["sha256"],
         "model": "independent cold-start Gaussian process per experiment; not V4.2 surrogate",
         "scenario_count": 4, "seeds": oldplan["seeds"], "strategies": oldplan["methods"],
         "queries_per_experiment": oldplan["queries_per_experiment"], "initial_queries": oldplan["initial_queries"],
         "logical_events": old["logical_evaluation_events"], "unique_computations": old["unique_evaluator_computations"],
         "cache_hits": old["cache_hits"], "by_scenario": [], "limitations": old["limitations"], "rerun": False}
    b["evidence_paths"] = [f"{V4}/search/search_summary.json", f"{V4}/search/frozen_search_protocol.json",
                           f"{V4}/search/experiment_summaries.json"]
    for scenario in oldplan["scenarios"]:
        item = {"scenario_id": scenario["id"], "objective": scenario["objective"]["target"],
                "direction": scenario["objective"]["direction"],
                "unit": "fs" if scenario["objective"]["direction"] == "minimize" else "MW"}
        for method in oldplan["methods"]:
            subset = sorted((e for e in experiments if e["scenario_id"] == scenario["id"] and e["method"] == method), key=lambda e: e["seed"])
            require([e["seed"] for e in subset] == [11, 22, 33], "Missing paired seeds")
            item[method] = [{"seed": e["seed"], "best_actual_feasible": e["best_actual_feasible"]["64"]} for e in subset]
        b["by_scenario"].append(item)

    cand = read(f"{V43}/candidates/candidate_summary.json")
    plan = read(f"{V43}/candidates/frozen_candidate_plan.json")
    with source(f"{V43}/candidates/candidate_results.csv").open(newline="") as f:
        rows = list(csv.DictReader(f))
    require(len(rows) == 64 and cand["logical_queries"] == 64 and cand["unique_queried_designs"] == 63 and cand["cache_hits"] == 1, "Candidate accounting changed")
    require(plan["model_identity"]["sha256"] == MODEL_SHA, "Candidate model mismatch")
    scenarios = {s["id"]: s for s in plan["scenarios"]}
    c = {"model_sha256": MODEL_SHA, "frozen_plan_hash": plan["plan_hash"],
         "seed": plan["seed"], "prior_training_designs": cand["prior_model_training_designs"],
         "logical_events": cand["logical_queries"], "new_unique_designs": cand["unique_queried_designs"],
         "cache_hits": cand["cache_hits"], "failed_queries": cand["failed_queries"],
         "per_method_per_scenario_queries": plan["per_method_maximum"], "comparisons": [],
         "new_confirmation_performed_in_closeout": False,
         "limitation": "one seed with 1024-design training prior; finite synthetic confirmation; no general superiority or physical-optimum claim"}
    c["evidence_paths"] = [f"{V43}/candidates/candidate_summary.json", f"{V43}/candidates/frozen_candidate_plan.json",
                           f"{V43}/candidates/candidate_results.csv"]
    for saved in cand["comparisons"]:
        sid, method = saved["scenario_id"], saved["method"]
        scenario = scenarios[sid]
        objective, direction = scenario["objective"]["target"], scenario["objective"]["direction"]
        incumbent = plan["common_incumbents"][sid]
        require(incumbent == saved["common_incumbent"], "Incumbent mismatch")
        queried = [r for r in rows if r["scenario_id"] == sid and r["method"] == method]
        feasible = [r for r in queried if r["status"] == "completed" and r["actual_feasible"] == "True"]
        require(len(queried) == 8 and len(feasible) == saved["actual_feasible"], "Candidate rows mismatch")
        # Reproduce the already-frozen objective, not a new ranking experiment.
        best = min(feasible, key=lambda r: (float(r[objective + "_actual"]) * (1 if direction == "minimize" else -1), r["design_id"]))
        best_new = {"design_id": best["design_id"], "value": float(best[objective + "_actual"]),
                    "targets": {t: float(best[t + "_actual"]) for t in TARGETS}}
        require(best_new["design_id"] == saved["best_newly_evaluated"]["design_id"] and close(best_new["value"], saved["best_newly_evaluated"]["value"]), "Saved candidate best mismatch")
        better = best_new["value"] < incumbent["value"] if direction == "minimize" else best_new["value"] > incumbent["value"]
        final_best = best_new if better else incumbent
        require(final_best["design_id"] == saved["best_evaluated_on_synthetic"]["design_id"] and close(final_best["value"], saved["best_evaluated_on_synthetic"]["value"]), "Final including incumbent mismatch")
        improvement = (final_best["value"] - incumbent["value"]) / abs(incumbent["value"]) * (100 if direction == "maximize" else -100)
        c["comparisons"].append({"scenario_id": sid, "method": method, "objective": objective, "direction": direction,
                                 "unit": "fs" if direction == "minimize" else "MW", "queries": 8,
                                 "actual_feasible": len(feasible), "incumbent": incumbent, "best_new": best_new,
                                 "final_including_incumbent": final_best, "improvement_percent": improvement,
                                 "denominator": "shared_existing_T2_training_incumbent_only"})

    selection4 = read(f"{V4}/models/selection.json")
    evaluation4 = read(f"{V4}/evaluation/summary.json")
    summary41 = read(f"{V41}/summary/summary.json")
    costs = {"do_not_sum": "Rows overlap through reused training, validation and inherited models; historical pipeline walls are not label-generation or real-solver savings.",
             "early_pilot": {"train_labels_seen": selection4["package_prior_pilot_train_labels_seen"], "validation_labels_seen": selection4["package_prior_pilot_validation_labels_seen"]},
             "v4_local_selection": {"unique_train": selection4["unique_train_labels_used_in_local_selection"], "validation": selection4["unique_validation_labels_used"], "fits": selection4["fit_count"]},
             "v4_evaluation": {k: evaluation4[k] for k in ("calibration_rows", "test_rows", "challenge_rows")},
             "v4_search": {"logical": old["logical_evaluation_events"], "unique": old["unique_evaluator_computations"], "cached": old["cache_hits"]},
             "v41": {"new_by_role": summary41["new_oracle_by_role"], "fits": summary41["new_candidate_fits"]},
             "v42": {k: v42[k] for k in ("training_union_unique", "old_reference_validation_labels", "old_special_development_labels", "new_training_labels", "new_development_labels", "new_calibration_labels", "new_test_labels", "new_candidate_fit_attempts")},
             "v43": {"new_train_dev_cal_test": 0, "fits": 0, "logical_candidate": 64, "new_unique_candidate": 63, "cached": 1}, "historical_external_wall_seconds": {}}
    costs["count_source_paths"] = {"early_pilot_and_v4_local_selection": f"{V4}/models/selection.json",
                                   "v4_evaluation": f"{V4}/evaluation/summary.json",
                                   "v4_search": f"{V4}/search/search_summary.json",
                                   "v41": f"{V41}/summary/summary.json", "v42": f"{V42}/summary.json",
                                   "v43": f"{V43}/candidates/candidate_summary.json"}
    for label, base in (("v4", V4), ("v41", V41), ("v42", V42), ("v43", V43)):
        ledger = read(f"{base}/budget_ledger.json")
        totals = {}
        for attempt in ledger["attempts"]:
            totals[attempt["category"]] = totals.get(attempt["category"], 0.0) + attempt["charged_s"]
        costs["historical_external_wall_seconds"][label] = {"source": f"{base}/budget_ledger.json", "categories": totals}

    figures = [
        (f"{V42}/analysis/selected_test_scatter.png", "v42_accuracy.png", "Saved V4.2 synthetic test; not rescored"),
        (f"{V42}/analysis/energy_pass_comparison.png", "v42_representation.png", "Saved development representation comparison"),
        (f"{V43}/demonstration/heatmap/plots/compressed_peak_power_MW.png", "v43_prediction_heatmap.png", "81 saved surrogate predictions; no evaluator labels"),
        (f"{V43}/analysis/candidate_comparison.png", "v43_candidate_confirmation.png", "Saved finite synthetic confirmations; not real solver"),
    ]
    for original, _, _ in figures:
        source(original)
    source("scripts/export_mvp_evidence.py")
    summary = {"schema_version": "mvp_saved_evidence_v1", "created_utc": datetime.now(timezone.utc).isoformat(),
               "operation": "read_saved_results_only", "new_labels": 0, "new_fit_calibration_search_scoring": 0,
               "MATLAB_starts": 0, "A_v42_supervised_accuracy": a, "B_v4_cold_start_search": b,
               "C_v43_frozen_application": c, "historical_cost_accounting": costs,
               "real_solver_generalization_error": None, "real_simulation_savings": None,
               "real_metrics_missing_reason": "not_measured; synthetic experiments do not measure real GMMNLSE generalization or savings",
               "physical_state": "undetermined", "numerical_validation": "not_verified",
               "eligible_as_validated_training_truth": False, "source_files": SOURCES, "figures": []}
    OUT.mkdir(exist_ok=False)
    (OUT / "figures").mkdir()
    for original, name, caption in figures:
        raw = (ROOT / original).read_bytes()
        destination = OUT / "figures" / name
        with destination.open("xb") as f:
            f.write(raw)
        summary["figures"].append({"source": original, "copy": destination.relative_to(ROOT).as_posix(),
                                   "sha256": SOURCES[original]["sha256"], "byte_identical": True, "caption": caption})
    write(OUT / "evidence_summary.json", summary)
    # The display tables consume the actual serialized summary, not duplicate constants.
    reread = json.loads((OUT / "evidence_summary.json").read_text())
    with (OUT / "readme_tables.md").open("x") as f:
        f.write(render_tables(reread))
    if args.update_readme:
        require(readme.read_text() == before, "README changed during export; refusing to replace it")
        tables = (OUT / "readme_tables.md").read_text()
        head, rest = before.split(start, 1)
        _, tail = rest.split(end, 1)
        after = head + start + "\n\n" + tables.rstrip() + "\n\n" + end + tail
        readme.write_text(after)
        write(OUT / "readme_update.json", {
            "path": "README.md", "replacement_scope": "MVP_RESULTS_START through MVP_RESULTS_END interior only",
            "before_sha256": hashlib.sha256(before.encode()).hexdigest(),
            "after_sha256": hashlib.sha256(after.encode()).hexdigest(),
            "source_tables_sha256": hashlib.sha256(tables.encode()).hexdigest(),
            "outside_marker_text_unchanged": True})
    print(json.dumps({"status": "completed", "output": OUT.relative_to(ROOT).as_posix(),
                      "new_labels": 0, "new_predictions": 0, "reopened_test": False}))


if __name__ == "__main__":
    main()
