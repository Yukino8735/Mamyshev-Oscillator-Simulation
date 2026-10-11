#!/usr/bin/env python3
"""Targeted serialized-spec AppTest; not a JavaScript/browser rendering test.

Run before and after the local adapter change under run_demo_chart_budget.py.
Each process covers one frozen model, two grid sizes and all three targets.
"""
import argparse
import copy
import importlib.metadata
import io
import json
from pathlib import Path
import subprocess
import sys
import threading
import time
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "demo"))


def write(path, value):
    with path.open("x") as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write("\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=["before", "after"])
    parser.add_argument("model_id", choices=["v42_T2_K64_A0001", "demo_10k_v1"])
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if not args.output.is_absolute():
        args.output = ROOT / args.output
    out = args.output / args.mode / args.model_id
    out.mkdir(parents=True, exist_ok=False)
    counters = dict(fit=0, oracle=0, Evaluation=0, MATLAB=0, predict=0)
    cases = []
    started = time.monotonic()

    def guard(frame, event, arg):
        if event != "call":
            return guard
        name, file = frame.f_code.co_name, frame.f_code.co_filename
        key = None
        if name in {"fit", "partial_fit", "fit_transform", "calibrate", "run_calibration"}:
            key = "fit"
        if file.endswith("oracle.py"):
            key = "oracle"
        if name in {"evaluate", "execute_authorized_design", "run_supervised"} and any(
                s in file for s in ("v4_evaluators", "authorization", "supervisor")):
            key = "Evaluation"
        if name == "predict" and file.endswith("models_v4.py"):
            counters["predict"] += 1
        if key:
            counters[key] += 1
            raise AssertionError("Forbidden runtime call: " + key)
        return guard

    original_popen = subprocess.Popen

    def popen(*a, **kw):
        command = a[0] if a else kw.get("args", "")
        if any(s in str(command).lower() for s in ("matlab", "run_mamyshev")):
            counters["MATLAB"] += 1
            raise AssertionError("Forbidden MATLAB call")
        return original_popen(*a, **kw)

    old_profile, old_thread_profile = sys.getprofile(), threading.getprofile()
    sys.setprofile(guard); threading.setprofile(guard)
    failure = None
    try:
        import altair as alt
        import pyarrow as pa
        from streamlit.testing.v1 import AppTest
        from streamlit.delta_generator import DeltaGenerator
        from mamyshev_ml.demo_inference import FEATURES, TARGETS, BOUNDS, MODELS
        from ui_logic import DEFAULT, prediction_csv, rank_predictions
        import ui_charts
        downloads = {}
        original_download = DeltaGenerator.download_button

        def download(self, label, data, *a, **kw):
            downloads[kw.get("key", label)] = data
            return original_download(self, label, data, *a, **kw)

        def clean(at):
            assert not at.exception, str(at.exception)

        def table_and_exports(at, result):
            json_export = downloads["response_prediction_json"]
            csv_export = downloads["response_prediction_csv"]
            assert json.loads(json_export) == result
            assert csv_export == prediction_csv(result)
            expected = [{**r["design"], **r["targets"]} for r in result["predictions"]]
            assert any(d.value.to_dict("records") == expected for d in at.dataframe)
            assert result["Evaluation_created"] == 0 and result["kind"] == "Prediction"
            return {"json": json_export, "csv": csv_export}

        with patch.object(subprocess, "Popen", popen), patch.object(DeltaGenerator, "download_button", download):
            at = AppTest.from_file(str(ROOT / "demo/app.py"), default_timeout=8).run()
            clean(at)
            assert at.session_state["model_id"] == "v42_T2_K64_A0001"
            if args.model_id != "v42_T2_K64_A0001":
                at.selectbox(key="model_id").set_value(args.model_id).run(); clean(at)
            at.radio(key="page").set_value("Parameter response").run(); clean(at)
            assert at.session_state["baseline_design"] == DEFAULT
            assert at.selectbox(key="axis1").value == "filter2_bw_nm"
            for mode, n in (("1D", 9), ("2D", 81)):
                if mode == "2D":
                    at.selectbox(key="scan_mode").set_value(mode).run(); clean(at)
                    assert "scan_result" not in at.session_state
                    assert at.selectbox(key="axis2").value == "filter_offset_nm"
                for target in TARGETS:
                    at.selectbox(key="scan_target").set_value(target).run(); clean(at)
                    assert "scan_result" not in at.session_state
                    assert "latest_chart_spec" not in at.session_state
                    downloads.clear()
                    at.button(key="run_scan").click().run(); clean(at)
                    assert not at.error, str(at.error)
                    saved = at.session_state["scan_result"]
                    result = saved["prediction"]
                    assert result["n_predictions"] == n
                    assert saved["request"]["ranges"]["filter2_bw_nm"] == BOUNDS["filter2_bw_nm"]
                    assert saved["request"]["counts"]["filter2_bw_nm"] == 9
                    assert all(r["design"]["pump_power_W"] == 4 and r["design"]["gain_length_m"] == 4
                               for r in result["predictions"])
                    if mode == "1D":
                        assert all(r["design"]["filter_offset_nm"] == 10 for r in result["predictions"])
                    else:
                        assert saved["request"]["ranges"]["filter_offset_nm"] == BOUNDS["filter_offset_nm"]
                    chart = at.get("vega_lite_chart")[0]
                    final = json.loads(chart.proto.spec)
                    alt.LayerChart.from_dict(final, validate=True)
                    assert final["padding"] == (16 if args.mode == "before" else dict.fromkeys(
                        ("left", "right", "top", "bottom"), 16))
                    assert all("padding" not in layer for layer in final["layer"])
                    datasets = {}
                    for dataset in chart.proto.datasets:
                        datasets[dataset.name] = pa.ipc.open_stream(io.BytesIO(dataset.data.data)).read_all().to_pylist()
                    original = at.session_state["latest_chart_spec"]
                    for layer in final["layer"]:
                        data = layer["data"]
                        cells = data.get("values", datasets.get(data.get("name")))
                        expected = next(v for v in original["layer"] if v["name"] == layer["name"])["data"]["values"]
                        assert cells == expected
                    main_layer = final["layer"][0]
                    assert main_layer["mark"]["type"] == ("line" if mode == "1D" else "rect")
                    markers = {v["name"]: v["data"]["values"][0] for v in original["layer"][1:]}
                    assert all(markers["baseline_marker"][k] == DEFAULT[k] for k in FEATURES)
                    ranked = rank_predictions(result, saved["scenario"])
                    if ranked:
                        assert all(markers["best_feasible_marker"][k] == ranked[0]["targets"][k] for k in TARGETS)
                    exports = table_and_exports(at, result)
                    record = {"request": saved["request"], "prediction": result, "final_spec": final,
                        "datasets": datasets, "exports": exports, "summary": at.session_state["latest_chart_summary"]}
                    name = mode + "_" + target + ".json"
                    write(out / name, record)
                    if args.mode == "after":
                        old = json.loads((args.output / "before" / args.model_id / name).read_text())
                        comparable = copy.deepcopy(record)
                        comparable["final_spec"]["padding"] = 16
                        assert comparable == old, "Unexpected change beyond top-level padding"
                    cases.append({"case": name, "rows": n, "final_padding": final["padding"],
                        "schema_valid": True, "exact_before_after_equal_except_padding": args.mode == "after"})
            if args.mode == "after":
                # A Python chart rejection must leave current data/export accessible.
                result = at.session_state["scan_result"]["prediction"]
                downloads.clear()
                with patch.object(ui_charts, "response_chart", side_effect=ValueError("chart-only fixture failure")):
                    at.run(); clean(at)
                assert any("chart-only fixture failure" in e.value for e in at.error)
                table_and_exports(at, result)
                cases.append({"case": "chart_failure_retains_current_table_exports", "passed": True})
                at.number_input(key="scan_fixed_pump_power_W").set_value(4.1).run(); clean(at)
                assert "scan_result" not in at.session_state and "latest_chart_spec" not in at.session_state
                assert not any(b.key.startswith("response_prediction_") for b in at.get("download_button"))
                at.button(key="run_scan").click().run(); clean(at)
                assert at.session_state["latest_chart_summary"]["baseline_marker"]["status"] == "omitted"
                assert all(r["design"]["pump_power_W"] == 4.1 for r in at.session_state["scan_result"]["prediction"]["predictions"])
                cases.append({"case": "fixed_change_invalidates_and_uses_new_slice", "passed": True})
                at.number_input(key="response_constraint_S3_fixed_hardware_compressed_duration_fs_lte").set_value(0.).run(); clean(at)
                assert "scan_result" not in at.session_state
                at.button(key="run_scan").click().run(); clean(at)
                assert at.session_state["latest_chart_summary"]["n_feasible"] == 0
                assert not any(v["name"] == "best_feasible_marker" for v in at.session_state["latest_chart_spec"]["layer"])
                cases.append({"case": "no_feasible_no_best_marker_no_constraint_relaxation", "passed": True})
            metadata = at.session_state["baseline_result"]
            write(out / "identity.json", {"model_id": args.model_id,
                "path": str(ROOT / "demo/assets/models" / MODELS[args.model_id][0] / "model.joblib"),
                "sha256": metadata["model_sha256"], "q": metadata["q_joint_log"],
                "versions": {n: importlib.metadata.version(n) for n in ("streamlit", "altair", "pyarrow")}})
    except BaseException as exc:
        failure = repr(exc)
        raise
    finally:
        sys.setprofile(old_profile); threading.setprofile(old_thread_profile)
        write(out / "result.json", {"cases": cases, "counters": counters, "error": failure,
            "internal_wall_s": time.monotonic() - started, "browser_visual_check": "not_run",
            "comparison_rule": "exact JSON/CSV/spec/dataset equality except top-level padding"})


if __name__ == "__main__":
    main()
