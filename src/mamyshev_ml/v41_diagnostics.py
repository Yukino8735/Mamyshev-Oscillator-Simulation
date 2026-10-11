"""Read-only diagnosis of the already observed V4 test/challenge predictions.

No fitting, oracle evaluation, bias correction, or new blind-test claim occurs here.
"""
from __future__ import annotations

import csv
import importlib.util
import json
from pathlib import Path
import sqlite3
import sys
import time

import joblib
import numpy as np
from scipy.spatial import cKDTree
from threadpoolctl import threadpool_limits

from .v4_roles import ROOT, PACKAGE, FEATURES, TARGETS, SOURCE, BACKEND, ReleaseData, sha, verify_frozen

ATOL = RTOL = 1e-10
UNITS = dict(zip(TARGETS, ("nJ", "fs", "MW")))
OLD = ROOT / "reports/local/accuracy_v4_001"


def verify_evaluator_metadata(identity):
    if (identity.get("source") != SOURCE or identity.get("backend") != BACKEND
            or identity.get("metric_definition", {}).get("units") != UNITS
            or identity.get("metric_definition", {}).get("plane") != "constructed_compressed_scalars"):
        raise ValueError("Frozen evaluator source/backend/metric units or plane mismatch")


def write_json(path, value):
    path = Path(path)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")
    tmp.replace(path)


def _finite_array(value, shape=None):
    value = np.asarray(value, dtype=float)
    if not np.isfinite(value).all() or (shape is not None and value.shape != shape):
        raise ValueError("Expected finite array with the declared shape")
    return value


def compare_prediction(actual, reference):
    actual = _finite_array(actual)
    reference = _finite_array(reference, actual.shape)
    error = np.abs(actual - reference)
    limit = ATOL + RTOL * np.abs(reference)
    return {"passed": bool(np.all(error <= limit)), "absolute_tolerance": ATOL,
            "relative_tolerance": RTOL, "max_absolute_error": float(error.max(initial=0)),
            "max_tolerance_ratio": float((error / limit).max(initial=0)),
            "violations": int(np.count_nonzero(error > limit)), "scalar_values": int(actual.size)}


def read_saved_csv(path):
    with Path(path).open(newline="") as stream:
        reader = csv.DictReader(stream)
        fields = reader.fieldnames or []
        expected = ["design_id", "region", *FEATURES, *[k + "_truth" for k in TARGETS],
                    *[k + "_prediction" for k in TARGETS]]
        if fields[:len(expected)] != expected:
            raise ValueError("Saved CSV feature/target order differs from the frozen contract")
        rows = list(reader)
    if not rows:
        raise ValueError("Empty saved prediction CSV")
    for row in rows:
        for name in [*FEATURES, *[k + "_truth" for k in TARGETS], *[k + "_prediction" for k in TARGETS]]:
            row[name] = float(row[name])
    return rows


def verify_saved_rows(saved, database, role):
    """Join by ID, not row order; require exact original X/Y float correspondence."""
    ids = [row["design_id"] for row in saved]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate saved design_id")
    dbids = [row["design_id"] for row in database]
    if len(dbids) != len(set(dbids)) or set(ids) != set(dbids):
        raise ValueError("Saved/database design_id sets differ or duplicate")
    lookup = {row["design_id"]: row for row in database}
    for row in saved:
        reference = lookup[row["design_id"]]
        if reference["role"] != role or row["region"] != reference["region"]:
            raise ValueError("ID-linked role/region mismatch")
        if reference["source_kind"] != SOURCE or reference["backend_id"] != BACKEND:
            raise ValueError("Source/backend mismatch")
        for feature in FEATURES:
            if not np.isfinite(row[feature]) or row[feature] != reference[feature]:
                raise ValueError(f"ID-linked feature mismatch: {row['design_id']} {feature}")
        for target in TARGETS:
            if not np.isfinite(row[target + "_truth"]) or row[target + "_truth"] != reference[target]:
                raise ValueError(f"ID-linked truth mismatch: {row['design_id']} {target}")
    return {"passed": True, "rows": len(saved), "ID_sets_exact": True,
            "X_Y_exact_by_ID": True, "order_independent_join": True,
            "source_kind": SOURCE, "backend_id": BACKEND}


