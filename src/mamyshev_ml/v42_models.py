"""Fixed V4.2 representation matrix and exact-count development decisions.

This module constructs the original LogSurrogate without fitting by default.
It does not import or query an oracle, read label tables, or change old defaults.
"""
from __future__ import annotations

import copy
from fractions import Fraction
import hashlib
import json
import math

import numpy as np

from .v4_ml import LogSurrogate, protocol as v4_protocol
from .v4_roles import FEATURES, TARGETS
from .v41_experiment import statistics

CONFIGURATIONS = (
    ("K16_A01", 16, 0.1), ("K16_A0001", 16, 0.001),
    ("K32_A01", 32, 0.1), ("K32_A0001", 32, 0.001),
    ("K64_A01", 64, 0.1), ("K64_A0001", 64, 0.001),
)
EXPECTED_FEATURES = {16: 137, 32: 201, 64: 329}
SPECIAL_GROUPS = ("slice", "near_slice", "outer_faces", "corners")
REFERENCE_GROUPS = ("historical_core", "expanded_proposal")
SCORE_TIE_TOLERANCE = 1e-12
TERMINAL_STATUSES = ("completed", "numerical_failed")


def candidate_specs():
    return [{"slot_id": f"{training}_{config}", "training_set": training,
             "config": config, "n_knots": knots, "alpha": alpha,
             "expected_features": EXPECTED_FEATURES[knots], "n_train": 1024,
             "reused": {"T1": "B1", "T2": "B2"}[training] if config == "K16_A01" else None}
            for training in ("T1", "T2") for config, knots, alpha in CONFIGURATIONS]


def _canonical_spec(spec):
    known = {item["slot_id"]: item for item in candidate_specs()}
    if spec.get("slot_id") not in known:
        raise ValueError("Candidate slot is outside the frozen twelve-slot matrix")
    expected = known[spec["slot_id"]]
    if any(spec.get(key) != value for key, value in expected.items()):
        raise ValueError("Candidate parameters differ from its frozen matrix slot")
    return expected


def make_model(spec, baseparams, domain):
    """Only n_knots/alpha change; caller must reuse existing K16_A01 weights."""
    spec = _canonical_spec(spec)
    required = {"n_knots": 16, "degree": 3, "knots": "uniform",
                "interaction_polynomial_degree": 4, "alpha": 0.1, "log_targets": True}
    if any(baseparams.get(key) != value for key, value in required.items()):
        raise ValueError("Base parameters do not match the unchanged V4.1 spline family")
    parameters = copy.deepcopy(baseparams)
    parameters.update(n_knots=spec["n_knots"], alpha=spec["alpha"])
    # Existing implementation preserves include_bias=False, original constant
    # spline extrapolation, StandardScaler, and Ridge's default solver settings.
    return LogSurrogate("spline_interactions", copy.deepcopy(domain), parameters, random_state=11)


def matrix_sha256(value):
    array = np.asarray(value, dtype="<f8")
    if not np.isfinite(array).all():
        raise FloatingPointError("Nonfinite feature matrix cannot be given a valid identity")
    digest = hashlib.sha256(json.dumps(list(array.shape), separators=(",", ":")).encode())
    digest.update(np.ascontiguousarray(array).tobytes(order="C"))
    return digest.hexdigest()


def _matrix(value, columns=None):
    value = np.asarray(value, dtype=float)
    if value.ndim != 2 or (columns is not None and value.shape[1] != columns):
        raise ValueError("Expected a two-dimensional matrix with declared columns")
    if not np.isfinite(value).all():
        raise FloatingPointError("Expected finite matrix values")
    return value


