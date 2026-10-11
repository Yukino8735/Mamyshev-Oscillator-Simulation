"""Explicit-source data bridge for emulating an evaluator, not validated physics.

The historical V4Store selector is deliberately byte-preserved because frozen
releases bind its hash. All new training commands use this qualified adapter.
No oracle, private experiment manifest, or MATLAB execution is imported here.
"""
from __future__ import annotations

import copy
import csv
import hashlib
import json
import math
from pathlib import Path
import sqlite3
import sys

from .v4_evaluators import (FEATURES, TARGETS, UNITS, PACKAGE, canonical,
                           design_id, identity_key, import_safe_result, validate_design)

INPUT_UNITS = dict(zip(FEATURES, ("W", "nm", "nm", "m")))
SYNTHETIC_SOURCE = "repository_guided_synthetic"
SOLVER_SOURCE = "repaired_original_backend"
PARAMETERS = {"n_knots": 64, "degree": 3, "knots": "uniform",
              "interaction_polynomial_degree": 4, "alpha": .001, "log_targets": True}
CSV_FIELDS = ["evaluation_id", "design_id", *FEATURES, *TARGETS, "source", "record_json"]


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def qualify_record(record, identity):
    """Raise on inadmissible labels; return task qualification without altering final.

    Solver emulation means learning this source's numerical outputs. It does not
    imply physical state classification, independent convergence or training truth.
    Real records are rechecked against their original parent final and artifacts.
    """
    identity_key(identity)
    if record.get("identity") != identity:
        raise ValueError("Exact source/backend/version/seed/observation/metric identity required")
    if record.get("kind") != "Evaluation" or record.get("job_status") != "completed":
        raise ValueError("Only completed Evaluations qualify; no Prediction/pending/failure labels")
    if record.get("design_id") != design_id(record.get("design", {})):
        raise ValueError("Canonical design identity mismatch")
    if record.get("units") != UNITS or set(record.get("targets", {})) != set(TARGETS):
        raise ValueError("Three original-unit compressed targets are required")
    for value in record["targets"].values():
        if (isinstance(value, bool) or not isinstance(value, (int, float))
                or not math.isfinite(value) or value <= 0):
            raise ValueError("Log-target fitting requires positive finite observed targets")
    source = identity["source"]
    if source == SYNTHETIC_SOURCE:
        definition = identity["metric_definition"]
        if (identity["backend"] != "mamyshev_repository_guided_synthetic_v3"
                or not isinstance(definition, dict)
                or definition.get("plane") != "constructed_compressed_scalars"
                or definition.get("units") != UNITS):
            raise ValueError("Synthetic labels must retain their own backend and constructed-scalar definition")
        task = "synthetic_emulation"
    elif source == SOLVER_SOURCE:
        path = record.get("final_path")
        if not path or identity["backend"] != "run_mamyshev_config":
            raise ValueError("Solver emulation requires the explicit real production parent final")
        fresh = import_safe_result(path)
        request = json.loads((Path(path).parent / "launch_request.json").read_text())
        if request.get("mode") != "real":
            raise ValueError("Component fixtures do not qualify as real solver labels")
        for key in ("identity", "design", "design_id", "targets", "units", "run_id",
                    "source_identity", "outputs", "artifacts", "job_status"):
            if record.get(key) != fresh.get(key):
                raise ValueError("Stored solver record differs from original verified final: " + key)
        plane = fresh["outputs"]["compressed_analysis"]
        if (plane.get("plane") != "After output pigtail and compressor analysis"
                or plane.get("processing") != "Legacy idealized Treacy-t compression analysis"):
            raise ValueError("The compressed target plane/processing must be explicitly consistent")
        for key, unit, source_field in (
                ("energy", "nJ", "run_mamyshev.compressed_field and t"),
                ("fwhm", "fs", "run_mamyshev.dechirped_fwhm_fs"),
                ("peak_power", "W", "run_mamyshev.dechirped_peak_power_W")):
            metric = plane[key]
            if (metric.get("unit") != unit or metric.get("source") != source_field
                    or not metric.get("definition") or metric.get("missing_reason")):
                raise ValueError("Compressed targets cannot borrow upstream values or lose definitions")
        task = "solver_emulation"
    else:
        raise ValueError("Unsupported training source; predictions and component fixtures are not labels")
    return {"task": task, "eligible_for_source_emulation": True,
            "physical_validation_claim": False,
            "original_physical_state": record.get("physical_state", "undetermined"),
            "original_eligible_as_validated_training_truth": record.get("eligible_as_validated_training_truth", False)}


