#!/usr/bin/env python3
"""One bounded serial replay demonstration; no new designs, labels or fitting."""
from __future__ import annotations

import csv
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
import zipfile

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports/local/mvp_closeout_001"
OLD = ROOT / "reports/local/application_v4_3_001/demonstration"
FEATURES = ("pump_power_W", "filter_offset_nm", "filter2_bw_nm", "gain_length_m")
TARGETS = ("compressed_energy_nJ", "compressed_duration_fs", "compressed_peak_power_MW")
ATOL = RTOL = 1e-10

GUARD = r'''import json, pathlib, runpy, sys, traceback
counter_path, target = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2])
arguments = sys.argv[3:]
counts = dict(fit_calls=0, calibration_calls=0, oracle_calls=0, fallback_attempts=0,
              model_deserializations=0, class_source_executions=0, predict_calls=0, prediction_rows=0)
def profile(frame, event, arg):
    if event != "call": return
    name, file = frame.f_code.co_name, pathlib.Path(frame.f_code.co_filename)
    forbidden = None
    if name in {"fit", "partial_fit", "fit_transform"}: forbidden = "fit_calls"
    elif name in {"calibrate", "calibrate_intervals", "calibration_reference"}: forbidden = "calibration_calls"
    elif file.name == "oracle.py": forbidden = "oracle_calls"
    if forbidden:
        counts[forbidden] += 1
        raise RuntimeError("Forbidden closeout call: " + forbidden)
    if file.name == "numpy_pickle.py" and name == "load": counts["model_deserializations"] += 1
    if file.name == "models_v4.py" and name == "<module>": counts["class_source_executions"] += 1
    if file.name == "models_v4.py" and name == "predict":
        counts["predict_calls"] += 1
        counts["prediction_rows"] += len(frame.f_locals["x"])
def audit(event, args):
    if event in {"subprocess.Popen", "os.system", "os.posix_spawn", "os.fork"} or event.startswith("socket."):
        counts["fallback_attempts"] += 1
        raise RuntimeError("External process/network fallback forbidden: " + event)
sys.addaudithook(audit)
sys.setprofile(profile)
code = 0
try:
    sys.argv = [str(target), *arguments]
    runpy.run_path(str(target), run_name="__main__")
except SystemExit as exc:
    code = exc.code if isinstance(exc.code, int) else (0 if exc.code is None else 1)
except BaseException:
    traceback.print_exc(); code = 1
finally:
    sys.setprofile(None)
    counts["exit_code"] = code
    counter_path.write_text(json.dumps(counts, indent=2) + "\n")
raise SystemExit(code)
'''


def dump(path, value):
    with path.open("x") as stream:
        json.dump(value, stream, indent=2, allow_nan=False); stream.write("\n")


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rows_json(path):
    value = json.loads(path.read_text())
    return [[row["targets"][key] for key in TARGETS] for row in value["predictions"]]


def compare(got, expected):
    if len(got) != len(expected) or any(len(row) != 3 for row in got):
        raise AssertionError("Prediction row/target dimensions differ")
    errors = [[abs(a - b) for a, b in zip(row, truth)] for row, truth in zip(got, expected)]
    passed = all(math.isfinite(a) and math.isfinite(b) and abs(a - b) <= ATOL + RTOL * abs(b)
                 for row, truth in zip(got, expected) for a, b in zip(row, truth))
    if not passed:
        raise AssertionError("Saved prediction regression exceeded predeclared 1e-10 tolerance")
    return {"passed": passed, "atol": ATOL, "rtol": RTOL, "absolute_errors": errors,
            "maximum_absolute_error": max(x for row in errors for x in row)}