def residual_summary(truth, predicted, protocol):
    truth, predicted = _finite_array(truth), _finite_array(predicted)
    if truth.shape != predicted.shape or truth.ndim != 2 or truth.shape[1] != 3 or not len(truth):
        raise ValueError("Need matching nonempty n-by-three arrays")
    result = {"n": len(truth), "signed_definition": "prediction_minus_truth",
              "relative_definition": "signed_residual/max(abs(truth),protocol_floor)", "targets": {}}
    passed = []
    for j, target in enumerate(TARGETS):
        residual = predicted[:, j] - truth[:, j]
        absolute = np.abs(residual)
        floor = protocol["relative_error_floor"][target]
        relative = residual / np.maximum(np.abs(truth[:, j]), floor)
        limits = protocol["tolerances"][target]
        allowed = np.maximum(limits["absolute"], limits["relative"] * np.abs(truth[:, j]))
        r = absolute / allowed
        item = {"unit": UNITS[target], "bias_mean_signed": float(np.mean(residual)),
                "bias_median_signed": float(np.median(residual)), "signed_min": float(residual.min()),
                "signed_max": float(residual.max()), "mean_signed_relative": float(relative.mean()),
                "positive_count": int((residual > 0).sum()), "negative_count": int((residual < 0).sum()),
                "zero_count": int((residual == 0).sum()), "pass_rate": float((r <= 1).mean()),
                "relative_floor_used_count": int((np.abs(truth[:, j]) < floor).sum()),
                "MAE": float(absolute.mean()), "RMSE": float(np.sqrt(np.mean(residual ** 2)))}
        for key, values in (("signed_residual", residual), ("absolute_residual", absolute),
                            ("signed_relative_residual", relative), ("absolute_relative_residual", np.abs(relative)),
                            ("tolerance_ratio_r", r)):
            quantiles = np.quantile(values, [.5, .9, .95])
            item[key] = dict(zip(("P50", "P90", "P95", "max"), map(float, [*quantiles, values.max()])))
        result["targets"][target] = item
        passed.append(r <= 1)
    result["joint_pass_rate"] = float(np.all(passed, axis=0).mean())
    return result


def training_X_only(selection):
    ids = selection["training_ids"]
    if selection["n_train"] != 512 or len(ids) != 512 or len(set(ids)) != 512:
        raise ValueError("This diagnosis is restricted to the actual frozen 512-row model")
    with sqlite3.connect(f"file:{PACKAGE / 'data/development.sqlite'}?mode=ro", uri=True) as db:
        db.row_factory = sqlite3.Row
        rows = []
        for begin in range(0, len(ids), 400):
            batch = ids[begin:begin + 400]
            # Deliberately do not join evaluations or SELECT any Y column.
            sql = "SELECT design_id,role," + ",".join(FEATURES) + " FROM designs WHERE design_id IN (" + ",".join("?" for _ in batch) + ")"
            rows.extend(dict(row) for row in db.execute(sql, batch))
    by_id = {row["design_id"]: row for row in rows}
    if set(by_id) != set(ids) or any(row["role"] != "train" for row in rows):
        raise ValueError("Frozen training IDs are missing or not train")
    return _finite_array([[by_id[did][k] for k in FEATURES] for did in ids], (512, 4))


def scaled(x, bounds):
    low, high = np.array([bounds[k][0] for k in FEATURES]), np.array([bounds[k][1] for k in FEATURES])
    return (x - low) / (high - low)


