"""One fixed 10k synthetic fit; no tuning, retry, or GMMNLSE execution.

Geometry, evaluator, model class and metrics reuse their immutable predecessors.
All per-design data remain in the exclusive ignored experiment directory.
"""
from __future__ import annotations

from collections import Counter
import csv
import datetime as dt
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import random
import time
import traceback
import warnings

import joblib
import numpy as np
from threadpoolctl import threadpool_limits

from .v41_sampling import _draw, _csv_x_rows, canonical, canonical_id, in_core, write_role
from .v43_candidates import project_exclusions
from .v4_evaluators import SyntheticEvaluator, validate_design
from .v4_store import V4Store
from .v4_ml import (LogSurrogate, matrices, predictions_csv, protocol as metric_protocol,
                    joint_log_calibration, prediction_intervals, intervals_with_units)
from .v41_experiment import constraint_statistics
from .v42_models import count_statistics, development_gate, inspect_model, matrix_sha256

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "reports/local/demo_10k_release_001"
CONFIG = ROOT / "configs/demo10k_protocol.json"
PACKAGE = ROOT / "mamyshev_accuracy_v4"
FEATURES = ("pump_power_W", "filter_offset_nm", "filter2_bw_nm", "gain_length_m")
TARGETS = ("compressed_energy_nJ", "compressed_duration_fs", "compressed_peak_power_MW")
GROUPS = ("reference_core", "reference_expanded", "slice", "near_slice", "outer_faces", "corners")
ROLES = ("train", "development", "calibration", "final_test")
MODEL_ID = "demo_10k_v1"
SOURCE = "repository_guided_synthetic"
PINNED = {
    "reference/models_v4.py": "46f9779b878d195b601930446cce3ec5335f694ef219f28c2ae728a353590b11",
    "reference/oracle.py": "98df4bade605db85f2d384f8bfebe69ceb4716120f729d3d460819ead25ade8e",
    "configs/generator_recipe.json": "4cc26ad801213d01554d96846a7d10f5d6d3260c07e099e8df9441c357d4c770",
    "configs/domain.json": "66802d60ab841a6ca5f7530147c80cbd465936ccef8b82b411f38d7a126ba668",
}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def now():
    return dt.datetime.now(dt.timezone.utc).isoformat()