def training_records(store, *, identity):
    """Task-qualified companion to the frozen low-level V4Store selector."""
    identity_key(identity)
    records = store.training_records(source=identity["source"], identity=identity)
    for record in records:
        qualify_record(record, identity)
    return records


def _select(records, identity):
    identity_key(identity)
    selected, excluded = [], []
    for record in records:
        if record.get("identity") != identity:
            excluded.append({"evaluation_id": record.get("evaluation_id"), "reason": "different_exact_identity"})
            continue
        try:
            qualify_record(record, identity)
        except (ValueError, KeyError, TypeError, OSError) as error:
            excluded.append({"evaluation_id": record.get("evaluation_id"), "reason": str(error)})
        else:
            selected.append(copy.deepcopy(record))
    ids = [record.get("evaluation_id") for record in selected]
    if any(not isinstance(key, str) or not key for key in ids) or len(ids) != len(set(ids)):
        raise ValueError("Selected evaluation IDs must be present and unique; do not inflate rows by duplication")
    return selected, {"source_identity": identity, "selected_rows": len(selected),
                      "unique_designs": len({row["design_id"] for row in selected}), "excluded": excluded}


def read_records(*, identity, db=None, csv_path=None):
    """Read explicitly provided V4Store SQLite or lossless training CSV, read-only."""
    if (db is None) == (csv_path is None):
        raise ValueError("Specify exactly one explicit database or training CSV")
    if db is not None:
        path = Path(db).resolve()
        with sqlite3.connect(path.as_uri() + "?mode=ro", uri=True) as connection:
            records = [json.loads(row[0]) for row in connection.execute(
                "SELECT record_json FROM evaluations ORDER BY evaluation_id")]
    else:
        records = []
        with Path(csv_path).open(newline="") as stream:
            reader = csv.DictReader(stream)
            if reader.fieldnames != CSV_FIELDS:
                raise ValueError("Expected lossless training export CSV, including original record_json")
            for row in reader:
                record = json.loads(row["record_json"])
                expected = {"evaluation_id": record.get("evaluation_id"), "design_id": record.get("design_id"),
                            "source": record.get("identity", {}).get("source")}
                if any(row[key] != value for key, value in expected.items()):
                    raise ValueError("CSV scalar identity differs from embedded original record")
                for key in FEATURES + TARGETS:
                    original = record["design" if key in FEATURES else "targets"][key]
                    if float(row[key]) != original:
                        raise ValueError("CSV scalar differs from embedded original record: " + key)
                records.append(record)
    return _select(records, identity)


def export_records(records, output_csv, *, identity):
    """Exclusive lossless CSV: scalar columns are convenient; original evidence remains."""
    selected, audit = _select(records, identity)
    if audit["excluded"]:
        raise ValueError("Export requires prequalified records; inspect selection exclusions first")
    with Path(output_csv).open("x", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=CSV_FIELDS)
        writer.writeheader()
        for row in selected:
            writer.writerow({"evaluation_id": row["evaluation_id"], "design_id": row["design_id"],
                             **row["design"], **row["targets"], "source": identity["source"],
                             "record_json": canonical(row)})
    return {**audit, "csv_sha256": sha(output_csv), "features": list(FEATURES),
            "targets": list(TARGETS), "input_units": INPUT_UNITS, "units": UNITS}


