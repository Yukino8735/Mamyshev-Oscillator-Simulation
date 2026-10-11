#!/usr/bin/env python3
"""Build one local inference bundle after checking the untouched full V4.2 release."""
from __future__ import annotations

import importlib.metadata
import json
from pathlib import Path
import platform
import shutil
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from mamyshev_ml.closeout_inference import BOUNDS, FEATURES, INPUT_UNITS, LOCKED, TARGETS, UNITS, sha, verify
from mamyshev_ml.v42_release import verify_release
from mamyshev_ml.v43_adapter import calibration_reference

OUT = ROOT / "reports/local/mvp_closeout_001"
RELEASE = ROOT / "reports/local/accuracy_v4_2_001/release"


def dump(path, value):
    with path.open("x") as stream:
        json.dump(value, stream, indent=2, allow_nan=False); stream.write("\n")


def main():
    bundle, archive = OUT / "inference_bundle", OUT / "inference_bundle.zip"
    if not OUT.is_dir() or bundle.exists() or archive.exists():
        raise FileExistsError("Require existing batch and absent bundle/archive; never overwrite")
    release = verify_release(RELEASE / "model.joblib", RELEASE / "selection.json")
    calibration = calibration_reference(release)
    if calibration["status"] != "verified_semantic_relationship":
        raise ValueError("Calibration relationship was not verified: " + str(calibration))
    assets = {"model.joblib": RELEASE / "model.joblib",
              "models_v4.py": ROOT / "mamyshev_accuracy_v4/reference/models_v4.py",
              "domain.json": ROOT / "mamyshev_accuracy_v4/configs/domain.json",
              "calibration.json": Path(calibration["path"]),
              "origin_selection.json": RELEASE / "selection.json"}
    for kind in ("protocol", "training_ids", "evaluation_summary", "final_metrics"):
        assets["origin_" + kind + ".json"] = ROOT / release[kind + "_path"]
    for name, path in assets.items():
        if sha(path) != LOCKED[name]:
            raise ValueError("Fixed asset changed before copy: " + name)
    bundle.mkdir()
    for name, path in assets.items():
        shutil.copyfile(path, bundle / name)
    shutil.copyfile(ROOT / "src/mamyshev_ml/closeout_inference.py", bundle / "infer.py")
    shutil.copyfile(__file__, bundle / "build_mvp_inference_bundle.py")
    dump(bundle / "schema.json", {"features": list(FEATURES), "targets": list(TARGETS),
        "input_units": INPUT_UNITS, "units": UNITS, "bounds": BOUNDS, "gain_length_step_m": .1,
        "length_rounding": False, "domain_status": "exploratory_not_validated_operating_domain",
        "filter_offset_definition": "SF1_center_nm - SF2_center_nm; SF1 fixed 1040 nm"})
    dump(bundle / "dependencies.json", {"python_build_version": platform.python_version(),
        "platform_build": platform.platform(), "not_a_clean_environment_or_cross_platform_test": True,
        "packages": {k: importlib.metadata.version(k) for k in
                     ("numpy", "scipy", "scikit-learn", "joblib", "threadpoolctl")}})
    dump(bundle / "provenance.json", {"model_id": release["release_id"], "training_designs": 1024,
        "training_source": "T2: 512 reused prior designs + 512 V4.1 targeted designs; repository_guided_synthetic",
        "training_ids": "origin_training_ids.json", "calibration": {k: v for k, v in calibration.items() if k != "path"},
        "original_artifacts": {name: {"repository_path": str(path.relative_to(ROOT)), "sha256": sha(path)}
                               for name, path in assets.items()},
        "builder_repository_path": "scripts/build_mvp_inference_bundle.py",
        "builder_source_sha256": sha(__file__), "fitted_model_modified": False,
        "full_experiment_archive_replaced": False, "default_model_replaced": False,
        "interval_status": "limited", "physical_state": "undetermined", "numerical_validation": "not_verified",
        "eligible_as_validated_training_truth": False, "public_redistribution": "not_authorized_pending_rights_review"})
    (bundle / "README.md").write_text("""# Local frozen inference bundle

Use the existing mamyshev-ml environment; no repository or PYTHONPATH is needed.
Run `python infer.py verify`, then `python infer.py predict --input inputs.json --output predictions.json`.
JSON accepts one exact four-field object or a list; CSV uses the four feature names in schema.json.
Both JSON and CSV output are supported; existing output files are never overwritten.
The package only predicts; it never obtains labels, trains, scans MATLAB or falls back to another backend.

The original 42,530-byte model and models_v4.py class are byte-for-byte copies. The class contains
historical fit methods, but this CLI only invokes predict and does not rebuild the 329-feature transform.
The independently verified original archive remains authoritative. origin_* files are frozen provenance
copies; their historical path references are not required at inference time and are not a complete archive.
build_mvp_inference_bundle.py records the actual builder; rebuilding needs the original repository.

Dependencies and exact package versions are in dependencies.json. This is not a clean-environment or
cross-platform certification. Hashes check identity/integrity, not safety/authenticity of unknown pickle/code.
Only this explicitly pinned project model/custom class can load. Do not treat arbitrary modified packages as trusted.

Outputs approximate repository-guided synthetic scalars, not measured or GMMNLSE performance.
Intervals remain limited: empirical joint coverage 1936/2048 overall, 216/256 near_slice.
No per-point/group safety guarantee, physical truth or default-model replacement is implied.
This local review copy is not a public license grant; source/asset redistribution remains pending rights review.
""")
    dump(bundle / "manifest.json", {"schema_version": "mamyshev_mvp_inference_bundle_v1",
        "files": {path.name: sha(path) for path in sorted(bundle.iterdir())},
        "full_experiment_archive_replaced": False, "fixed_model_sha256": LOCKED["model.joblib"]})
    checked = verify(bundle)
    with zipfile.ZipFile(archive, "x", compression=zipfile.ZIP_DEFLATED) as stream:
        for path in sorted(bundle.iterdir()):
            stream.write(path, path.name)
    receipt = {"bundle": str(bundle.relative_to(ROOT)), "archive": str(archive.relative_to(ROOT)),
        "archive_sha256": sha(archive), "archive_bytes": archive.stat().st_size,
        "uncompressed_bytes": sum(p.stat().st_size for p in bundle.iterdir()), "verification": checked,
        "model_deserialization_performed": False, "prediction_rows": 0, "new_labels": 0}
    dump(OUT / "bundle_build.json", receipt)
    print(json.dumps(receipt, indent=2))


if __name__ == "__main__":
    main()