def exclusive(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x") as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write("\n")


def event(path, value):
    with Path(path).open("a") as stream:
        stream.write(canonical(value) + "\n")
        stream.flush()
        os.fsync(stream.fileno())


def dependencies():
    return {"python": platform.python_version(), "packages": {
        name: importlib.metadata.version(name) for name in ("numpy", "scipy", "scikit-learn", "joblib", "threadpoolctl")}}


def validate_protocol(p):
    expected_counts = (10000, 1024, 1024, 2048)
    if (p["protocol_id"] != MODEL_ID or tuple(p["group_order"]) != GROUPS
            or tuple(p["features"]) != FEATURES or tuple(p["targets"]) != TARGETS
            or tuple(p["sampling_seeds"][r] for r in ROLES) != (61001, 61002, 61003, 61004)
            or tuple(sum(p["role_quotas"][r].values()) for r in ROLES) != expected_counts
            or p["parameters"] != {"n_knots": 64, "degree": 3, "knots": "uniform", "interaction_polynomial_degree": 4, "alpha": .001, "log_targets": True}
            or p["new_labels_max"] != 14096 or p["formal_three_target_fit_attempts_max"] != 1):
        raise ValueError("Frozen 10k protocol differs from explicit authorization")
    for role, core, special in (("train", 2500, 1250), ("development", 256, 128),
                               ("calibration", 256, 128), ("final_test", 512, 256)):
        if p["role_quotas"][role] != {g: core if g in GROUPS[:2] else special for g in GROUPS}:
            raise ValueError("Group quotas changed")
    if p["tolerances"] != metric_protocol()["tolerances"]:
        raise ValueError("Error tolerances changed")
    return p


def source_hashes():
    names = ["src/mamyshev_ml/demo10k_experiment.py", "scripts/run_demo10k.py", "configs/demo10k_protocol.json",
             "src/mamyshev_ml/v41_sampling.py", "src/mamyshev_ml/v43_candidates.py",
             "src/mamyshev_ml/v4_evaluators.py", "src/mamyshev_ml/v4_store.py",
             "src/mamyshev_ml/v4_ml.py", "src/mamyshev_ml/v41_experiment.py", "src/mamyshev_ml/v42_models.py",
             "mamyshev_accuracy_v4/reference/metrics_v4.py", "mamyshev_accuracy_v4/configs/accuracy_protocol.json"]
    return {n: sha(ROOT / n) for n in names}


def collect_exclusions(root=ROOT, output=OUT):
    ids, summary = project_exclusions(root, current_output=output)
    paths = [Path(root) / "mamyshev_accuracy_v4/data/candidates_unlabeled_20000.csv"]
    paths += sorted((Path(root) / "reports/local").glob("**/samples/*/inputs.csv"))
    for path in paths:
        if path.resolve().is_relative_to(Path(output).resolve()):
            continue
        count = 0
        for _, old_id, x in _csv_x_rows(path):
            ids.add(canonical_id(x)); count += 1
        if path.name == "candidates_unlabeled_20000.csv" and count != 20000:
            raise ValueError("Expected full existing 20k X-only candidate pool")
        summary["sources"].append({"path": str(path.relative_to(root)), "sha256": sha(path),
            "kind": "X_ID_only_saved_role_or_candidate_pool", "rows": count, "target_columns_selected": False})
    ids.add(canonical_id(dict(zip(FEATURES, (4., 10., 3., 4.)))))
    summary.update(canonical_exclusions=len(ids), pure_unlabeled_pool_also_excluded=True,
                   missing_external_sources="Only locally visible recorded inputs and canonical IDs can be excluded")
    return ids, summary


def sample_rows(role, p, excluded, domain):
    """X-only streams, original V4.1 geometry, shared cross-role exact-ID set."""
    rows, rejected = [], []
    for group in GROUPS:
        stream_identity = [p["sampling_version"], role, p["sampling_seeds"][role], group]
        rng = random.Random(int.from_bytes(hashlib.sha256(canonical(stream_identity).encode()).digest(), "big"))
        accepted = proposed = 0
        while accepted < p["role_quotas"][role][group]:
            if proposed >= p["max_proposals_per_group"]:
                raise RuntimeError("X sampling cap exhausted; no reroll")
            x = validate_design(_draw(group, rng, accepted, domain)); proposed += 1
            did = canonical_id(x)
            reason = ("expanded_inside_core" if group == "reference_expanded" and in_core(x, domain) else
                      "near_equals_exact_slice" if group == "near_slice" and x[FEATURES[0]] == 4 and x[FEATURES[3]] == 4 else
                      "existing_X_or_ID" if did in excluded else None)
            if reason:
                rejected.append({"role": role, "group": group, "proposal": proposed, "design_id": did, "reason": reason})
                continue
            excluded.add(did); accepted += 1
            rows.append({"design_id": did, "role": role, "group": group, "order_in_role": len(rows) + 1, **x})
    return rows, rejected


def score(rows, y, pred, p):
    tags = np.asarray([r["group"] for r in rows])
    groups = {g: count_statistics(y[tags == g], pred[tags == g], p) for g in GROUPS}
    ref = np.isin(tags, GROUPS[:2])
    reference = count_statistics(y[ref], pred[ref], p)
    gate = development_gate(reference, {"historical_core": groups[GROUPS[0]], "expanded_proposal": groups[GROUPS[1]]},
                            {g: groups[g] for g in GROUPS[2:]})
    return {"metrics": count_statistics(y, pred, p), "groups": groups, "reference": reference, "gate": gate}


def query_role(rows, p, out, budget_counts):
    role = rows[0]["role"]; folder = out / "samples" / role
    exclusive(folder / "query.lock", {"started_utc": now(), "role": role, "n_requested": len(rows)})
    if budget_counts["reserved"] + len(rows) > p["new_labels_max"]:
        raise RuntimeError("Label authorization exhausted")
    evaluator = SyntheticEvaluator(seed=0)
    db = V4Store(folder / "evaluations.sqlite")
    labeled = []; started = time.monotonic()
    columns = [*rows[0], *TARGETS, "source_kind", "region"]
    with (folder / "labels.csv").open("x", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns); writer.writeheader()
        try:
            for row in rows:
                did = row["design_id"]
                event(out / "oracle_queries.jsonl", {"event": "reserved", "role": role, "design_id": did, "utc": now()})
                budget_counts["reserved"] += 1
                record = evaluator.evaluate({k: row[k] for k in FEATURES}, design_id=did, request_id=f"demo10k/{role}/{did}")
                values = np.asarray([record["targets"][k] for k in TARGETS], float)
                if (record["job_status"] != "completed" or record["cache_hit"] or record["source_kind"] != SOURCE
                        or not np.isfinite(values).all() or (values <= 0).any()):
                    raise ValueError("Invalid fresh synthetic evaluation; no skipped hard points")
                db.save_evaluation(record)
                label = dict(row, **record["targets"], source_kind=SOURCE, region=row["group"])
                writer.writerow(label); stream.flush(); labeled.append(label)
                budget_counts["completed"] += 1
                event(out / "oracle_queries.jsonl", {"event": "completed", "role": role, "design_id": did,
                      "evaluation_id": record["evaluation_id"], "utc": now()})
        except BaseException as error:
            event(out / "oracle_queries.jsonl", {"event": "failed", "role": role, "utc": now(), "error": repr(error)})
            raise
        finally:
            db.close()
            exclusive(folder / "accounting.json", {"role": role, "new_labels": len(labeled), "oracle_calls": evaluator.calls,
                "unique_computations": evaluator.unique_computations, "cache_hits": evaluator.cache_hits,
                "elapsed_s": time.monotonic() - started, "identity": evaluator.identity, "seed": 0,
                "inputs_sha256": sha(folder / "inputs.csv"), "labels_sha256": sha(folder / "labels.csv")})
    return labeled


def readback(model, path, rows, out):
    """Reuse three saved inputs; no additional labels or model fit."""
    designs = [{k: r[k] for k in FEATURES} for r in rows[:3]]
    x = np.asarray([[d[k] for k in FEATURES] for d in designs])
    expected = model.predict(x); reloaded = joblib.load(path)
    batch = reloaded.predict(x); single = np.vstack([reloaded.predict(x[i:i+1]) for i in range(len(x))])
    exclusive(out / "reload_inputs.json", designs)
    exclusive(out / "reload_predictions.json", batch.tolist())
    with (out / "reload_predictions.csv").open("x", newline="") as stream:
        w = csv.writer(stream); w.writerow([*FEATURES, *TARGETS]); w.writerows(np.column_stack((x, batch)))
    with (out / "reload_predictions.csv").open() as stream:
        csv_back = np.asarray([[float(r[k]) for k in TARGETS] for r in csv.DictReader(stream)])
    json_back = np.asarray(json.loads((out / "reload_predictions.json").read_text()))
    checks = {"joblib_batch": batch, "joblib_single": single, "csv": csv_back, "json": json_back}
    errors = {}
    for name, value in checks.items():
        np.testing.assert_allclose(value, expected, atol=1e-10, rtol=1e-10)
        errors[name] = float(np.max(np.abs(value - expected)))
    exclusive(out / "reload_checks.json", {"passed": True, "distinct_inputs": len(x), "atol": 1e-10,
        "rtol": 1e-10, "max_absolute_errors": errors, "new_labels": 0, "new_fits": 0})


def run():
    out = OUT
    if not out.is_dir():
        raise FileNotFoundError("Root budget/snapshot must reserve the single batch first")
    exclusive(out / "experiment.lock", {"model_id": MODEL_ID, "started_utc": now(), "fit_allowance": 1})
    started = time.monotonic(); counts = {"reserved": 0, "completed": 0}; stage = "freeze"
    try:
        p = validate_protocol(json.loads(CONFIG.read_text()))
        for name, digest in PINNED.items():
            if sha(PACKAGE / name) != digest:
                raise ValueError("Original recipe/model class/domain bytes changed: " + name)
        mp = metric_protocol()
        frozen = {**p, "frozen_utc": now(), "config_sha256": sha(CONFIG), "sources": source_hashes(),
                  "package_hashes": PINNED, "dependencies": dependencies(), "metrics_protocol": mp}
        exclusive(out / "protocol.json", frozen)
        excluded, exclusion = collect_exclusions()
        exclusive(out / "exclusions_summary.json", exclusion)
        exclusive(out / "old_excluded_ids.json", sorted(excluded))
        old_ids = set(excluded); domain = json.loads((PACKAGE / "configs/domain.json").read_text())
        allrows = {}; all_new = set()
        for role in ROLES:
            rows, rejected = sample_rows(role, p, excluded, domain)
            ids = {r["design_id"] for r in rows}
            if len(ids) != len(rows) or ids & (old_ids | all_new):
                raise AssertionError("Nonunique or overlapping role")
            all_new |= ids; allrows[role] = rows
            write_role(rows, rejected, out / "samples" / role)
        exclusive(out / "sampling.json", {"roles": {r: {"n": len(rows), "unique_designs": len({x['design_id'] for x in rows}),
            "groups": dict(Counter(x["group"] for x in rows)), "inputs_sha256": sha(out / "samples" / r / "inputs.csv")}
            for r, rows in allrows.items()}, "all_roles_mutually_disjoint": True, "old_exclusions_overlap": 0,
            "old_excluded_ids_sha256": sha(out / "old_excluded_ids.json"), "new_unique_inputs": len(all_new),
            "all_X_frozen_before_first_label": True, "holdout_labels_not_yet_queried": True})
        stage = "train_development_labels"
        train = query_role(allrows["train"], p, out, counts)
        dev = query_role(allrows["development"], p, out, counts)
        xt, yt = matrices(train); xd, yd = matrices(dev)
        train_ids = [r["design_id"] for r in train]
        if len(train) != 10000 or len(set(train_ids)) != 10000:
            raise AssertionError("Exactly 10000 distinct rows must enter fit")
        folder = out / "release"; folder.mkdir(exist_ok=False)
        exclusive(out / "training_ids.json", train_ids)
        exclusive(out / "fit.lock", {"attempt": 1, "n_unique_fit": len(set(train_ids)), "train_X_sha256": matrix_sha256(xt),
            "train_Y_sha256": matrix_sha256(yt), "training_ids_sha256": sha(out / "training_ids.json"), "utc": now()})
        stage = "one_formal_fit"
        model = LogSurrogate(p["model_family"], domain["bounds"], p["parameters"], random_state=p["model_random_state"])
        fit_start = time.monotonic()
        with threadpool_limits(limits=2), warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            model.fit(xt, yt)
            fit_elapsed = time.monotonic() - fit_start
            joblib.dump(model, folder / "model.joblib")
            model_hash = sha(folder / "model.joblib")
            inspection = inspect_model(model, xt)
            if any(item["scaler"]["n_samples_seen"] != 10000 for item in inspection["targets"].values()):
                raise AssertionError("Fitted transforms did not see all 10000 rows")
            exclusive(out / "fit_inspection.json", inspection)
            exclusive(out / "fit_record.json", {"status": "completed", "formal_fit_attempts": 1, "n_unique_fit": 10000,
                "three_target_regressors": 3, "elapsed_s": fit_elapsed, "model_sha256": model_hash,
                "parameters": p["parameters"], "features": FEATURES, "targets": TARGETS, "actual_feature_count": 329,
                "warnings": [{"category": w.category.__name__, "message": str(w.message)} for w in caught]})
            stage = "development_score"
            pt, pd = model.predict(xt), model.predict(xd)
            train_scores, dev_scores = score(train, yt, pt, mp), score(dev, yd, pd, mp)
            exclusive(out / "train_metrics.json", train_scores)
            exclusive(out / "development_metrics.json", dev_scores)
            predictions_csv(out / "train_predictions.csv", train, yt, pt)
            predictions_csv(out / "development_predictions.csv", dev, yd, pd)
            exclusive(folder / "frozen_model.json", {"model_id": MODEL_ID, "model_sha256": model_hash,
                "n_unique_fit": 10000, "development_gate": dev_scores["gate"], "frozen_before_calibration": True,
                "protocol_sha256": sha(out / "protocol.json"), "fit_record_sha256": sha(out / "fit_record.json")})
            readback(model, folder / "model.joblib", dev, out)
            cal = None; final = None
            if dev_scores["gate"]["passed"]:
                stage = "calibration"
                calibration = query_role(allrows["calibration"], p, out, counts)
                xc, yc = matrices(calibration); pc = model.predict(xc)
                cal = joint_log_calibration(yc, pc, .05)
                if cal["rank"] != 974:
                    raise AssertionError("Wrong conformal rank")
                cal.update(model_sha256=model_hash, model_id=MODEL_ID)
                exclusive(folder / "calibration.json", cal)
                predictions_csv(out / "calibration_predictions.csv", calibration, yc, pc)
                stage = "one_final_evaluation"
                exclusive(out / "final_evaluation.lock", {"model_sha256": model_hash, "attempt": 1, "utc": now()})
                test = query_role(allrows["final_test"], p, out, counts)
                x, y = matrices(test); pred = model.predict(x); tags = np.asarray([r["group"] for r in test])
                final = score(test, y, pred, mp)
                final.update(intervals=intervals_with_units(y, pred, cal), constraints=constraint_statistics(y, pred, cal),
                    group_intervals={g: intervals_with_units(y[tags == g], pred[tags == g], cal) for g in GROUPS},
                    group_constraints={g: constraint_statistics(y[tags == g], pred[tags == g], cal) for g in GROUPS})
                lo, hi = prediction_intervals(pred, cal)
                predictions_csv(out / "final_test_predictions.csv", test, y, pred, lo, hi)
                exclusive(out / "final_metrics.json", final)
            else:
                exclusive(folder / "calibration.json", {"q_joint_log": None, "model_sha256": model_hash,
                    "model_id": MODEL_ID, "missing_reason": "development_gate_failed_no_holdout_labels"})
        if sha(folder / "model.joblib") != model_hash or source_hashes() != frozen["sources"]:
            raise AssertionError("Model or frozen learning sources changed during experiment")
        accepted = bool(final is not None and final["gate"]["passed"])
        summary = {"model_id": MODEL_ID, "status": "completed", "formal_fit_attempts": 1, "n_unique_fit": 10000,
            "source_kind": SOURCE, "backend_id": p["backend_id"], "development_accuracy_target_met": dev_scores["gate"]["passed"],
            "accuracy_target_met": accepted, "available_for_demo": accepted, "interval_status": "limited" if cal else "not_available",
            "role_label_counts": {r: (len(allrows[r]) if r in ("train", "development") or cal is not None else 0) for r in ROLES},
            "label_accounting": counts, "model_sha256": model_hash, "fit_elapsed_s": fit_elapsed,
            "pipeline_elapsed_s": time.monotonic() - started, "calibration_status": "completed" if cal else "not_run",
            "final_test_status": "completed" if final else "not_run", "GMMNLSE_attempts": 0,
            "physical_state": "undetermined", "numerical_validation": "not_verified", "eligible_as_validated_training_truth": False,
            "old_default_replaced": False, "missing_reason": None if final else "development_gate_failed"}
        exclusive(out / "summary.json", summary)
        return summary
    except BaseException as error:
        exclusive(out / "experiment_error.json", {"status": "failed", "stage": stage, "error": repr(error),
            "traceback": traceback.format_exc(), "label_accounting": counts, "elapsed_s": time.monotonic() - started,
            "retry_authorized": False, "utc": now()})
        raise
