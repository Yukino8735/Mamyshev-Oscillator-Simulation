#!/usr/bin/env python3
"""Bounded task journey in an outside-repository, data-free Demo copy.

This is AppTest component simulation, not browser visual acceptance. The previous
copy implementation and process guard are reused; no HTTP server is started.
"""
from pathlib import Path
import argparse
import hashlib
import importlib.util
import io
import json
import os
import subprocess
import sys
import tempfile
import threading
import time
import traceback
import unittest

ROOT = Path(__file__).resolve().parents[1]


def write(path, value):
    with Path(path).open("x") as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write("\n")


def module_from_file(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main_inside(output):
    sys.path.insert(0, str(ROOT / "src"))
    sys.path.insert(0, str(ROOT / "demo"))
    from streamlit.testing.v1 import AppTest
    import numpy as np
    from mamyshev_ml.demo_inference import predict, load_model, load_catalog, FEATURES, TARGETS
    from ui_logic import DEFAULT, compare_predictions, constraint_rows
    assets = ROOT / "demo/assets/models"
    catalog = load_catalog(assets)
    counters = {"fit_calls": 0, "oracle_calls": 0, "Evaluation_calls": 0,
                "MATLAB_calls": 0, "prediction_calls": 0}
    cases, comparisons, timings = [], [], []
    started = time.monotonic()

    def guard(frame, event, arg):
        if event != "call":
            return guard
        name, file = frame.f_code.co_name, frame.f_code.co_filename
        reason = None
        if name in {"fit", "partial_fit", "fit_transform", "calibrate", "run_calibration"}:
            counters["fit_calls"] += 1; reason = "fit/calibration"
        if file.endswith("oracle.py"):
            counters["oracle_calls"] += 1; reason = "oracle"
        if name in {"evaluate", "execute_authorized_design", "run_supervised"} and any(s in file for s in ("v4_evaluators", "authorization", "supervisor")):
            counters["Evaluation_calls"] += 1; reason = "Evaluation/live backend"
        if name == "predict" and file.endswith("models_v4.py"):
            counters["prediction_calls"] += 1
        if reason:
            raise AssertionError("Forbidden Demo runtime call: " + reason)
        return guard

    old_profile, old_thread_profile = sys.getprofile(), threading.getprofile()
    original_popen = subprocess.Popen

    def guarded_popen(*args, **kwargs):
        submitted = args[0] if args else kwargs.get("args", "")
        command = " ".join(map(str, submitted)) if isinstance(submitted, (list, tuple)) else str(submitted)
        if "matlab" in command.lower() or "run_mamyshev" in command.lower():
            counters["MATLAB_calls"] += 1
            raise AssertionError("Forbidden MATLAB launch from Demo")
        return original_popen(*args, **kwargs)

    subprocess.Popen = guarded_popen
    sys.setprofile(guard); threading.setprofile(guard)
    failure, tests_run = None, None

    def clean(at):
        assert not at.exception, str(at.exception)

    def missing(at, key):
        assert key not in at.session_state, "stale state retained: " + key

    def mark(name, **extra):
        cases.append({"case": name, "passed": True, **extra})

    def values(row):
        return np.array([row["targets"][k] for k in TARGETS])

    def same(actual, expected):
        np.testing.assert_allclose(actual, expected, atol=1e-10, rtol=1e-10)

    try:
        # Fixtures and affected old regressions run once in a separate bounded
        # component process. This process covers actual AppTest interactions.
        tests_run = 0
        # Measure verified loading separately from warm coefficient prediction.
        for model_id in catalog["models"]:
            begin = time.perf_counter(); model, metadata = load_model(assets, model_id)
            loading = time.perf_counter() - begin
            x = [[DEFAULT[k] for k in FEATURES]]
            model.predict(x)
            begin = time.perf_counter(); warm = model.predict(x)
            warm_s = time.perf_counter() - begin
            timings.append({"model_id": model_id, "verified_model_loading_s": loading,
                            "warm_predict_s": warm_s, "n_rows": 1,
                            "warm_target_values": np.asarray(warm).tolist(),
                            "includes_rendering": False, "is_speedup_claim": False})

        at = AppTest.from_file(str(ROOT / "demo/app.py"), default_timeout=10).run()
        clean(at)
        assert at.session_state["model_id"] == catalog["default_model_id"]
        at.button(key="load_example").click().run(); clean(at)
        assert at.session_state["model_id"] == "demo_10k_v1"
        assert at.session_state["baseline_design"] == DEFAULT
        baseline = at.session_state["baseline_result"]
        assert baseline["n_train"] == 10000 and baseline["predictions"][0]["design"] == DEFAULT
        at.button(key="predict_current").click().run(); clean(at)
        mark("explicit_10k_example_load_and_same_model_baseline", baseline=baseline["predictions"][0])
        for model_id in ("demo_10k_v1", "v42_T2_K64_A0001"):
            if at.session_state["model_id"] != model_id:
                at.selectbox(key="model_id").set_value(model_id).run(); clean(at)
                missing(at, "current_result")
                at.button(key="predict_current").click().run(); clean(at)
            ui = at.session_state["current_result"]["prediction"]
            direct = predict(assets, model_id, [DEFAULT])
            same(values(ui["predictions"][0]), values(direct["predictions"][0]))
            input_path, output_path = output / (model_id + "_input.json"), output / (model_id + "_cli.json")
            write(input_path, DEFAULT)
            cli = module_from_file("_demo_cli", ROOT / "demo/predict.py")
            saved_argv = sys.argv
            try:
                sys.argv = ["demo/predict.py", "--model-id", model_id, "--input", str(input_path), "--out", str(output_path)]
                cli.main()
            finally:
                sys.argv = saved_argv
            command = json.loads(output_path.read_text())
            same(values(ui["predictions"][0]), values(command["predictions"][0]))
            comparisons.append({"model_id": model_id, "atol": 1e-10, "rtol": 1e-10,
                                "UI_vs_direct_max_abs": float(np.max(abs(values(ui["predictions"][0]) - values(direct["predictions"][0])))),
                                "UI_vs_CLI_max_abs": float(np.max(abs(values(ui["predictions"][0]) - values(command["predictions"][0])))),
                                "q_joint_log": ui["q_joint_log"], "model_sha256": ui["model_sha256"]})
        mark("both_models_UI_direct_CLI_same_input_fixed_tolerance")

        at.button(key="load_example").click().run(); clean(at)
        at.number_input(key="candidate_n").set_value(512)
        at.number_input(key="candidate_seed").set_value(72001)
        at.button(key="rank").click().run(); clean(at)
        current = at.session_state["candidate_result"]
        ranked = current["ranked"]
        assert len(ranked) >= 3, "Explicit finite example has fewer than three feasible predictions"
        assert current["prediction"]["n_predictions"] <= 512
        assert current["scenario"]["id"] == "S3_fixed_hardware"
        target = TARGETS[2]
        assert all(r["design"]["pump_power_W"] == 4 and r["design"]["gain_length_m"] == 4 for r in ranked)
        assert all(r["targets"][TARGETS[1]] <= 40 for r in ranked)
        assert [r["targets"][target] for r in ranked] == sorted([r["targets"][target] for r in ranked], reverse=True)
        direct_rank = predict(assets, "demo_10k_v1", [r["design"] for r in ranked[:3]])
        for actual, expected in zip(ranked[:3], direct_rank["predictions"]):
            same(values(actual), values(expected))
        at.selectbox(key="candidate_focus").set_value(1).run(); clean(at)
        at.multiselect(key="selected_candidates").set_value([0, 1, 2]).run(); clean(at)
        tables = [element.value for element in at.dataframe]
        top_table = next(table for table in tables if set(FEATURES).issubset(table.columns))
        for index, (_, displayed) in enumerate(top_table.iterrows()):
            same([displayed[t] for t in TARGETS], values(ranked[index]))
            same([displayed[f] for f in FEATURES], [ranked[index]["design"][f] for f in FEATURES])
            assert displayed["Model"] == "demo_10k_v1" and displayed["Source"] == "predicted_not_verified"
        comparison_table = next(table for table in tables if "Candidate − baseline" in table.columns)
        same(comparison_table["Candidate"].to_numpy(), values(ranked[1]))
        same(comparison_table["Baseline"].to_numpy(), values(current["baseline"]))
        same(comparison_table["Candidate − baseline"].to_numpy(), values(ranked[1]) - values(current["baseline"]))
        pending = at.session_state["pending_request"]
        assert len(pending["requests"]) == 3 and pending["max_new_real_attempts"] == 0
        assert pending["source_model_id"] == "demo_10k_v1"
        for actual, expected in zip(pending["requests"], ranked[:3]):
            assert actual["design_config"] == expected["design"]
            same([actual["prediction"][t] for t in TARGETS], values(expected))
            assert actual["real_targets"] is None and actual["evaluation_id"] is None
        evidence = {"count_requested": 512, "candidate_seed": 72001,
                    "plan": current["plan"], "scenario": current["scenario"],
                    "prediction": current["prediction"], "n_point_feasible": len(ranked),
                    "baseline": current["baseline"], "top_three": ranked[:3],
                    "selected_comparison": compare_predictions(current["baseline"], ranked[1], current["scenario"]["objective"]),
                    "pending": pending}
        write(output / "actual_example.json", evidence)
        mark("rank_selection_exact_values_and_three_zero_authority_requests", feasible_count=len(ranked), prediction_count=current["prediction"]["n_predictions"])

        # Each changed dependency invalidates old candidates before resubmission.
        constraint_key = "constraint_S3_fixed_hardware_compressed_duration_fs_lte"
        at.number_input(key=constraint_key).set_value(1.).run(); clean(at)
        missing(at, "candidate_result"); missing(at, "pending_request")
        at.button(key="rank").click().run(); clean(at)
        assert not at.session_state["candidate_result"]["ranked"]
        missing(at, "pending_request")
        at.number_input(key=constraint_key).set_value(40.).run()
        at.button(key="rank").click().run(); clean(at)
        at.number_input(key="candidate_seed").set_value(72002).run(); clean(at)
        missing(at, "candidate_result")
        at.button(key="rank").click().run(); clean(at)
        at.number_input(key="cand_S3_fixed_hardware_filter_offset_nm_lo").set_value(8.1).run(); clean(at)
        missing(at, "candidate_result")
        mark("constraint_no_feasible_seed_and_range_changes_invalidate")
        for scenario_id in ("S1_peak_under_40fs", "S2_low_pump", "S4_short_pulse"):
            at.selectbox(key="scenario").set_value(scenario_id).run(); clean(at)
            missing(at, "candidate_result")
            at.button(key="rank").click().run(); clean(at)
            assert at.session_state["candidate_result"]["scenario"]["id"] == scenario_id
        at.selectbox(key="scenario").set_value("S1_peak_under_40fs").run(); clean(at)
        at.checkbox(key="cand_S1_peak_under_40fs_pump_power_W_vary").set_value(False).run(); clean(at)
        at.number_input(key="cand_S1_peak_under_40fs_pump_power_W_fixed").set_value(5.).run(); clean(at)
        at.button(key="rank").click().run(); clean(at)
        fixed_case = at.session_state["candidate_result"]
        assert fixed_case["scenario"]["fixed_inputs"]["pump_power_W"] == 5.
        assert fixed_case["ranked"] and all(r["design"]["pump_power_W"] == 5. for r in fixed_case["ranked"])
        baseline_check = next(item for item in fixed_case["comparison"]["baseline_constraints"]
                              if item["field"] == "pump_power_W" and item["operator"] == "eq")
        assert baseline_check["value"] == 4. and baseline_check["boundary"] == 5. and not baseline_check["point_pass"]
        pending_fixed = at.session_state["pending_request"]
        assert pending_fixed["scenario"]["fixed_inputs"]["pump_power_W"] == 5.
        assert pending_fixed["max_new_real_attempts"] == 0
        assert all(r["real_targets"] is None for r in pending_fixed["requests"])
        mark("user_fixed_input_is_effective_constraint_in_comparison_and_pending_snapshot")
        at.selectbox(key="model_id").set_value("v42_T2_K64_A0001").run(); clean(at)
        missing(at, "candidate_result"); missing(at, "pending_request")
        assert at.session_state["baseline_result"]["model_id"] == "v42_T2_K64_A0001"
        at.button(key="predict_current").click().run(); clean(at)
        at.number_input(key="current_pump_power_W").set_value(4.1).run(); clean(at)
        missing(at, "current_result")
        at.button(key="set_baseline").click().run(); clean(at)
        assert at.session_state["baseline_design"]["pump_power_W"] == 4.1
        assert at.session_state["baseline_result"]["predictions"][0]["design"]["pump_power_W"] == 4.1
        at.number_input(key="current_gain_length_m").set_value(4.15).run(); clean(at)
        at.button(key="predict_current").click().run(); clean(at)
        assert at.error
        missing(at, "current_result")
        mark("all_scenarios_model_current_input_and_invalid_length")

        at.button(key="load_example").click().run(); clean(at)
        at.radio(key="page").set_value("Parameter response").run(); clean(at)
        at.selectbox(key="axis1").set_value("filter_offset_nm").run(); clean(at)
        at.number_input(key="scan_axis1_filter_offset_nm_lo").set_value(8.)
        at.number_input(key="scan_axis1_filter_offset_nm_hi").set_value(12.)
        at.number_input(key="scan_n1").set_value(3)
        at.button(key="run_scan").click().run(); clean(at)
        one = at.session_state["scan_result"]
        assert one["prediction"]["n_predictions"] == 3
        offsets = [r["design"]["filter_offset_nm"] for r in one["prediction"]["predictions"]]
        assert offsets == [8., 10., 12.]
        spec = at.session_state["latest_chart_spec"]
        assert any(v.get("name") == "prediction_curve" for v in spec["layer"])
        mark("one_dimensional_actual_input_order_units_and_three_predictions")
        at.selectbox(key="scan_mode").set_value("2D").run(); clean(at)
        missing(at, "scan_result")
        at.selectbox(key="axis2").set_value("filter2_bw_nm").run(); clean(at)
        at.number_input(key="scan_axis2_filter2_bw_nm_lo").set_value(2.)
        at.number_input(key="scan_axis2_filter2_bw_nm_hi").set_value(4.)
        at.number_input(key="scan_n1").set_value(21)
        at.number_input(key="scan_n2").set_value(21)
        at.button(key="run_scan").click().run(); clean(at)
        two = at.session_state["scan_result"]
        assert two["prediction"]["n_predictions"] == 441
        spec = at.session_state["latest_chart_spec"]
        charts = at.get("vega_lite_chart")
        assert charts, "No actual Streamlit Vega-Lite output"
        rendered = json.loads(charts[0].proto.spec)
        layer = next(v for v in rendered["layer"] if v.get("name") == "prediction_cells")
        assert layer["mark"]["type"] == "rect" if isinstance(layer["mark"], dict) else layer["mark"] == "rect"
        enc = layer["encoding"]
        assert all(k in enc for k in ("x", "x2", "y", "y2", "color"))
        assert "MW" in json.dumps(enc["color"])
        assert "nm" in json.dumps(enc["x"]) and "nm" in json.dumps(enc["y"])
        names = {v.get("name") for v in rendered["layer"]}
        assert {"baseline_marker", "best_feasible_marker"} <= names
        # Independently inspect the exact submitted spec's row values and geometry.
        original_layer = next(v for v in spec["layer"] if v.get("name") == "prediction_cells")
        data = original_layer.get("data", spec.get("data", {}))
        cells = data.get("values", spec.get("datasets", {}).get(data.get("name")))
        assert len(cells) == 441
        rendered_data = layer.get("data", rendered.get("data", {}))
        rendered_cells = rendered_data.get("values")
        if rendered_cells is None:
            name = rendered_data.get("name")
            rendered_cells = rendered.get("datasets", {}).get(name)
        if rendered_cells is None:
            import pyarrow as pa
            dataset = next(item for item in charts[0].proto.datasets if item.name == rendered_data["name"])
            rendered_cells = pa.ipc.open_stream(io.BytesIO(dataset.data.data)).read_all().to_pylist()
        assert len(rendered_cells) == 441
        for rendered_cell, original in zip(rendered_cells, cells):
            same([rendered_cell[f] for f in FEATURES], [original[f] for f in FEATURES])
            same([rendered_cell[t] for t in TARGETS], [original[t] for t in TARGETS])
            same([rendered_cell[k] for k in ("x_lo", "x_hi", "y_lo", "y_hi")],
                 [original[k] for k in ("x_lo", "x_hi", "y_lo", "y_hi")])
        predicted = two["prediction"]["predictions"]
        direct_cells = predict(assets, "demo_10k_v1", [r["design"] for r in predicted])
        for cell, row, independent in zip(cells, predicted, direct_cells["predictions"]):
            same(values(row), values(independent))
            assert cell[enc["color"]["field"]] == row["targets"][two["target"]]
            for axis, feature in (("x", "filter_offset_nm"), ("y", "filter2_bw_nm")):
                assert cell[enc[axis]["field"]] < row["design"][feature] < cell[enc[axis + "2"]["field"]]
        write(output / "actual_heatmap_spec.json", spec)
        write(output / "actual_scan_result.json", two)
        mark("actual_rect_heatmap_441_cell_values_units_bounds_baseline_best_markers")
        at.selectbox(key="scan_target").set_value(TARGETS[0]).run(); clean(at)
        missing(at, "scan_result"); missing(at, "latest_chart_spec")
        at.button(key="run_scan").click().run(); clean(at)
        assert at.session_state["scan_result"]["target"] == TARGETS[0]
        at.selectbox(key="axis1").set_value("pump_power_W").run(); clean(at)
        missing(at, "scan_result"); missing(at, "latest_chart_spec")
        at.selectbox(key="axis2").set_value("pump_power_W").run(); clean(at)
        at.button(key="run_scan").click().run(); clean(at)
        assert at.error
        missing(at, "scan_result"); missing(at, "latest_chart_spec")
        mark("plot_target_axis_changes_invalidate_and_repeated_axis_rejected")
        at.radio(key="page").set_value("Method & evidence").run(); clean(at)
        at.radio(key="page").set_value("MATLAB data pipeline").run(); clean(at)
        assert not any("run" in b.label.lower() or "launch" in b.label.lower() for b in at.button)
        mark("methods_history_and_zero_live_pipeline_render")

        # A deliberate UI-only failure fixture never supplies fabricated output.
        # Reject only a warmed current design while baseline DEFAULT still works.
        at.radio(key="page").set_value("Design workbench").run(); clean(at)
        at.button(key="load_example").click().run(); clean(at)
        at.number_input(key="current_pump_power_W").set_value(4.1).run(); clean(at)
        at.button(key="predict_current").click().run(); clean(at)
        assert "current_result" in at.session_state
        import streamlit as st
        import mamyshev_ml.demo_inference as inference
        original_predict = inference.predict
        rejected_calls = []

        def deliberate_UI_rejection(assets_root, selected_model, designs):
            if any(d["pump_power_W"] == 4.1 for d in designs):
                rejected_calls.append({"model_id": selected_model, "designs": designs})
                raise ValueError("UI-only injected prediction failure; no output produced")
            return original_predict(assets_root, selected_model, designs)

        st.cache_data.clear()
        inference.predict = deliberate_UI_rejection
        try:
            at.button(key="predict_current").click().run(); clean(at)
            assert at.error
            missing(at, "current_result")
            assert not any(element.value == "Current design vs baseline" for element in at.subheader)
            at.button(key="set_baseline").click().run(); clean(at)
            assert at.error
            assert at.session_state["baseline_design"] == DEFAULT
            assert at.session_state["baseline_result"]["predictions"][0]["design"] == DEFAULT
            assert len(rejected_calls) == 2
        finally:
            inference.predict = original_predict
            st.cache_data.clear()
        mark("UI_error_fixture_preserves_baseline_and_removes_old_current_display",
             deliberately_rejected_UI_requests=len(rejected_calls), fabricated_outputs=0)

        # Fail closed only in this copied directory; original trusted assets untouched.
        weight = assets / "v42/model.joblib"
        moved = weight.with_suffix(".held")
        weight.rename(moved)
        before = counters["prediction_calls"]
        try:
            failed = AppTest.from_file(str(ROOT / "demo/app.py"), default_timeout=10).run()
            assert failed.error and not failed.exception
            assert counters["prediction_calls"] == before
        finally:
            moved.rename(weight)
        mark("missing_copied_asset_fails_closed_before_prediction")
        assert Path(sys.modules["models_v4"].__file__).resolve().is_relative_to(ROOT)
        assert all(counters[k] == 0 for k in ("fit_calls", "oracle_calls", "Evaluation_calls", "MATLAB_calls"))
    except BaseException as error:
        failure = {"type": type(error).__name__, "message": str(error), "traceback": traceback.format_exc()}
    finally:
        subprocess.Popen = original_popen
        sys.setprofile(old_profile); threading.setprofile(old_thread_profile)
        value = {"status": "failed" if failure else "passed", "failure": failure,
                 "cases": cases, "test_methods": tests_run, "fixed_tolerance_comparisons": comparisons,
                 "runtime_counts": counters, "timings": timings, "independent_copy": True,
                 "cwd": str(Path.cwd()), "PYTHONPATH": os.environ.get("PYTHONPATH"),
                 "elapsed_s": time.monotonic() - started, "server_started": False,
                 "browser_visual_check": "not_run_AppTest_is_component_simulation"}
        write(output / "app_test_result.json", value)
    if failure:
        print(failure["traceback"], file=sys.stderr)
        raise SystemExit(1)
    print(json.dumps({"status": "passed", "test_methods": tests_run, "cases": len(cases), "runtime_counts": counters}))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--inside", action="store_true")
    args = parser.parse_args()
    if args.inside:
        main_inside(args.out.resolve()); return
    args.out.mkdir(parents=True, exist_ok=False)
    helper = module_from_file("_old_copy_helper", ROOT / "scripts/check_demo_ui.py")
    helper.ALLOW = tuple(p for p in helper.ALLOW if p != "tests/test_demo_ui_logic.py") + (
        "demo/ui_charts.py", "scripts/check_demo_ux.py", "tests/test_demo_ux.py")
    outside = Path(tempfile.mkdtemp(prefix="mamyshev_demo_ux_")) / "preview"
    files = helper.copy_demo(outside)
    env = dict(os.environ); env.pop("PYTHONPATH", None)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    for key in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS", "VECLIB_MAXIMUM_THREADS", "NUMEXPR_NUM_THREADS"):
        env[key] = "2"
    command = [sys.executable, "-I", "-B", str(outside / "scripts/check_demo_ux.py"), "--inside", "--out", str(args.out.resolve())]
    write(args.out / "independent_copy.json", {"directory": str(outside), "files": files,
         "command": command, "contains_datasets": False, "PYTHONPATH_removed": True,
         "public_release_blocked": True, "license_review_not_resolved": True})
    started = time.monotonic()
    try:
        completed = subprocess.run(command, cwd=outside, env=env, text=True, capture_output=True, timeout=50)
        stdout, stderr, returncode = completed.stdout, completed.stderr, completed.returncode
        timeout = False
    except subprocess.TimeoutExpired as error:
        stdout = error.stdout or ""; stderr = error.stderr or ""
        stdout = stdout.decode(errors="replace") if isinstance(stdout, bytes) else stdout
        stderr = stderr.decode(errors="replace") if isinstance(stderr, bytes) else stderr
        returncode, timeout = 124, True
    (args.out / "stdout.log").write_text(stdout)
    (args.out / "stderr.log").write_text(stderr)
    write(args.out / "process.json", {"returncode": returncode, "internal_timeout": timeout,
         "elapsed_s": time.monotonic() - started, "server_started": False,
         "outside_copy": str(outside), "internal_watchdog_s": 50})
    if returncode:
        print(stderr, file=sys.stderr)
        raise SystemExit(returncode)
    print(stdout)


if __name__ == "__main__":
    main()