def prediction_paths(model, cli_evaluator, x, saved, bounds, expected_model_hash):
    """Four genuine inference routes, with no estimator.fit or transform refit."""
    x = _finite_array(x)
    batch = _finite_array(model.predict(x), (len(x), 3))
    single = _finite_array([model.predict(row[None, :])[0] for row in x], batch.shape)
    xscaled = scaled(x, bounds)
    transformed = _finite_array(model._x(x), xscaled.shape)
    direct_log = _finite_array(np.column_stack([pipeline.predict(xscaled) for pipeline in model.models]), batch.shape)
    direct = _finite_array(np.exp(direct_log), batch.shape)
    cli = []
    from .v4_evaluators import design_id
    for row in x:
        design = dict(zip(FEATURES, map(float, row)))
        value = cli_evaluator.evaluate(design)
        if (value["kind"] != "Prediction" or value["job_status"] != "predicted"
                or value["design_id"] != design_id(design) or value["design"] != design
                or value["model_identity"]["sha256"] != expected_model_hash
                or value["identity"]["numerical_version"] != expected_model_hash
                or value["identity"]["source"] != "surrogate_prediction" or value["units"] != UNITS):
            raise ValueError("CLI adapter prediction identity/design/units mismatch")
        cli.append([value["targets"][target] for target in TARGETS])
    checks = {"batch_vs_saved": compare_prediction(batch, saved),
              "single_vs_saved": compare_prediction(single, saved),
              "single_vs_batch": compare_prediction(single, batch),
              "direct_fitted_log_pipelines_exp_vs_saved": compare_prediction(direct, saved),
              "CLI_helper_evaluator_vs_saved": compare_prediction(cli, saved),
              "manual_declared_domain_scaling_vs_model": compare_prediction(transformed, xscaled)}
    checks["CLI_identity_and_units"] = {"passed": True, "rows": len(x), "cached_prediction_lookup_used": False}
    return checks, batch


def _distribution(values):
    values = _finite_array(values)
    if not len(values):
        return {"n": 0, "P50": None, "P90": None, "P95": None, "max": None,
                "missing_reason": "empty_group"}
    return {"n": len(values), **dict(zip(("P50", "P90", "P95", "max"),
            map(float, [*np.quantile(values, [.5, .9, .95]), values.max()]))) }


def support_diagnostics(model, train_x, all_x, bounds):
    train_scaled, query_scaled = scaled(train_x, bounds), scaled(all_x, bounds)
    distance, nearest = cKDTree(train_scaled).query(query_scaled, k=1)
    exact = (train_x[:, 0] == 4) & (train_x[:, 3] == 4)
    neighborhood = ((train_x[:, 0] >= 3.5) & (train_x[:, 0] <= 4.5)
                    & (train_x[:, 3] >= 3.7) & (train_x[:, 3] <= 4.3))
    result = {"training_X_rows": len(train_x), "training_Y_read": False,
              "exact_P4_L4_count": int(exact.sum()), "P_exact_4_count": int((train_x[:, 0] == 4).sum()),
              "L_exact_4_count": int((train_x[:, 3] == 4).sum()),
              "neighborhood_inclusive_P_3_5_to_4_5_L_3_7_to_4_3_count": int(neighborhood.sum()),
              "neighborhood_excluding_exact_slice_count": int((neighborhood & ~exact).sum()),
              "training_pump_4_to_6_right_exclusive_count": int(((train_x[:, 0] >= 4) & (train_x[:, 0] < 6)).sum()),
              "nearest_neighbor": "Euclidean distance in four declared-domain-scaled inputs, no Y used; not an accuracy certificate",
              "train_feature_ranges": {k: [float(train_x[:, i].min()), float(train_x[:, i].max())] for i, k in enumerate(FEATURES)},
              "transform_support": []}
    # Inspect only fitted model state. These knots were fitted from train X,
    # not loaded from the label generator or any historical curve.
    for j, pipeline in enumerate(model.models):
        union = pipeline.named_steps["featureunion"]
        transformers = dict(union.transformer_list)
        spline = transformers["splinetransformer"]
        scaler = pipeline.named_steps["standardscaler"]
        bases = spline.bsplines_
        spline_bounds = np.array([[basis.t[basis.k], basis.t[-basis.k - 1]] for basis in bases])
        lower, upper = spline_bounds[:, 0], spline_bounds[:, 1]
        outside = (query_scaled < lower) | (query_scaled > upper)
        training_features = _finite_array(union.transform(train_scaled))
        query_features = _finite_array(union.transform(query_scaled))
        fmin, fmax = training_features.min(axis=0), training_features.max(axis=0)
        feature_outside = (query_features < fmin) | (query_features > fmax)
        mean_check = compare_prediction(np.mean(training_features, axis=0), scaler.mean_)
        variance_check = compare_prediction(np.var(training_features, axis=0), scaler.var_)
        result["transform_support"].append({"target": TARGETS[j],
            "fitted_spline_domain_scaled_support": dict(zip(FEATURES, spline_bounds.tolist())),
            "fitted_spline_extrapolation": spline.extrapolation,
            "query_rows_outside_any_spline_training_support": int(outside.any(axis=1).sum()),
            "query_rows_outside_support_by_input": dict(zip(FEATURES, map(int, outside.sum(axis=0)))),
            "scaler_n_samples_seen": int(scaler.n_samples_seen_),
            "scaler_input_feature_count": int(scaler.n_features_in_),
            "scaler_mean_matches_frozen_training_X": mean_check,
            "scaler_variance_matches_frozen_training_X": variance_check,
            "scaler_fitted_mean": scaler.mean_.tolist(), "scaler_fitted_scale": scaler.scale_.tolist(),
            "training_transformed_feature_min": fmin.tolist(), "training_transformed_feature_max": fmax.tolist(),
            "query_rows_outside_any_observed_transformed_feature_range": int(feature_outside.any(axis=1).sum()),
            "interpretation": "StandardScaler imposes no validity bounds; observed feature ranges describe support, not certified accuracy"})
    return result, distance, nearest