def inspect_model(model, trainX):
    """Transform training X using fitted state only, without fit or prediction."""
    x = _matrix(trainX, 4)
    if len(x) == 0 or model.family != "spline_interactions" or len(model.models) != 3:
        raise ValueError("Need a fitted three-target spline model and nonempty training X")
    knots = model.parameters["n_knots"]
    if knots not in EXPECTED_FEATURES:
        raise ValueError("Unsupported knot count outside frozen matrix")
    xscaled = _matrix(model._x(x), 4)
    result = {"n_train": len(x), "feature_order": list(FEATURES), "target_order": list(TARGETS),
              "parameters": copy.deepcopy(model.parameters), "train_X_sha256": matrix_sha256(x),
              "domain_scaled_X_sha256": matrix_sha256(xscaled),
              "train_X_ranges": {k: [float(x[:, j].min()), float(x[:, j].max())] for j, k in enumerate(FEATURES)},
              "domain_scaled_X_ranges": {k: [float(xscaled[:, j].min()), float(xscaled[:, j].max())] for j, k in enumerate(FEATURES)},
              "targets": {}, "fitting_performed": False}
    for target, pipeline in zip(TARGETS, model.models):
        union = pipeline.named_steps["featureunion"]
        components = dict(union.transformer_list)
        spline, polynomial = components["splinetransformer"], components["polynomialfeatures"]
        scaler, ridge = pipeline.named_steps["standardscaler"], pipeline.named_steps["ridge"]
        features = _matrix(union.transform(xscaled), EXPECTED_FEATURES[knots])
        standardized = _matrix(scaler.transform(features), EXPECTED_FEATURES[knots])
        if (spline.n_knots != knots or spline.degree != 3 or spline.knots != "uniform"
                or spline.include_bias is not False or spline.extrapolation != "constant"
                or polynomial.degree != 4 or polynomial.include_bias is not False
                or polynomial.interaction_only is not False
                or ridge.alpha != model.parameters["alpha"]):
            raise ValueError("Fitted pipeline does not preserve the declared fixed representation")
        actual_knots = {feature: {"degree": int(basis.k), "all_extended_knots": basis.t.tolist(),
                        "base_support_scaled": [float(basis.t[basis.k]), float(basis.t[-basis.k - 1])]}
                        for feature, basis in zip(FEATURES, spline.bsplines_)}
        settings = ridge.get_params(deep=False)
        result["targets"][target] = {
            "actual_feature_count": features.shape[1], "expected_feature_count": EXPECTED_FEATURES[knots],
            "feature_matrix_shape": list(features.shape), "feature_matrix_sha256": matrix_sha256(features),
            "scaled_feature_matrix_sha256": matrix_sha256(standardized),
            "spline_output_features": int(spline.n_features_out_),
            "polynomial_output_features": int(polynomial.n_output_features_),
            "actual_knots": actual_knots,
            "spline_settings": {"n_knots": spline.n_knots, "degree": spline.degree, "knots": spline.knots,
                                "include_bias": spline.include_bias, "extrapolation": spline.extrapolation},
            "polynomial_settings": {"degree": polynomial.degree, "include_bias": polynomial.include_bias,
                                    "interaction_only": polynomial.interaction_only, "order": polynomial.order},
            "scaler": {"with_mean": scaler.with_mean, "with_std": scaler.with_std,
                       "n_features_in": int(scaler.n_features_in_), "n_samples_seen": int(scaler.n_samples_seen_),
                       "mean": scaler.mean_.tolist(), "scale": scaler.scale_.tolist(), "variance": scaler.var_.tolist()},
            "ridge_settings": {key: settings[key] for key in ("alpha", "fit_intercept", "copy_X", "max_iter", "tol", "solver", "positive", "random_state")},
            "ridge_fitted_solver": getattr(ridge, "solver_", None),
            "ridge_fitted_solver_missing_reason": None if hasattr(ridge, "solver_") else "installed_Ridge_does_not_expose_solver_",
            "ridge_coef_shape": list(np.asarray(ridge.coef_).shape),
            "finite_features": True, "finite_scaled_features": True,
            "finite_fitted_coefficients": bool(np.isfinite(ridge.coef_).all() and np.isfinite(ridge.intercept_).all())}
        if not result["targets"][target]["finite_fitted_coefficients"]:
            raise FloatingPointError("Nonfinite fitted coefficients")
    result["actual_feature_counts"] = {key: value["actual_feature_count"] for key, value in result["targets"].items()}
    result["feature_signature"] = {target: {key: value[key] for key in
        ("feature_matrix_sha256", "scaled_feature_matrix_sha256")}
        for target, value in result["targets"].items()}
    return result


