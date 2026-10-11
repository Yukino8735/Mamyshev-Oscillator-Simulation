#!/usr/bin/env python3
"""One bounded, instrumented AppTest plus independently copied Demo check."""
from pathlib import Path
import argparse
import csv
import hashlib
import importlib.util
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]
ALLOW = (
    "demo/app.py", "demo/ui_logic.py", "demo/predict.py",
    "src/mamyshev_ml/__init__.py", "src/mamyshev_ml/demo_inference.py",
    "src/mamyshev_ml/v4_evaluators.py", "src/mamyshev_ml/v4_scan.py",
    "mamyshev_accuracy_v4/configs/domain.json", "mamyshev_accuracy_v4/configs/scenarios.json",
    "tests/test_demo_ui_logic.py", "scripts/check_demo_ui.py",
)


def write(path, value):
    with path.open("x") as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write("\n")


def copy_demo(destination):
    destination.mkdir(exist_ok=False)
    sources = [ROOT / p for p in ALLOW]
    sources += [p for p in (ROOT / "demo/assets").rglob("*") if p.is_file()]
    files = []
    for path in sources:
        relative = path.relative_to(ROOT)
        if path.is_symlink() or "__pycache__" in relative.parts:
            if "__pycache__" in relative.parts:
                continue
            raise ValueError("No symlinks in standalone copy")
        if path.suffix.lower() not in {".py", ".json", ".png", ".joblib", ".md", ".txt"}:
            raise ValueError("Unexpected public preview file: " + str(relative))
        if path.suffix in {".json", ".py", ".md", ".txt"} and (b"/" + b"Users/") in path.read_bytes():
            raise ValueError("Private absolute path in preview: " + str(relative))
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, target)
        files.append({"path": str(relative), "bytes": path.stat().st_size,
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
    write(destination / "preview_manifest.json", {"files": files,
        "public_release_blocked": True, "reason": "Internal functional copy includes assets with pending distribution/attribution review; not a publication approval",
        "includes_datasets": False, "clean_environment_tested": False})
    return files


def inside(output):
    """Run in the outside-repository copy with explicit local-only imports."""
    sys.path.insert(0, str(ROOT / "src"))
    sys.path.insert(0, str(ROOT / "demo"))
    from streamlit.testing.v1 import AppTest
    import numpy as np
    from mamyshev_ml.demo_inference import load_catalog
    from ui_logic import DEFAULT, TARGETS, prediction_csv
    assets = ROOT / "demo/assets/models"
    catalog = load_catalog(assets)
    model_ids = list(catalog["models"])
    started = time.monotonic()
    counters = {"fit_calls": 0, "oracle_calls": 0, "evaluation_calls": 0, "MATLAB_calls": 0,
                "prediction_calls": 0}

    def guard(frame, event, arg):
        if event != "call":
            return guard
        name = frame.f_code.co_name
        file = frame.f_code.co_filename
        reason = None
        if name in {"fit", "partial_fit", "fit_transform", "calibrate", "run_calibration"}:
            counters["fit_calls"] += 1
            reason = "fit"
        if file.endswith("oracle.py"):
            counters["oracle_calls"] += 1
            reason = "oracle"
        if name in {"evaluate", "execute_authorized_design", "run_supervised"} and ("v4_evaluators" in file or "authorization" in file or "supervisor" in file):
            counters["evaluation_calls"] += 1
            reason = "Evaluation/live backend"
        if name == "predict" and file.endswith("models_v4.py"):
            counters["prediction_calls"] += 1
        if reason:
            raise AssertionError("Forbidden Demo runtime call: " + reason)
        return guard

    old_profile = sys.getprofile()
    old_thread_profile = threading.getprofile()
    original_popen = subprocess.Popen

    def guarded_popen(*args, **kwargs):
        submitted = args[0] if args else kwargs.get("args", "")
        command = " ".join(map(str, submitted)) if isinstance(submitted, (list, tuple)) else str(submitted)
        if "matlab" in command.lower() or "run_mamyshev" in command.lower():
            counters["MATLAB_calls"] += 1
            raise AssertionError("Forbidden external MATLAB/production-launch attempt from Demo: " + command)
        return original_popen(*args, **kwargs)

    subprocess.Popen = guarded_popen
    sys.setprofile(guard)
    threading.setprofile(guard)
    cases = []
    comparisons = []
    try:
        for model_id in model_ids:
            at = AppTest.from_file(str(ROOT / "demo/app.py"), default_timeout=20).run()
            assert not at.exception, str(at.exception)
            at.selectbox(key="model_id").set_value(model_id).run()
            at.button(key="predict").click().run()
            assert not at.exception and not at.error, str(at.exception)
            ui = at.session_state["single_result"]
            assert ui["model_id"] == model_id
            assert len(at.metric) == 3
            cases.append({"case": "single_actual_prediction", "model_id": model_id, "n_train": ui["n_train"], "passed": True})
            # Calling the same CLI main is an in-process command boundary; no process fallback.
            input_path, output_path = output / (model_id + "_input.json"), output / (model_id + "_cli.json")
            write(input_path, DEFAULT)
            spec = importlib.util.spec_from_file_location("_demo_cli", ROOT / "demo/predict.py")
            cli = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(cli)
            saved_argv = sys.argv
            try:
                sys.argv = ["demo/predict.py", "--model-id", model_id, "--input", str(input_path), "--out", str(output_path)]
                cli.main()
            finally:
                sys.argv = saved_argv
            command = json.loads(output_path.read_text())
            a = [ui["predictions"][0]["targets"][k] for k in TARGETS]
            b = [command["predictions"][0]["targets"][k] for k in TARGETS]
            np.testing.assert_allclose(a, b, atol=1e-10, rtol=1e-10)
            comparisons.append({"model_id": model_id, "max_abs_difference": float(np.max(np.abs(np.asarray(a) - b))), "atol": 1e-10, "rtol": 1e-10})
            at.number_input(key="single_pump_power_W").set_value(4.1)
            at.button(key="predict").click().run()
            assert at.session_state["single_result"]["predictions"][0]["design"]["pump_power_W"] == 4.1
            at.text_area(key="exact_json").set_value('{"pump_power_W": 4}')
            at.button(key="predict").click().run()
            assert at.error and "single_result" not in at.session_state
            cases.append({"case": "changed_input_and_invalid_json_rejection", "model_id": model_id, "passed": True})
            at.radio(key="page").set_value("Parameter scan").run()
            at.number_input(key="scan_n").set_value(3)
            at.button(key="run_scan").click().run()
            assert not at.exception and at.session_state["scan_result"]["prediction"]["n_predictions"] == 3
            # Streamlit 1.64 enqueues VegaLiteChart as "vega_lite_chart".
            # Its UnknownElement exposes the actual protobuf spec and datasets.
            charts = at.get("vega_lite_chart")
            assert charts and json.loads(charts[0].proto.spec)
            assert charts[0].proto.datasets or charts[0].proto.data.data
            at.selectbox(key="scan_mode").set_value("2D")
            at.button(key="run_scan").click().run()
            assert not at.exception and at.session_state["scan_result"]["prediction"]["n_predictions"] == 9
            assert len(at.dataframe) >= 1
            exported = at.session_state["scan_result"]["prediction"]
            csv_rows = list(csv.DictReader(io.StringIO(prediction_csv(exported))))
            assert len(csv_rows) == 9
            for reread, original in zip(csv_rows, exported["predictions"]):
                np.testing.assert_allclose([float(reread[k]) for k in TARGETS],
                    [original["targets"][k] for k in TARGETS], atol=1e-10, rtol=1e-10)
                assert reread["kind"] == "Prediction" and reread["model_id"] == model_id
            write(output / (model_id + "_scan_export.json"), exported)
            cases.append({"case": "one_and_two_axis_scan_with_actual_chart", "model_id": model_id, "passed": True})
            at.radio(key="page").set_value("Design exploration").run()
            scenarios = json.loads((ROOT / "demo/assets/scenarios.json").read_text())["scenarios"]
            for scenario in scenarios:
                at.selectbox(key="scenario").set_value(scenario["id"])
                at.number_input(key="candidate_n").set_value(32)
                at.button(key="rank").click().run()
                assert not at.exception and not at.error, str(at.exception)
                current = at.session_state["candidate_result"]
                assert 0 < current["prediction"]["n_predictions"] <= 32
                assert current["scenario"] == scenario["id"]
            cases.append({"case": "four_x_only_scenarios_history_and_pending_export", "model_id": model_id, "passed": True})
            at.radio(key="page").set_value("MATLAB pipeline").run()
            assert not at.exception
            assert len(at.button) == 0
            assert any("not_run" in e.value for e in at.info)
            cases.append({"case": "pipeline_view_no_live_button", "model_id": model_id, "passed": True})

        # Missing trusted model bytes must fail before inference, even in a process
        # that previously imported the verified class. Restore this private copy.
        weight = next((assets / "v42").glob("*.joblib"))
        moved = weight.with_suffix(".held")
        weight.rename(moved)
        before = counters["prediction_calls"]
        try:
            bad = AppTest.from_file(str(ROOT / "demo/app.py"), default_timeout=20).run()
            assert bad.error and "unavailable" in bad.error[0].value
            assert counters["prediction_calls"] == before
        finally:
            moved.rename(weight)
        cases.append({"case": "missing_model_no_fallback", "passed": True})
        spec = importlib.util.spec_from_file_location("test_demo_ui_logic", ROOT / "tests/test_demo_ui_logic.py")
        tests = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(tests)
        suite = unittest.defaultTestLoader.loadTestsFromModule(tests)
        result = unittest.TextTestRunner(verbosity=2).run(suite)
        assert result.wasSuccessful()
        # Every model custom class came from this independent copy.
        module = sys.modules["models_v4"]
        assert Path(module.__file__).resolve().is_relative_to(ROOT)
    finally:
        subprocess.Popen = original_popen
        sys.setprofile(old_profile)
        threading.setprofile(old_thread_profile)
    value = {"status": "passed", "cases": cases, "UI_vs_same_model_CLI": comparisons,
        "unit_test_methods": result.testsRun, "runtime_counts": counters,
        "independent_copy": True, "cwd": str(Path.cwd()), "root": str(ROOT),
        "PYTHONPATH": os.environ.get("PYTHONPATH"), "existing_environment_only": True,
        "browser_visual_check": "not_run_AppTest_is_component_simulation",
        "elapsed_s": time.monotonic() - started}
    write(output / "app_test_result.json", value)
    print(json.dumps({"status": "passed", "cases": len(cases), "counts": counters}))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--inside", action="store_true")
    args = parser.parse_args()
    if args.inside:
        inside(args.out.resolve())
        return
    args.out.mkdir(parents=True, exist_ok=False)
    external = Path(tempfile.mkdtemp(prefix="mamyshev_demo_review_")) / "preview"
    files = copy_demo(external)
    env = dict(os.environ)
    env.pop("PYTHONPATH", None)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    command = [sys.executable, "-I", "-B", str(external / "scripts/check_demo_ui.py"), "--inside", "--out", str(args.out.resolve())]
    write(args.out / "independent_copy.json", {"directory": str(external), "files": files,
        "public_release_blocked": True, "command": command, "PYTHONPATH_removed": True})
    completed = subprocess.run(command, cwd=external, env=env, text=True, capture_output=True, timeout=140)
    (args.out / "stdout.log").write_text(completed.stdout)
    (args.out / "stderr.log").write_text(completed.stderr)
    write(args.out / "process.json", {"returncode": completed.returncode,
        "internal_preview": str(external), "server_started": False})
    if completed.returncode:
        print(completed.stderr, file=sys.stderr)
        raise SystemExit(completed.returncode)
    print(completed.stdout)


if __name__ == "__main__":
    main()
