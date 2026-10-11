"""Standalone frozen prediction CLI; copied unchanged into the local MVP bundle.

Identity hashes are integrity checks, not authentication of untrusted pickle or
Python code. Only the explicitly pinned, locally verified project assets load.
The original models_v4.LogSurrogate implements every numerical transformation.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.metadata
import importlib.util
import json
import math
from pathlib import Path
import sys

FEATURES = ("pump_power_W", "filter_offset_nm", "filter2_bw_nm", "gain_length_m")
TARGETS = ("compressed_energy_nJ", "compressed_duration_fs", "compressed_peak_power_MW")
INPUT_UNITS = dict(zip(FEATURES, ("W", "nm", "nm", "m")))
UNITS = dict(zip(TARGETS, ("nJ", "fs", "MW")))
BOUNDS = dict(zip(FEATURES, ([2, 10], [2, 16], [.5, 8], [1, 8])))
LOCKED = {
    "model.joblib": "c236c2d2dd6cb5b59e32bd5ab4f8c3823f7fefc10d7571108a3d6339ee46b2e0",
    "models_v4.py": "46f9779b878d195b601930446cce3ec5335f694ef219f28c2ae728a353590b11",
    "domain.json": "66802d60ab841a6ca5f7530147c80cbd465936ccef8b82b411f38d7a126ba668",
    "calibration.json": "5163e9f635cddd2432cb5e737439c0c9b9118d604c127907f65d5229eed5116a",
    "origin_selection.json": "603bf1e1ec670c2f151aaa879f0ec15b450b3b1ae1cd01abac301c27f82eb095",
    "origin_protocol.json": "fb624723207ee5f864976e70d971c3400fc2309313bf0467623237a59644f1cb",
    "origin_final_metrics.json": "2478d70d898d3898a5ed0cb3034d4f491baf8484b3d2a7ad61555686dbbf6d37",
    "origin_training_ids.json": "0db0820182bab9af6690f796440f4928f6d188a80b298550b80f3b3686c22139",
    "origin_evaluation_summary.json": "2595dcbdfe61094cb699ab0ac5735225e48262338096da512868888b1af9b06c",
}
FILES = set(LOCKED) | {"infer.py", "build_mvp_inference_bundle.py", "schema.json",
                       "provenance.json", "dependencies.json", "README.md"}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def no_duplicates(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON field: " + key)
        result[key] = value
    return result


def read_json(path):
    return json.loads(Path(path).read_text(), object_pairs_hook=no_duplicates)


def verify(bundle):
    """Verify all required bytes and fixed anchors before imports/deserialization."""
    bundle = Path(bundle).resolve()
    manifest = read_json(bundle / "manifest.json")
    if manifest.get("schema_version") != "mamyshev_mvp_inference_bundle_v1":
        raise ValueError("Unknown inference manifest")
    files = manifest.get("files", {})
    if set(files) != FILES:
        raise ValueError("Manifest must bind exactly the required inference assets")
    for name in sorted(FILES):
        path = bundle / name
        if path.is_symlink() or not path.is_file() or sha(path) != files[name]:
            raise ValueError("Missing, redirected or changed bundle asset: " + name)
        if name in LOCKED and files[name] != LOCKED[name]:
            raise ValueError("Asset differs from fixed trusted identity: " + name)
    schema = read_json(bundle / "schema.json")
    if (schema.get("features") != list(FEATURES) or schema.get("targets") != list(TARGETS)
            or schema.get("input_units") != INPUT_UNITS or schema.get("units") != UNITS
            or schema.get("bounds") != BOUNDS or schema.get("gain_length_step_m") != .1):
        raise ValueError("Input/output schema differs from fixed model")
    calibration = read_json(bundle / "calibration.json")
    protocol = read_json(bundle / "origin_protocol.json")
    final = read_json(bundle / "origin_final_metrics.json")
    q = calibration["q_joint_log"]
    if (calibration["model_sha256"] != LOCKED["model.joblib"]
            or calibration["selected"] != "T2_K64_A0001"
            or calibration["n_calibration"] != sum(protocol["role_quotas"]["calibration"].values())
            or calibration["alpha"] != protocol["calibration_alpha"]
            or calibration["rank"] != protocol["calibration_rank"]
            or protocol["calibration_method"] != "existing " + calibration["method"]
            or any(abs(x - 2 * math.sinh(q)) > 1e-14
                   for x in final["intervals"]["median_relative_interval_width"])):
        raise ValueError("Calibration semantic binding failed")
    dependencies = read_json(bundle / "dependencies.json")
    versions = {name: importlib.metadata.version(name) for name in dependencies["packages"]}
    if versions != dependencies["packages"]:
        raise ValueError("Runtime dependency versions differ from the tested bundle")
    return {"status": "verified", "model_sha256": LOCKED["model.joblib"],
            "manifest_sha256": sha(bundle / "manifest.json"), "files_verified": len(FILES),
            "dependency_versions": versions, "interval_status": "limited",
            "hashes_are_authentication": False, "prediction_performed": False}


def validate_design(value):
    if not isinstance(value, dict) or set(value) != set(FEATURES):
        raise ValueError("Exactly four named design fields required")
    result = {}
    for key in FEATURES:
        x = value[key]
        if isinstance(x, bool) or not isinstance(x, (int, float)) or not math.isfinite(x):
            raise ValueError(key + ": finite real value required")
        if not BOUNDS[key][0] <= x <= BOUNDS[key][1]:
            raise ValueError(key + ": outside declared exploratory domain")
        result[key] = float(x)
    grid = result["gain_length_m"] / .1
    if abs(grid - round(grid)) > 1e-9:
        raise ValueError("gain_length_m must already be on 0.1 m grid; no rounding")
    return result


def read_inputs(path):
    path = Path(path)
    if path.suffix.lower() == ".json":
        value = read_json(path)
        rows = value if isinstance(value, list) else [value]
    elif path.suffix.lower() == ".csv":
        with path.open(newline="") as stream:
            reader = csv.DictReader(stream)
            if (reader.fieldnames is None or len(reader.fieldnames) != 4
                    or set(reader.fieldnames) != set(FEATURES)):
                raise ValueError("CSV header must contain exactly the four input fields")
            rows = []
            for row in reader:
                if set(row) != set(FEATURES) or any(v is None for v in row.values()):
                    raise ValueError("Malformed CSV row")
                rows.append({k: float(row[k]) for k in FEATURES})
    else:
        raise ValueError("Input extension must be .json or .csv")
    if not rows:
        raise ValueError("At least one existing input design is required")
    return [validate_design(row) for row in rows]


def load_model(bundle):
    bundle = Path(bundle).resolve()
    verify(bundle)
    source = bundle / "models_v4.py"
    loaded = sys.modules.get("models_v4")
    if loaded is not None and Path(getattr(loaded, "__file__", "")).resolve() != source:
        raise ValueError("models_v4 is already loaded from a different location")
    if loaded is None:
        spec = importlib.util.spec_from_file_location("models_v4", source)
        module = importlib.util.module_from_spec(spec)
        sys.modules["models_v4"] = module
        # Execute the verified source bytes, never an unbound cached .pyc file.
        exec(compile(source.read_bytes(), str(source), "exec"), module.__dict__)
    import joblib
    model = joblib.load(bundle / "model.joblib")
    expected = read_json(bundle / "origin_selection.json")
    if (type(model) is not sys.modules["models_v4"].LogSurrogate
            or model.family != expected["model_family"] or model.parameters != expected["parameters"]
            or model.domain != BOUNDS or len(model.models) != 3):
        raise ValueError("Loaded model schema differs from pinned release")
    return model


def predict(bundle, designs):
    designs = [validate_design(x) for x in designs]
    if not designs:
        raise ValueError("No designs supplied")
    model = load_model(bundle)
    import numpy as np
    values = np.asarray(model.predict([[x[k] for k in FEATURES] for x in designs]))
    if values.shape != (len(designs), 3) or not np.isfinite(values).all() or (values <= 0).any():
        raise ValueError("Expected finite positive three-target predictions")
    q = read_json(Path(bundle) / "calibration.json")["q_joint_log"]
    rows = [{"kind": "Prediction", "source_kind": "surrogate_prediction", "design": x,
             "targets": dict(zip(TARGETS, y.tolist())),
             "lower": dict(zip(TARGETS, (y * math.exp(-q)).tolist())),
             "upper": dict(zip(TARGETS, (y * math.exp(q)).tolist()))} for x, y in zip(designs, values)]
    return {"schema_version": "mamyshev_mvp_predictions_v1", "model_id": "v42_T2_K64_A0001",
            "model_sha256": LOCKED["model.joblib"], "input_units": INPUT_UNITS, "units": UNITS,
            "source_kind": "surrogate_prediction", "training_target_source": "repository_guided_synthetic",
            "interval_status": "limited", "q_joint_log": q,
            "empirical_joint_interval_coverage": {"overall": [1936, 2048], "near_slice": [216, 256]},
            "interval_safety_guarantee": False, "physical_state": "undetermined",
            "numerical_validation": "not_verified", "eligible_as_validated_training_truth": False,
            "n_predictions": len(rows), "predictions": rows}


def write_output(path, result):
    path = Path(path)
    if path.suffix.lower() == ".json":
        with path.open("x") as stream:
            json.dump(result, stream, indent=2, allow_nan=False); stream.write("\n")
    elif path.suffix.lower() == ".csv":
        columns = list(FEATURES) + list(TARGETS) + [f"{side}_{key}" for side in ("lower", "upper") for key in TARGETS]
        columns += ["kind", "model_sha256", "interval_status"]
        with path.open("x", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=columns); writer.writeheader()
            for row in result["predictions"]:
                writer.writerow({**row["design"], **row["targets"],
                    **{f"{s}_{k}": row[s][k] for s in ("lower", "upper") for k in TARGETS},
                    "kind": "Prediction", "model_sha256": result["model_sha256"], "interval_status": "limited"})
    else:
        raise ValueError("Output extension must be .json or .csv")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("verify", help="verify identities and dependencies; no prediction")
    predict_parser = sub.add_parser("predict", help="pure frozen prediction; no oracle or MATLAB")
    predict_parser.add_argument("--input", required=True)
    predict_parser.add_argument("--output", required=True)
    args = parser.parse_args()
    try:
        bundle = Path(__file__).resolve().parent
        if args.command == "verify":
            print(json.dumps(verify(bundle), indent=2))
        else:
            if Path(args.output).exists():
                raise FileExistsError("Refusing to overwrite output: " + args.output)
            result = predict(bundle, read_inputs(args.input))
            write_output(args.output, result)
            print(json.dumps({"status": "predicted", "n_predictions": result["n_predictions"], "output": args.output}))
    except (OSError, ValueError, TypeError, KeyError, ImportError) as exc:
        print(json.dumps({"status": "rejected", "error": f"{type(exc).__name__}: {exc}", "fallback": None}), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