def save_perpoint(path, rows, truth, predicted, distance, nearest_ids, protocol):
    fields = ["role", "design_id", "region", *FEATURES, "nearest_training_design_id", "nearest_scaled_distance"]
    suffixes = ("truth", "prediction", "signed_residual", "absolute_residual", "signed_relative_residual", "tolerance_ratio_r")
    fields += [target + "_" + suffix for target in TARGETS for suffix in suffixes]
    with Path(path).open("x", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for i, row in enumerate(rows):
            entry = {key: row[key] for key in ("role", "design_id", "region", *FEATURES)}
            entry.update(nearest_training_design_id=nearest_ids[i], nearest_scaled_distance=float(distance[i]))
            for j, target in enumerate(TARGETS):
                residual = predicted[i, j] - truth[i, j]
                limits = protocol["tolerances"][target]
                values = (truth[i, j], predicted[i, j], residual, abs(residual),
                          residual / max(abs(truth[i, j]), protocol["relative_error_floor"][target]),
                          abs(residual) / max(limits["absolute"], limits["relative"] * abs(truth[i, j])))
                entry.update({target + "_" + suffix: float(v) for suffix, v in zip(suffixes, values)})
            writer.writerow(entry)


def plot_signed_scatter(path, rows, truth, predicted, title):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    x = np.array([[row[k] for k in FEATURES] for row in rows])
    fig, axes = plt.subplots(1, 3, figsize=(14, 4), constrained_layout=True)
    for j, target in enumerate(TARGETS):
        residual = predicted[:, j] - truth[:, j]
        limit = max(float(np.max(np.abs(residual))), 1e-12)
        artist = axes[j].scatter(x[:, 1], x[:, 2], c=residual, s=14, cmap="coolwarm", vmin=-limit, vmax=limit)
        axes[j].set(xlabel="Filter offset (nm)", ylabel="Filter 2 bandwidth (nm)", title=target)
        fig.colorbar(artist, ax=axes[j], label=f"prediction - truth ({UNITS[target]})")
    fig.suptitle(title + "; observed points, no interpolation; other inputs may vary")
    fig.savefig(path, dpi=140)
    plt.close(fig)


def diagnose(output, *, model_dir=OLD / "models", evaluation_dir=OLD / "evaluation", snapshot=None):
    output, model_dir, evaluation_dir = Path(output), Path(model_dir), Path(evaluation_dir)
    output.mkdir(parents=True, exist_ok=False)
    started = time.monotonic()
    result = {"scope": "V4 observed holdout diagnostic only; not new independent evaluation",
              "refitting": False, "oracle_queries": 0, "MATLAB_starts": 0, "status": "in_progress",
              "confirmed_wiring_issue": None, "development_may_proceed": False}
    try:
        model_path, selection_path = model_dir / "model.joblib", model_dir / "selection.json"
        selection = verify_frozen(model_path, selection_path)
        if list(FEATURES) != selection["features"] or list(TARGETS) != selection["targets"]:
            raise ValueError("Frozen feature/target order mismatch")
        bounds = json.loads((PACKAGE / "configs/domain.json").read_text())["bounds"]
        protocol = json.loads((PACKAGE / "configs/accuracy_protocol.json").read_text())
        identity = json.loads((OLD / "search/frozen_search_protocol.json").read_text())["evaluator_identity"]
        verify_evaluator_metadata(identity)
        # Hash recipe/oracle bytes only; never execute or parse their contents.
        if identity["numerical_version"] != sha(PACKAGE / "reference/oracle.py") or identity["metric_definition"]["recipe_sha256"] != sha(PACKAGE / "configs/generator_recipe.json"):
            raise ValueError("Original oracle/recipe identity changed")
        helper_path = ROOT / "scripts/v4_scan.py"
        adapter_unchanged_since_snapshot = None
        if snapshot is not None:
            frozen = json.loads(Path(snapshot).read_text())["sha256"]
            if frozen["scripts/v4_scan.py"] != sha(helper_path):
                raise ValueError("CLI helper changed after V4.1 freeze")
            adapter_unchanged_since_snapshot = frozen["src/mamyshev_ml/v4_evaluators.py"] == sha(ROOT / "src/mamyshev_ml/v4_evaluators.py")
        result["provenance"] = {"model_sha256": sha(model_path), "selection_sha256": sha(selection_path),
            "helper_path": str(helper_path.relative_to(ROOT)), "helper_sha256": sha(helper_path),
            "evaluator_sha256": sha(ROOT / "src/mamyshev_ml/v4_evaluators.py"),
            "evaluator_matches_batch_start_hash": adapter_unchanged_since_snapshot,
            "evaluator_change_review": "Batch may add model-scope metadata; root separately audits any adapter source diff. Prediction/identity/units checked here.",
            "helper_hash_compared_to_batch_snapshot": snapshot is not None,
            "original_evaluator_identity": identity, "input_units": dict(zip(FEATURES, ("W", "nm", "nm", "m"))),
            "target_units": UNITS, "mapping": "filter_offset_nm and filter2_bw_nm are separate ordered columns; no cw2 alias swap",
            "row_version_limitation": "Published SQLite rows store source/backend, not per-row recipe/seed; version is anchored by frozen DB hashes and original evaluator identity"}
        spec = importlib.util.spec_from_file_location("_v41_original_scan_cli", helper_path)
        helper = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(helper)
        cli = helper.load_frozen_surrogate(model_path, selection_path)
        model = joblib.load(model_path)
        if model.family != "spline_interactions" or model.domain != bounds or len(model.models) != 3 or model.parameters != selection["parameters"]:
            raise ValueError("Loaded model family/domain/target count/parameters mismatch")
        result["model_hash_before"] = sha(model_path)
        train_x = training_X_only(selection)
        loader = ReleaseData(evaluation=True, model=model_path, selection=selection_path, log_path=output / "old_data_access.jsonl")
        roles, all_rows, xs, ys, ps = {}, [], [], [], []
        prediction_rows = 0
        with threadpool_limits(limits=2):
            for role in ("test", "challenge"):
                saved = read_saved_csv(evaluation_dir / f"{role}_predictions.csv")
                database = loader.read(role, source_kind=SOURCE)
                aligned = verify_saved_rows(saved, database, role)
                x = _finite_array([[row[k] for k in FEATURES] for row in saved])
                truth = _finite_array([[row[k + "_truth"] for k in TARGETS] for row in saved])
                prediction = _finite_array([[row[k + "_prediction"] for k in TARGETS] for row in saved])
                checks, batch = prediction_paths(model, cli, x, prediction, bounds, selection["model_sha256"])
                prediction_rows += len(x) * 4
                roles[role] = {"CSV_sha256": sha(evaluation_dir / f"{role}_predictions.csv"),
                               "row_alignment": aligned, "inference_checks": checks,
                               "residuals": residual_summary(truth, prediction, protocol)}
                for row in saved:
                    row["role"] = role
                all_rows += saved
                xs.append(x); ys.append(truth); ps.append(prediction)
            x, truth, prediction = np.vstack(xs), np.vstack(ys), np.vstack(ps)
            support, distance, nearest = support_diagnostics(model, train_x, x, bounds)
        result["roles"] = roles
        result["training_support"] = support
        masks = {"all_old_test": np.array([r["role"] == "test" for r in all_rows]),
                 "all_old_challenge": np.array([r["role"] == "challenge" for r in all_rows]),
                 "fixed_P4_L4_challenge": np.array([r["role"] == "challenge" for r in all_rows]) & (x[:, 0] == 4) & (x[:, 3] == 4),
                 "test_pump_4_to_6": np.array([r["role"] == "test" for r in all_rows]) & (x[:, 0] >= 4) & (x[:, 0] < 6)}
        for region in sorted({r["region"] for r in all_rows if r["role"] == "challenge"}):
            masks["challenge_region_" + region] = np.array([r["role"] == "challenge" and r["region"] == region for r in all_rows])
        result["groups"] = {}
        for name, mask in masks.items():
            if not mask.any():
                result["groups"][name] = {"n": 0, "missing_reason": "empty_group"}
                continue
            result["groups"][name] = {"residuals": residual_summary(truth[mask], prediction[mask], protocol),
                "nearest_scaled_training_distance": _distribution(distance[mask]),
                "inside_declared_domain_count": int(np.all((scaled(x[mask], bounds) >= 0) & (scaled(x[mask], bounds) <= 1), axis=1).sum())}
            if name in ("fixed_P4_L4_challenge", "test_pump_4_to_6"):
                subset = [row for row, keep in zip(all_rows, mask) if keep]
                plot_signed_scatter(output / (name + "_signed_error.png"), subset, truth[mask], prediction[mask], name)
        save_perpoint(output / "old_holdout_diagnostic_residuals.csv", all_rows, truth, prediction, distance,
                      [selection["training_ids"][i] for i in nearest], protocol)
        inference_ok = all(check["passed"] for role in roles.values() for check in role["inference_checks"].values())
        scaler_ok = all(s["scaler_mean_matches_frozen_training_X"]["passed"] and s["scaler_variance_matches_frozen_training_X"]["passed"] for s in support["transform_support"])
        # Re-check the frozen source/data/model identity after all inference,
        # before permitting development to continue from these diagnostics.
        verify_frozen(model_path, selection_path)
        if sha(selection_path) != result["provenance"]["selection_sha256"]:
            raise ValueError("Frozen selection changed during diagnosis")
        if sha(helper_path) != result["provenance"]["helper_sha256"]:
            raise ValueError("CLI helper changed during diagnosis")
        if sha(ROOT / "src/mamyshev_ml/v4_evaluators.py") != result["provenance"]["evaluator_sha256"]:
            raise ValueError("Surrogate adapter source changed during diagnosis")
        result.update(status="completed", inference_consistent=inference_ok, fitted_scaler_training_X_consistent=scaler_ok,
            model_hash_after=sha(model_path), model_bytes_unchanged=sha(model_path) == result["model_hash_before"],
            confirmed_wiring_issue=not (inference_ok and scaler_ok),
            development_may_proceed=inference_ok and scaler_ok and sha(model_path) == result["model_hash_before"],
            prediction_design_rows_across_four_routes=prediction_rows, fitted_pipeline_scalar_predictions=prediction_rows * 3,
            fixed_equivalence_tolerance={"atol": ATOL, "rtol": RTOL},
            classification="no_wiring_evidence_in_checked_paths" if inference_ok and scaler_ok else "confirmed_inference_or_transform_inconsistency_requires_review",
            coverage_interpretation="X support and residual patterns are compatible with coverage/representation limitations but do not prove their causal contribution; no one-distance accuracy certificate",
            limitations=["Old test/challenge have been observed and are diagnostic only", "No bias correction/refit/oracle query performed",
                "Agreement among inference routes does not prove model accuracy", "Synthetic scalar results do not validate GMMNLSE or physical states"],
            elapsed_s=time.monotonic() - started)
        write_json(output / "diagnostic_summary.json", result)
        return result
    except Exception as exc:
        result.update(status="failed", error=f"{type(exc).__name__}: {exc}",
                      classification="check_blocked_or_mismatch_requires_review_not_automatic_root_cause",
                      development_may_proceed=False, elapsed_s=time.monotonic() - started)
        write_json(output / "diagnostic_summary.json", result)
        raise
