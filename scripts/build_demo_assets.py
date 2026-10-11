#!/usr/bin/env python3
"""Prepare data-free, locally reviewed model assets; never train or obtain labels."""
from __future__ import annotations

import importlib.metadata
import json
from pathlib import Path
import platform
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from mamyshev_ml.demo_inference import (ASSETS, CLASS_SHA, DOMAIN_SHA, FEATURES, TARGETS,
    INPUT_UNITS, UNITS, sha, verify, load_model)
from mamyshev_ml.v42_release import verify_release
from mamyshev_ml.v43_adapter import calibration_reference

OUT = ROOT / "reports/local/demo_10k_release_001"
DEST = ROOT / "demo/assets/models"
OLD = ROOT / "reports/local/accuracy_v4_2_001"
OLD_SHA = "c236c2d2dd6cb5b59e32bd5ab4f8c3823f7fefc10d7571108a3d6339ee46b2e0"
PACKAGE = ROOT / "mamyshev_accuracy_v4"


def read(path):
    return json.loads(Path(path).read_text())


def write(path, value):
    with Path(path).open("x") as stream:
        json.dump(value, stream, indent=2, allow_nan=False); stream.write("\n")


def aggregate(value):
    # Only aggregate dictionaries; no raw row IDs or X/Y/prediction tables.
    return {key: value[key] for key in ("metrics", "groups", "reference", "gate", "intervals",
        "group_intervals", "constraints", "group_constraints") if key in value}


def build_one(directory, model_id, model_path, calibration_path, metrics_path, card):
    folder = DEST / directory; folder.mkdir(parents=True, exist_ok=False)
    for name, source in {"model.joblib": model_path, "models_v4.py": PACKAGE / "reference/models_v4.py",
                          "domain.json": PACKAGE / "configs/domain.json", "calibration.json": calibration_path}.items():
        shutil.copyfile(source, folder / name)
    if sha(folder / "models_v4.py") != CLASS_SHA or sha(folder / "domain.json") != DOMAIN_SHA:
        raise ValueError("Original model class/domain changed")
    write(folder / "metrics.json", aggregate(read(metrics_path)))
    write(folder / "model_card.json", card)
    write(folder / "dependencies.json", {"python": platform.python_version(), "packages": {
        k: importlib.metadata.version(k) for k in ("numpy", "scipy", "scikit-learn", "joblib", "threadpoolctl")},
        "same_existing_environment_only": True, "new_clean_environment_tested": False})
    if {p.name for p in folder.iterdir()} != ASSETS:
        raise ValueError("Unexpected asset; raw records may not enter inference release")
    write(folder / "manifest.json", {"schema_version": "mamyshev_demo_inference_v1", "model_id": model_id,
        "files": {name: sha(folder / name) for name in sorted(ASSETS)}, "data_files_included": False,
        "public_release_status": "blocked_pending_license_and_user_review", "old_release_unchanged": True})
    return {"directory": directory, "manifest_sha256": sha(folder / "manifest.json"),
            "model_sha256": sha(folder / "model.joblib"), "n_train": card["n_train"],
            "display_name": f"{model_id} · {card['n_train']:,} synthetic training designs"}


def base_card(model_id, n, digest, parameters):
    return {"model_id": model_id, "n_train": n, "n_unique_fit": n, "model_sha256": digest,
        "available_for_demo": True, "source_kind": "repository_guided_synthetic",
        "training_target_source": "repository_guided_synthetic", "backend_id": "mamyshev_repository_guided_synthetic_v3",
        "features": FEATURES, "targets": TARGETS, "input_units": INPUT_UNITS, "units": UNITS,
        "parameters": parameters, "model_family": "spline_interactions", "actual_feature_count": 329,
        "interval_status": "limited", "interval_safety_guarantee": False,
        "domain_status": "exploratory_not_validated_GMMNLSE_operating_domain",
        "physical_state": "undetermined", "numerical_validation": "not_verified",
        "eligible_as_validated_training_truth": False, "real_solver_generalization": "not_measured",
        "real_solver_time_savings": "not_measured", "license_status": "pending_review_no_publication_authorized",
        "hashes_are_integrity_not_security_certification": True}


def inspect_no_training_rows(model):
    """Inspect trusted deserialized state; fitted coefficients/transforms only."""
    import numpy as np
    if set(vars(model)) != {"family", "domain", "parameters", "random_state", "models"}:
        raise ValueError("Unexpected model state may contain training data")
    visited = set(); arrays = []
    def walk(value, path):
        if id(value) in visited: return
        visited.add(id(value))
        if isinstance(value, np.ndarray):
            arrays.append({"path": path, "shape": list(value.shape), "bytes": int(value.nbytes)})
            if value.size >= 10000 or (value.ndim >= 2 and value.shape[0] >= 1000):
                raise ValueError("Large array inconsistent with this coefficient-only model")
        elif isinstance(value, dict):
            for key, child in value.items(): walk(child, path + "." + str(key))
        elif isinstance(value, (list, tuple)):
            for i, child in enumerate(value): walk(child, path + f"[{i}]")
        elif hasattr(value, "__dict__"):
            walk(vars(value), path)
    walk(model, "model")
    return {"passed": True, "arrays": arrays, "raw_training_X_Y_stored": False,
        "method": "Inspect known original class state and every reachable numpy array; expected fitted transforms/coefficients only"}


