"""Thin, explicit V4.2 application adapter; no fitting, oracle or MATLAB calls."""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
import math
from pathlib import Path

import numpy as np

from .v4_evaluators import FEATURES, TARGETS, UNITS, validate_design
from .v42_release import INPUT_UNITS, V42ReleaseEvaluator, load_release_evaluator

ROOT = Path(__file__).resolve().parents[2]
CALIBRATION_WIDTH_ATOL = 1e-14


def _sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _coverage(n, rate):
    covered = round(n * rate)
    if n <= 0 or not math.isfinite(rate) or not 0 <= rate <= 1 or abs(covered / n - rate) > 1e-12:
        raise ValueError("Bound empirical coverage is not an integer count fraction")
    return {"covered": covered, "n": n, "fraction": rate}


def calibration_reference(release):
    """Relate existing calibration bytes to the *hash-bound* final interval widths.

    The old manifest does not hash calibration.json directly. We therefore
    report this semantic relationship explicitly; we neither amend that manifest
    nor manufacture a trusted q constant. Failure disables intervals only.
    """
    try:
        path = Path(release["verification"]["final_metrics_path"]).parent / "calibration.json"
        calibration = json.loads(path.read_text())
        protocol = release["protocol"]
        if (calibration.get("model_sha256") != release["model_sha256"]
                or calibration.get("selected") != release["selected"]
                or calibration.get("n_calibration") != sum(protocol["role_quotas"]["calibration"].values())
                or calibration.get("alpha") != protocol["calibration_alpha"]
                or calibration.get("rank") != protocol["calibration_rank"]
                or protocol["calibration_method"] != "existing " + str(calibration.get("method"))):
            raise ValueError("Calibration model, selection, sample count or frozen protocol differs")
        q = calibration.get("q_joint_log")
        if isinstance(q, bool) or not isinstance(q, (int, float)) or not math.isfinite(q) or not 0 <= q <= 1:
            raise ValueError("Finite nonnegative diagnostic log width required")
        width = 2 * math.sinh(q)
        final = release["final_metrics"]
        actual = final["intervals"]["median_relative_interval_width"]
        if len(actual) != 3 or any(not math.isfinite(x) or abs(x - width) > CALIBRATION_WIDTH_ATOL for x in actual):
            raise ValueError("Calibration q disagrees with hash-bound final interval widths")
        return {"status": "verified_semantic_relationship", "path": str(path), "sha256": _sha(path),
                "q_joint_log": float(q), "method": calibration["method"],
                "n_calibration": calibration["n_calibration"], "alpha": calibration["alpha"],
                "rank": calibration["rank"], "model_sha256": release["model_sha256"],
                "selected": release["selected"], "old_manifest_direct_calibration_hash": False,
                "binding": "same model/selection/protocol and 2*sinh(q) equals bound final median relative interval widths",
                "width_comparison_atol": CALIBRATION_WIDTH_ATOL, "width_comparison_rtol": 0,
                "bound_final_metrics_sha256": release["final_metrics_sha256"],
                "missing_reason": None}
    except (OSError, KeyError, TypeError, ValueError, OverflowError) as exc:
        return {"status": "not_available", "q_joint_log": None,
                "old_manifest_direct_calibration_hash": False,
                "missing_reason": f"{type(exc).__name__}: {exc}"}