def make_split(records, *, seed=0, development_fraction=.2):
    """Deterministic design-group split using IDs alone, never target magnitudes."""
    if type(seed) is not int or not 0 < development_fraction < 1:
        raise ValueError("Integer split seed and development fraction strictly between zero and one required")
    ids = sorted({record["design_id"] for record in records},
                 key=lambda key: hashlib.sha256(f"{seed}:{key}".encode()).hexdigest())
    ndev = max(2, round(len(ids) * development_fraction))
    split = {"schema_version": "design_group_split_v1", "seed": seed,
             "group_by": "design_id", "train": ids[ndev:], "development": ids[:ndev], "test": []}
    validate_split(records, split)
    return split


def validate_split(records, split):
    if (split.get("schema_version") != "design_group_split_v1"
            or split.get("group_by") != "design_id"
            or set(split) - {"schema_version", "seed", "group_by", "train", "development", "test"}):
        raise ValueError("Explicit design_group_split_v1 required; unknown split fields rejected")
    groups = []
    for role in ("train", "development", "test"):
        value = split.get(role, [])
        if not isinstance(value, list) or len(value) != len(set(value)) or any(not isinstance(k, str) for k in value):
            raise ValueError("Split groups must be unique design-ID lists")
        groups.append(set(value))
    if any(groups[a] & groups[b] for a, b in ((0, 1), (0, 2), (1, 2))):
        raise ValueError("A repeated design cannot cross training/development/test groups")
    if set.union(*groups) != {record["design_id"] for record in records}:
        raise ValueError("Every selected design must belong to exactly one explicit split")
    if len(groups[0]) < 8 or len(groups[1]) < 2 or (groups[2] and len(groups[2]) < 2):
        raise ValueError("Insufficient distinct designs: need >=8 train and >=2 development (and >=2 if testing)")
    return groups


def arrays(records):
    import numpy as np
    x = np.array([[validate_design(row["design"])[key] for key in FEATURES] for row in records], float).reshape(-1, 4)
    y = np.array([[row["targets"][key] for key in TARGETS] for row in records], float).reshape(-1, 3)
    if not np.isfinite(x).all() or not np.isfinite(y).all() or (y <= 0).any():
        raise ValueError("Positive finite targets and finite four-input matrix required")
    return x, y


def _model_class():
    """Import only the existing public feature/regression implementation."""
    reference = PACKAGE / "reference"
    present = sys.modules.get("models_v4")
    if present is not None and Path(present.__file__).resolve() != (reference / "models_v4.py").resolve():
        raise ValueError("models_v4 already loaded from a different asset; use a fresh process")
    if str(reference) not in sys.path:
        sys.path.insert(0, str(reference))
    from models_v4 import LogSurrogate
    return LogSurrogate