def _historical_build():
    """Retained historical implementation; superseded by the frozen snapshot."""
    if DEST.exists(): raise FileExistsError("Refusing to replace prepared assets")
    old = verify_release(OLD / "release/model.joblib", OLD / "release/selection.json")
    calibration = calibration_reference(old)
    if calibration["status"] != "verified_semantic_relationship": raise ValueError("Old q binding invalid")
    if old["model_sha256"] != OLD_SHA or old["n_train"] != 1024: raise ValueError("Old release identity invalid")
    card = base_card("v42_T2_K64_A0001", old["n_train"], old["model_sha256"], old["parameters"])
    card.update(accuracy_target_met=read(OLD / "summary.json")["accuracy_target_met"], experiment="historical_accuracy_v4_2_001",
        training_recipe="T2:512 historical training plus512 targeted synthetic designs", final_test_n=2048,
        provenance={"original_selection_sha256": sha(OLD / "release/selection.json"),
            "original_model_sha256": OLD_SHA, "original_training_ids_sha256": old["training_ids_sha256"],
            "original_final_metrics_sha256": sha(OLD / "evaluation/final_metrics.json")},
        reproducibility="Original archived training identity retained locally; this inference release contains no training rows or ID list")
    models = {"v42_T2_K64_A0001": build_one("v42", "v42_T2_K64_A0001", OLD / "release/model.joblib",
        Path(calibration["path"]), OLD / "evaluation/final_metrics.json", card)}
    summary_path = OUT / "summary.json"
    unavailable_reason = "new_experiment_did_not_complete"
    if summary_path.exists():
        summary = read(summary_path)
        if summary.get("available_for_demo") is True:
            fit = read(OUT / "fit_record.json"); protocol = read(OUT / "protocol.json")
            if (fit["status"] != "completed" or fit["n_unique_fit"] != 10000 or fit["formal_fit_attempts"] != 1
                    or fit["model_sha256"] != sha(OUT / "release/model.joblib")
                    or not read(OUT / "development_metrics.json")["gate"]["passed"]
                    or not read(OUT / "final_metrics.json")["gate"]["passed"]):
                raise ValueError("New weights have not passed their own fixed point-prediction acceptance")
            card = base_card("demo_10k_v1", fit["n_unique_fit"], fit["model_sha256"], fit["parameters"])
            card.update(accuracy_target_met=True, experiment="demo_10k_release_001", formal_fit_attempts=1,
                role_label_counts=summary["role_label_counts"], final_test_n=summary["role_label_counts"]["final_test"],
                training_recipe="Fresh fixed-stratum synthetic designs; all10000 unique rows in one three-target fit",
                provenance={"protocol_sha256": sha(OUT / "protocol.json"), "training_ids_sha256": sha(OUT / "training_ids.json"),
                    "fit_record_sha256": sha(OUT / "fit_record.json"), "final_metrics_sha256": sha(OUT / "final_metrics.json"),
                    "old_ID_exclusion_sha256": sha(OUT / "old_excluded_ids.json"), "recipe_sha256": protocol["package_hashes"]["configs/generator_recipe.json"]},
                reproducibility={"same_recipe_regeneration": True, "exact_row_reconstruction_from_public_assets": False,
                    "reason": "Local historical ID-only exclusion list is not distributed; digest is retained as provenance"},
                comparison_to_1024="Different freshly sampled test datasets; not a common-holdout sample-size ablation")
            models["demo_10k_v1"] = build_one("demo_10k_v1", "demo_10k_v1", OUT / "release/model.joblib",
                OUT / "release/calibration.json", OUT / "final_metrics.json", card)
            unavailable_reason = None
        else:
            unavailable_reason = summary.get("missing_reason") or "new_model_failed_own_fixed_point_prediction_gate"
    write(DEST / "catalog.json", {"schema_version": "mamyshev_demo_catalog_v1", "default_model_id": "v42_T2_K64_A0001",
        "models": models, "demo_10k_unavailable_reason": unavailable_reason, "historical_default_replaced": False,
        "public_release_status": "blocked_pending_license_and_user_review", "data_files_included": False})
    checks = {}
    for model_id in models:
        meta = verify(DEST, model_id); model, _ = load_model(DEST, model_id)
        checks[model_id] = {"verification": {k: meta[k] for k in ("status", "files_verified", "model_sha256", "n_train")},
                            "stored_state": inspect_no_training_rows(model)}
    receipt = {"catalog": str(DEST.relative_to(ROOT) / "catalog.json"), "catalog_sha256": sha(DEST / "catalog.json"),
        "models": models, "checks": checks, "total_bytes": sum(p.stat().st_size for p in DEST.rglob("*") if p.is_file()),
        "training_rows_distributed": 0, "raw_training_data_or_ID_lists_distributed": False,
        "new_fits": 0, "new_labels": 0, "new_predictions": 0,
        "public_release_status": "blocked_pending_license_and_user_review"}
    write(OUT / "asset_build.json", receipt)
    print(json.dumps({k: v for k, v in receipt.items() if k != "checks"}, indent=2))


def main():
    """Verify the current frozen bundle; never rebuild the retired catalog."""
    from mamyshev_ml.demo_inference import load_catalog, MODEL_ID
    if not (DEST / "catalog.json").exists():
        raise FileNotFoundError("Restore the reviewed single_10k_001 assets; do not regenerate historical templates")
    catalog = load_catalog(DEST)
    metadata = verify(DEST, MODEL_ID)
    print(json.dumps({"status": "verified_existing_frozen_assets", "model_id": MODEL_ID,
        "catalog_sha256": sha(DEST / "catalog.json"), "files_verified": metadata["files_verified"],
        "new_fits": 0, "new_labels": 0, "assets_written": 0}))


if __name__ == "__main__": main()