class V43ApplicationEvaluator(V42ReleaseEvaluator):
    """Retains the trusted evaluator and Prediction role, adding limited intervals."""
    def __init__(self, trusted):
        super().__init__(trusted.model, trusted.model_identity, trusted.release)
        self.calibration = calibration_reference(self.release)
        final = self.release["final_metrics"]
        self.empirical_coverage = {
            "overall": _coverage(final["intervals"]["n"], final["intervals"]["joint_coverage"]),
            "near_slice": _coverage(final["group_intervals"]["near_slice"]["n"],
                                    final["group_intervals"]["near_slice"]["joint_coverage"])}
        self.adapter_identity = {"adapter_id": "mamyshev_v43_frozen_application_v1",
            "sources": {"src/mamyshev_ml/v43_adapter.py": _sha(__file__)},
            "training_identity_unchanged": True}
        self.prediction_rows = 0

    def _intervals(self, values):
        q = self.calibration["q_joint_log"]
        if q is None:
            return None, None
        return values * math.exp(-q), values * math.exp(q)

    def predict_arrays(self, designs):
        """One vectorized call for an X-only pool; no per-row provenance duplication."""
        designs = [validate_design(d) for d in designs]
        if not designs:
            values = np.empty((0, 3), dtype=float)
        else:
            values = np.asarray(self.model.predict(np.array([[d[k] for k in FEATURES] for d in designs])), dtype=float)
        if values.shape != (len(designs), 3) or not np.isfinite(values).all() or (values <= 0).any():
            raise ValueError("Expected three finite positive scalar predictions per design")
        self.prediction_rows += len(designs)
        lower, upper = self._intervals(values)
        return {"designs": designs, "targets": values, "lower": lower, "upper": upper,
                "calibration": deepcopy(self.calibration), "model_identity": deepcopy(self.model_identity),
                "units": dict(UNITS), "input_units": dict(INPUT_UNITS),
                "adapter_identity": deepcopy(self.adapter_identity)}

    def evaluate(self, design, **kwargs):
        result = super().evaluate(design, **kwargs)
        self.prediction_rows += 1
        values = np.array([result["targets"][k] for k in TARGETS])
        lower, upper = self._intervals(values)
        result.update(application_adapter=deepcopy(self.adapter_identity), input_units=dict(INPUT_UNITS),
            physical_state="undetermined", numerical_validation="not_verified",
            domain_check={"status": "inside_declared_exploratory_domain", "length_grid_m": .1,
                "silent_rounding_or_clipping": False, "arbitrary_input_evaluation_group": None,
                "group_missing_reason": "No guaranteed evaluation-group mapping is assigned to arbitrary new inputs."},
            diagnostic_intervals={"status": "limited" if lower is not None else "not_available",
                "lower": None if lower is None else dict(zip(TARGETS, lower.tolist())),
                "upper": None if upper is None else dict(zip(TARGETS, upper.tolist())),
                "units": dict(UNITS), "calibration": deepcopy(self.calibration),
                "empirical_joint_coverage": deepcopy(self.empirical_coverage),
                "guaranteed_feasible": False, "per_group_or_per_point_95_percent_guarantee": False,
                "missing_reason": self.calibration["missing_reason"],
                "use": "Diagnostic only. Threshold crossings are uncertain; being wholly on one side does not replace evaluator confirmation."})
        result["known_limitations"].append({"id": "limited_interval_coverage", "interpretation":
            "Point tolerances passed on the fixed 2048 synthetic test rows; errors are not zero and future/GMMNLSE accuracy is not guaranteed. Overall joint interval coverage 1936/2048, near_slice 216/256; no certified safety claim."})
        return result

    def evaluate_many(self, designs):
        """Convenience full-record API; each row uses the existing trusted path.

        Use predict_arrays for vectorized large X-only pools. This method records
        one actual model row per submitted design and never creates Evaluations.
        """
        return [self.evaluate(design) for design in designs]


def load_application_evaluator(model_path, selection_path):
    return V43ApplicationEvaluator(load_release_evaluator(model_path, selection_path))


def interval_constraint(record, target, operator, threshold):
    """A descriptive threshold relation, never an authorization or safety verdict."""
    if target not in TARGETS or operator not in ("<=", ">=") or not math.isfinite(threshold):
        raise ValueError("A known target, <=/>= operator and finite threshold are required")
    interval = record["diagnostic_intervals"]
    if interval["lower"] is None:
        relation = "not_available"
    else:
        lo, hi = interval["lower"][target], interval["upper"][target]
        relation = ("entirely_on_predicted_feasible_side" if (hi <= threshold if operator == "<=" else lo >= threshold)
                    else "entirely_on_predicted_infeasible_side" if (lo > threshold if operator == "<=" else hi < threshold)
                    else "uncertain")
    return {"relation": relation, "target": target, "operator": operator, "threshold": threshold,
            "evaluator_confirmation_required": True, "guaranteed_feasible": False}