def fit_model(records, split, output_dir, *, identity, model_id):
    """One three-target fit, no model search, calibration or old held-out access."""
    import joblib
    import numpy as np
    from threadpoolctl import threadpool_limits
    if not isinstance(model_id, str) or not model_id or model_id in {"demo_10k_v1", "v42_T2_K64_A0001"}:
        raise ValueError("Use a new non-frozen model identity")
    selected, audit = _select(records, identity)
    if audit["excluded"]:
        raise ValueError("Training input contains unqualified records; use an explicit clean export")
    groups = validate_split(selected, split)
    roles = {role: [row for row in selected if row["design_id"] in group]
             for role, group in zip(("train", "development", "test"), groups)}
    matrices = {role: arrays(rows) for role, rows in roles.items()}
    domain = json.loads((PACKAGE / "configs/domain.json").read_text())["bounds"]
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=False)
    # Reservation occurs before fit; a failure leaves this directory to refuse overwrites.
    (output / "fit_request.json").write_text(canonical({"model_id": model_id, "identity": identity,
        "split": split, "parameters": PARAMETERS, "three_target_fit_calls_requested": 1}) + "\n")
    model = _model_class()("spline_interactions", domain, copy.deepcopy(PARAMETERS), random_state=11)
    train_x, train_y = matrices["train"]
    with threadpool_limits(limits=2):
        model.fit(train_x, train_y)
        predictions = {role: model.predict(x) for role, (x, _) in matrices.items() if len(x)}
        for pipeline in model.models:
            features = pipeline.named_steps["featureunion"].transform(model._x(train_x))
            scaler = pipeline.named_steps["standardscaler"]
            if int(scaler.n_samples_seen_) != len(train_x):
                raise AssertionError("Scaler was not fitted on training rows only")
            np.testing.assert_allclose(scaler.mean_, features.mean(axis=0), rtol=1e-12, atol=1e-12)
        joblib.dump(model, output / "model.joblib")
        restored = joblib.load(output / "model.joblib")
        for role, prediction in predictions.items():
            if not np.isfinite(prediction).all() or (prediction <= 0).any():
                raise FloatingPointError("Nonfinite or nonpositive saved-model predictions")
            np.testing.assert_array_equal(prediction, restored.predict(matrices[role][0]))
    metrics = {}
    for role in ("development", "test"):
        if role not in predictions:
            metrics[role] = {"n": 0, "metrics": None, "reason": "no_explicit_role_requested"}
            continue
        error = predictions[role] - matrices[role][1]
        metrics[role] = {"n": len(error), "metrics": {key: {"mae": float(np.mean(abs(error[:, j]))),
            "rmse": float(np.sqrt(np.mean(error[:, j] ** 2))), "unit": UNITS[key]}
            for j, key in enumerate(TARGETS)}}
    metadata = {"schema_version": "source_emulation_model_v1", "model_id": model_id,
        "source_identity": copy.deepcopy(identity), "task": qualify_record(selected[0], identity)["task"],
        "features": list(FEATURES), "targets": list(TARGETS), "input_units": INPUT_UNITS, "units": UNITS,
        "parameters": copy.deepcopy(PARAMETERS), "domain": domain, "split": split,
        "dataset_sha256": hashlib.sha256(canonical(selected).encode()).hexdigest(),
        "model_sha256": sha(output / "model.joblib"), "model_class_sha256": sha(PACKAGE / "reference/models_v4.py"),
        "counts": {role: {"rows": len(rows), "unique_designs": len({r['design_id'] for r in rows})}
                   for role, rows in roles.items()}, "scaler_fit_rows": len(train_x),
        "feature_count": int(model.models[0].named_steps["standardscaler"].n_features_in_),
        "three_target_fit_calls": 1, "reload_max_abs_difference": 0., "evaluation": metrics,
        "physical_state": "undetermined", "numerical_validation": "not_verified",
        "eligible_as_validated_training_truth": False, "intervals": None,
        "intervals_missing_reason": "No calibration performed by this training entrypoint."}
    (output / "metadata.json").write_text(json.dumps(metadata, indent=2, allow_nan=False) + "\n")
    return metadata


def load_model(output_dir, *, trusted_local=False):
    """Only deserialize an explicitly trusted local artifact after identity checks."""
    if trusted_local is not True:
        raise PermissionError("Joblib is executable serialization; explicit trusted_local=True required")
    import joblib
    output = Path(output_dir)
    metadata = json.loads((output / "metadata.json").read_text())
    if (metadata.get("schema_version") != "source_emulation_model_v1"
            or metadata.get("features") != list(FEATURES) or metadata.get("targets") != list(TARGETS)
            or metadata.get("input_units") != INPUT_UNITS or metadata.get("units") != UNITS
            or metadata.get("model_sha256") != sha(output / "model.joblib")
            or metadata.get("model_class_sha256") != sha(PACKAGE / "reference/models_v4.py")):
        raise ValueError("Training artifact schema, units or source/weight integrity mismatch")
    _model_class()
    model = joblib.load(output / "model.joblib")
    if (model.family != "spline_interactions" or model.parameters != metadata["parameters"]
            or model.domain != metadata["domain"] or len(model.models) != 3):
        raise ValueError("Saved feature pipeline and metadata disagree")
    return model, metadata