def compare_alpha_feature_matrices(records):
    """Compare same-T, same-knots fitted features; never compares unlike T as equal."""
    lookup = {row["slot_id"]: row for row in records}
    if len(lookup) != len(records):
        raise ValueError("Duplicate slot in feature comparison")
    specs = candidate_specs()
    pairs = []
    for training in ("T1", "T2"):
        for knots in (16, 32, 64):
            pair = [s for s in specs if s["training_set"] == training and s["n_knots"] == knots]
            ids = [s["slot_id"] for s in pair]
            values = [lookup.get(identifier, {}).get("inspection") for identifier in ids]
            if any(v is None for v in values):
                pairs.append({"training_set": training, "n_knots": knots, "slots": ids,
                              "verified": False, "passed": None, "missing_reason": "one_or_both_fitted_inspections_unavailable"})
                continue
            first, second = values
            checks = {"same_train_X": first["train_X_sha256"] == second["train_X_sha256"],
                      "same_domain_scaled_X": first["domain_scaled_X_sha256"] == second["domain_scaled_X_sha256"]}
            for target in TARGETS:
                a, b = first["targets"][target], second["targets"][target]
                checks[target + "_features"] = a["feature_matrix_sha256"] == b["feature_matrix_sha256"]
                checks[target + "_scaled_features"] = a["scaled_feature_matrix_sha256"] == b["scaled_feature_matrix_sha256"]
                checks[target + "_knots"] = a["actual_knots"] == b["actual_knots"]
            pairs.append({"training_set": training, "n_knots": knots, "slots": ids,
                          "verified": True, "passed": all(checks.values()), "checks": checks, "missing_reason": None})
    return {"pairs": pairs, "all_six_pairs_verified": all(p["verified"] for p in pairs),
            "all_verified_pairs_passed": all(p["passed"] for p in pairs if p["verified"]),
            "scope": "Within one fixed training set and knot count; alpha must not change transforms"}


def count_statistics(y, prediction, protocol=None):
    """Reuse V4.1 metrics, adding exact integer numerators and explicit empty groups."""
    y, prediction = _matrix(y, 3), _matrix(prediction, 3)
    if y.shape != prediction.shape:
        raise ValueError("Truth/prediction shapes differ")
    p = v4_protocol() if protocol is None else protocol
    if "metrics_protocol" in p:
        p = p["metrics_protocol"]
    n = len(y)
    if n == 0:
        empty_target = {key: None for key in ("passed", "pass_rate", "mae", "rmse", "r2",
            "median_relative_error", "P90_relative_error", "P95_relative_error", "max_absolute_error",
            "relative_floor_used_count", "P95_tolerance_ratio", "median_tolerance_ratio",
            "signed_mean", "signed_relative_mean", "overprediction_count", "underprediction_count")}
        empty_target.update(n=0, missing_reason="empty_group", r2_missing_reason="empty_group",
                            wilson95=[None, None])
        for key in ("signed_error_quantiles", "signed_relative_quantiles", "absolute_error_quantiles",
                    "absolute_relative_quantiles", "normalized_error_quantiles"):
            empty_target[key] = dict.fromkeys(("P50", "P90", "P95", "max"))
        return {"n": 0, "passed": None, "joint_passed": None, "joint_pass_rate": None,
                "joint_wilson95": [None, None], "mean_tolerance_normalized_rmse": None,
                "targets": {name: {**copy.deepcopy(empty_target), "unit": unit}
                            for name, unit in zip(TARGETS, ("nJ", "fs", "MW"))},
                "finite_valid": True, "missing_reason": "empty_group"}
    value = statistics(y, prediction, {"metrics_protocol": p})
    def verify_finite_scalars(item):
        if isinstance(item, dict):
            for child in item.values():
                verify_finite_scalars(child)
        elif isinstance(item, (tuple, list)):
            for child in item:
                verify_finite_scalars(child)
        elif isinstance(item, (float, np.floating)) and not math.isfinite(item):
            raise FloatingPointError("Nonfinite derived metric; preserve numerical failure")
    verify_finite_scalars(value)
    flags = []
    for j, target in enumerate(TARGETS):
        tolerance = p["tolerances"][target]
        allowed = np.maximum(tolerance["absolute"], tolerance["relative"] * np.abs(y[:, j]))
        passed = np.abs(prediction[:, j] - y[:, j]) <= allowed
        value["targets"][target].update(n=n, passed=int(passed.sum()),
            pass_rate=int(passed.sum()) / n, missing_reason=None)
        flags.append(passed)
    joint = int(np.all(flags, axis=0).sum())
    value.update(joint_passed=joint, joint_pass_rate=joint / n, finite_valid=True, missing_reason=None)
    return value


def exact_rate(passed, n, threshold):
    if (type(n) is not int or n <= 0 or type(passed) is not int or passed < 0 or passed > n):
        return False
    fraction = Fraction(str(threshold))
    return passed * fraction.denominator >= n * fraction.numerator