def main():
    demo = OUT / "demo"
    demo.mkdir()  # Exclusive: a failed or completed attempt is never reused.
    started = time.monotonic()
    records, result = [], {"status": "running", "atol": ATOL, "rtol": RTOL,
                           "new_labels": 0, "distinct_saved_designs": 3}
    guard = demo / "guard.py"
    guard.write_text(GUARD)
    env = os.environ.copy()
    env.pop("PYTHONPATH", None)
    for name in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS", "VECLIB_MAXIMUM_THREADS"):
        env[name] = "2"
    env["PYTHONDONTWRITEBYTECODE"] = "1"

    def run(label, command, cwd, expected_code=0, guarded=True, expected_rows=0):
        begin = time.monotonic()
        record = {"label": label, "command": command, "cwd": str(cwd), "expected_exit_code": expected_code,
                  "PYTHONPATH_removed": True, "isolated_python": True, "subprocess_timeout_s": 10}
        records.append(record)
        try:
            completed = subprocess.run(command, cwd=cwd, env=env, text=True, capture_output=True, timeout=10, check=False)
            record.update(exit_code=completed.returncode, elapsed_s=time.monotonic() - begin)
            (demo / (label + ".stdout.log")).write_text(completed.stdout)
            (demo / (label + ".stderr.log")).write_text(completed.stderr)
            if guarded:
                counts = json.loads((demo / (label + ".counts.json")).read_text())
                record["counters"] = counts
                if any(counts[k] for k in ("fit_calls", "calibration_calls", "oracle_calls", "fallback_attempts")):
                    raise AssertionError("Forbidden runtime call detected")
                if counts["prediction_rows"] != expected_rows:
                    raise AssertionError("Unexpected number of prediction rows")
                if expected_rows == 0 and (counts["model_deserializations"] or counts["class_source_executions"]):
                    raise AssertionError("Rejected/verify path loaded a model or custom class")
            if completed.returncode != expected_code:
                raise AssertionError(label + ": unexpected exit code")
        except BaseException as exc:
            record.update(error=f"{type(exc).__name__}: {exc}", elapsed_s=time.monotonic() - begin)
            if isinstance(exc, subprocess.TimeoutExpired):
                for suffix, content in (("stdout", exc.stdout), ("stderr", exc.stderr)):
                    if isinstance(content, bytes):
                        content = content.decode(errors="replace")
                    (demo / (label + "." + suffix + ".log")).write_text(content or "")
                record.update(exit_code=None, timeout=True)
            raise
        finally:
            dump(demo / (label + ".command.json"), record)

    try:
        source_paths = [OLD / "single_input.json", OLD / "single_prediction.json", OLD / "curve/export/results.csv"]
        single = json.loads(source_paths[0].read_text())
        prior_single = json.loads(source_paths[1].read_text())
        if single != prior_single["design"]:
            raise ValueError("Saved single input does not match its recorded prediction")
        with source_paths[2].open(newline="") as stream:
            curve = list(csv.DictReader(stream))[:2]
        designs = [single, *[{k: float(row[k]) for k in FEATURES} for row in curve]]
        truth = [[prior_single["targets"][k] for k in TARGETS], *[[float(row[k]) for k in TARGETS] for row in curve]]
        if len({json.dumps(row, sort_keys=True) for row in designs}) != 3:
            raise ValueError("Expected exactly three distinct previously saved designs")
        dump(demo / "protocol.json", {"atol": ATOL, "rtol": RTOL, "designs": designs,
            "saved_targets": truth, "new_designs": 0, "maximum_actual_prediction_rows": 9,
            "sources": {str(p.relative_to(ROOT)): sha(p) for p in source_paths},
            "guard_sha256": sha(guard), "no_test_rescoring": True})
        with tempfile.TemporaryDirectory(prefix="mamyshev_mvp_external_") as temporary:
            temporary = Path(temporary).resolve()
            if temporary.is_relative_to(ROOT):
                raise ValueError("Independent package check must be outside the repository")
            bundle = temporary / "bundle"; bundle.mkdir()
            with zipfile.ZipFile(OUT / "inference_bundle.zip") as archive:
                if any(Path(name).is_absolute() or ".." in Path(name).parts for name in archive.namelist()):
                    raise ValueError("Archive contains escaping path")
                archive.extractall(bundle)
            external_guard = temporary / "guard.py"
            shutil.copyfile(guard, external_guard)

            def cli(label, directory, arguments, expected_code=0, rows=0):
                run(label, [sys.executable, "-I", str(external_guard), str(demo / (label + ".counts.json")),
                            str(directory / "infer.py"), *arguments], temporary, expected_code, True, rows)

            cli("verify", bundle, ["verify"])
            singles = []
            for i, design in enumerate(designs):
                input_path, output_path = temporary / f"single_{i}.json", temporary / f"single_{i}_prediction.json"
                dump(input_path, design)
                cli(f"single_{i}", bundle, ["predict", "--input", str(input_path), "--output", str(output_path)], rows=1)
                singles.extend(rows_json(output_path))
                shutil.copyfile(output_path, demo / output_path.name)
            batch_input = temporary / "batch.csv"
            with batch_input.open("x", newline="") as stream:
                writer = csv.DictWriter(stream, fieldnames=FEATURES); writer.writeheader(); writer.writerows(designs)
            shutil.copyfile(batch_input, demo / batch_input.name)
            output_json, output_csv = temporary / "batch_prediction.json", temporary / "batch_prediction.csv"
            cli("batch_json", bundle, ["predict", "--input", str(batch_input), "--output", str(output_json)], rows=3)
            cli("batch_csv", bundle, ["predict", "--input", str(batch_input), "--output", str(output_csv)], rows=3)
            batch = rows_json(output_json)
            with output_csv.open(newline="") as stream:
                csv_rows = [[float(row[k]) for k in TARGETS] for row in csv.DictReader(stream)]
            result["comparisons"] = {"single_vs_saved": compare(singles, truth), "batch_vs_saved": compare(batch, truth),
                "single_vs_batch": compare(singles, batch), "csv_vs_json": compare(csv_rows, batch)}
            for path in (output_json, output_csv):
                shutil.copyfile(path, demo / path.name)
            malformed = temporary / "malformed.json"
            dump(malformed, {**single, "unknown": 1})
            cli("malformed", bundle, ["predict", "--input", str(malformed), "--output", str(temporary / "never.json")], 2)
            for label, asset, alter in (("missing_model", "model.joblib", False),
                                        ("missing_class", "models_v4.py", False),
                                        ("tampered_class", "models_v4.py", True)):
                broken = temporary / label; shutil.copytree(bundle, broken)
                if alter:
                    with (broken / asset).open("a") as stream:
                        stream.write("\nraise RuntimeError('tampered source must never execute')\n")
                else:
                    (broken / asset).unlink()
                cli(label, broken, ["predict", "--input", str(temporary / "single_0.json"),
                                   "--output", str(temporary / (label + "_never.json"))], 2)
            test_script = temporary / "component_tests.py"
            test_script.write_text("import sys, unittest\n"
                + f"sys.path[:0] = {[str(ROOT / 'src'), str(ROOT / 'tests')]!r}\n"
                + "names = ['test_closeout_inference', 'test_v4_live_supervisor.LiveAuthorization.test_default_denial_and_zero_allowance_do_not_reserve']\n"
                + "suite = unittest.defaultTestLoader.loadTestsFromNames(names)\n"
                + "assert suite.countTestCases() == 8\n"
                + "result = unittest.TextTestRunner(verbosity=2).run(suite)\n"
                + "raise SystemExit(0 if result.wasSuccessful() else 1)\n")
            run("components", [sys.executable, "-I", str(test_script)], temporary, guarded=False)
        result.update(status="passed", temporary_directory_removed=True, component_test_methods=8,
                      new_component_methods=7, reused_component_methods=1, actual_prediction_rows=9,
                      independent_environment="existing environment outside repository; not a fresh environment")
    except BaseException as exc:
        result.update(status="failed", error=f"{type(exc).__name__}: {exc}")
        raise
    finally:
        result.update(elapsed_s=time.monotonic() - started, commands=records)
        dump(demo / "result.json", result)


if __name__ == "__main__":
    main()