def rate_gate(value, each, joint=None):
    if value.get("finite_valid") is not True or value.get("n", 0) <= 0:
        return False
    n = value["n"]
    if set(value.get("targets", {})) != set(TARGETS):
        return False
    per_target = all(value["targets"][name].get("n") == n
                     and exact_rate(value["targets"][name].get("passed"), n, each) for name in TARGETS)
    return per_target and (joint is None or exact_rate(value.get("joint_passed"), n, joint))


def development_gate(reference, reference_groups, special_groups):
    checks = {"reference_all": rate_gate(reference, .95, .90)}
    for group in REFERENCE_GROUPS:
        checks["reference_" + group] = group in reference_groups and rate_gate(reference_groups[group], .90)
    for group in SPECIAL_GROUPS:
        checks[group] = group in special_groups and rate_gate(special_groups[group], .95, .90)
    return {"passed": all(checks.values()), "checks": checks,
            "decision_rule": "integer numerator/denominator cross multiplication; no rate rounding or Wilson gate"}


def equal_group_score(reference_groups, special_groups):
    values = []
    for group in REFERENCE_GROUPS + SPECIAL_GROUPS:
        record = reference_groups.get(group) if group in REFERENCE_GROUPS else special_groups.get(group)
        if not record or record.get("n", 0) <= 0 or record.get("finite_valid") is not True:
            raise ValueError("All six nonempty finite groups are required for the comparison score")
        score = record["mean_tolerance_normalized_rmse"]
        if not isinstance(score, (int, float)) or not math.isfinite(score) or score < 0:
            raise ValueError("Nonfinite/invalid group score")
        values.append(score)
    return float(np.mean(values))


def _choose(records, known):
    if not records:
        return None, []
    minimum = min(r["equal_group_normalized_rmse"] for r in records)
    tied = [r for r in records if r["equal_group_normalized_rmse"] - minimum <= SCORE_TIE_TOLERANCE]
    rank = lambda r: (known[r["slot_id"]]["n_knots"], -known[r["slot_id"]]["alpha"],
                      0 if known[r["slot_id"]]["training_set"] == "T1" else 1)
    return min(tied, key=rank), [r["slot_id"] for r in tied]


def select_candidates(records, expected=12):
    """No formal selection until every frozen slot reaches a terminal state."""
    if expected != 12:
        raise ValueError("V4.2 final selection requires the complete twelve-slot matrix")
    known = {spec["slot_id"]: spec for spec in candidate_specs()}
    ids = [record["slot_id"] for record in records]
    if len(set(ids)) != len(ids) or not set(ids).issubset(known):
        raise ValueError("Duplicate or unknown candidate slot")
    for record in records:
        if record.get("status") == "numerical_failed" and record.get("numeric_valid") is not False:
            raise ValueError("Numerical failure must remain explicitly invalid")
    fatal = [r["slot_id"] for r in records if r.get("status") not in (*TERMINAL_STATUSES, "not_run", "running", "budget_exhausted")]
    terminal = [r for r in records if r.get("status") in TERMINAL_STATUSES]
    complete = len(terminal) == expected and not fatal
    valid = [r for r in records if r.get("status") == "completed" and r.get("numeric_valid") is True]
    for record in valid:
        score = record.get("equal_group_normalized_rmse")
        if not isinstance(score, (int, float)) or isinstance(score, bool) or not math.isfinite(score) or score < 0:
            raise ValueError("A numerically valid candidate needs a finite six-group score")
    best, _ = _choose(valid, known)
    passing = [r for r in valid if r.get("gate", {}).get("passed") is True]
    selected, tied = _choose(passing, known) if complete else (None, [])
    return {"status": "blocked" if fatal else ("completed" if complete else "partial"),
            "matrix_complete": complete, "expected_slots": expected,
            "terminal_slots": len(terminal), "numerically_valid_slots": len(valid),
            "numerical_failed_slots": [r["slot_id"] for r in records if r.get("status") == "numerical_failed"],
            "fatal_slots": fatal, "passing_slots": [r["slot_id"] for r in passing],
            "selected": selected["slot_id"] if selected else None,
            "selection_score": selected["equal_group_normalized_rmse"] if selected else None,
            "score_tied_slots": tied,
            "best_diagnostic": best["slot_id"] if best else None,
            "development_accuracy_target_met": selected is not None,
            "holdout_may_open": selected is not None,
            "tie_tolerance": SCORE_TIE_TOLERANCE,
            "stop_reason": "fatal_identity_or_infrastructure_failure" if fatal else
                ("matrix_incomplete_no_final_selection" if not complete else
                 (None if selected else "development_gates_not_met_no_holdout"))}
