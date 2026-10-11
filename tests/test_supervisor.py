"""Actual short child processes and pure final merge fixtures; never MATLAB."""
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from mamyshev_ml import supervisor as s


def expected():
    return {"run_id": "component_001", "mode": "synthetic", "source_identity": {"digest": "fixture", "files": []}}


def candidate():
    value = s._blank(expected())
    value.update(job_status="completed", stop_reason="synthetic_component_return", completed_roundtrips=2,
                 failure_reason=None, observability={"kind": "synthetic_component", "required_records_complete": True})
    value["outputs"]["sf1_rejected_raw"]["energy"].update(value=12.3, missing_reason="")
    value["references"]["transform_limited_fwhm"].update(value=10., missing_reason="")
    return value


def process(exit_code=0, **updates):
    result = {"status": "completed" if exit_code == 0 else "failed", "exit_code": exit_code,
              "stop_reason": "process_exit", "stop_events": [], "elapsed_s": 0.1}
    result.update(updates)
    return result


class MergeTest(unittest.TestCase):
    def assert_safe_failure(self, result):
        self.assertNotEqual(result["job_status"], "completed")
        self.assertEqual(result["physical_state"], "undetermined")
        self.assertFalse(result["eligible_as_validated_training_truth"])
        for plane in result["outputs"].values():
            for name in ("energy", "peak_power", "fwhm"):
                self.assertIsNone(plane[name]["value"])
                self.assertTrue(plane[name]["missing_reason"])
        self.assertIsNone(result["references"]["transform_limited_fwhm"]["value"])
        self.assertIsNone(result["outputs"]["compressed_analysis"]["field"]["value"])
        self.assertTrue(result["outputs"]["compressed_analysis"]["field"]["missing_reason"])

    def test_normal_completed_candidate(self):
        result = s.merge_result(candidate(), process(), expected())
        self.assertEqual(result["job_status"], "completed")
        self.assertEqual(result["outputs"]["sf1_rejected_raw"]["energy"]["value"], 12.3)

    def test_nonzero_preserves_specific_candidate_error(self):
        c = candidate()
        c.update(job_status="failed", stop_reason="numerical_error", failure_reason={"identifier": "NonFinite", "message": "fixture"})
        result = s.merge_result(c, process(7), expected())
        self.assert_safe_failure(result)
        self.assertEqual(result["stop_reason"], "numerical_error")
        self.assertEqual(result["supervisor"]["exit_code"], 7)

    def test_nonzero_completed_and_zero_failed_are_inconsistent(self):
        for code, status in ((7, "completed"), (0, "failed")):
            with self.subTest(code=code):
                c = candidate(); c["job_status"] = status
                result = s.merge_result(c, process(code), expected())
                self.assert_safe_failure(result)
                self.assertTrue(result["supervisor"]["exit_candidate_inconsistent"])

    def test_first_observed_stop_wins_both_orders(self):
        for first, second in (("timeout", "cancelled"), ("cancelled", "timeout")):
            with self.subTest(first=first):
                events = [{"reason": first, "elapsed_s": 1}, {"reason": second, "elapsed_s": 2}]
                result = s.merge_result(candidate(), process(stop_events=events), expected())
                self.assertEqual(result["job_status"], first)
                self.assertEqual(result["supervisor"]["stop_events"], events)
                self.assert_safe_failure(result)

    def test_missing_protocol_and_identity_variants_fail_closed(self):
        variants = [None, {}, {**candidate(), "result_protocol_version": "bad"}]
        for field in ("run_id", "source_identity", "source_kind", "numerical_version"):
            c = candidate(); c["provenance"][field] = "mismatch"; variants.append(c)
        for c in variants:
            with self.subTest(candidate=c):
                self.assert_safe_failure(s.merge_result(c, process(), expected()))

    def test_incomplete_required_records_fail(self):
        c = candidate(); c["observability"]["required_records_complete"] = False
        reason = s.required_records_error(c, expected(), Path("."))
        result = s.merge_result(c, process(), expected(), records_error=reason)
        self.assert_safe_failure(result)
        self.assertEqual(result["stop_reason"], "incomplete_required_records")

    def test_malformed_nested_values_fail_closed(self):
        variants = []
        for key in ("provenance", "numerical_validation", "outputs", "references", "job_status"):
            for value in (None, [], 3):
                c = candidate(); c[key] = value; variants.append(c)
        for count in (True, -1, 0.5, float("inf"), float("nan"), 10**1000):
            c = candidate(); c["completed_roundtrips"] = count; variants.append(c)
        c = candidate(); del c["stop_reason"]; variants.append(c)
        c = candidate(); c["outputs"]["sf1_rejected_raw"] = None; variants.append(c)
        c = candidate(); c["references"]["transform_limited_fwhm"] = {}; variants.append(c)
        c = candidate(); c["outputs"]["sf1_rejected_raw"]["energy"]["value"] = float("inf"); variants.append(c)
        c = candidate(); del c["outputs"]["compressed_analysis"]["field"]; variants.append(c)
        for c in variants:
            with self.subTest(candidate=c):
                self.assert_safe_failure(s.merge_result(c, process(), expected()))

    def test_actual_record_gate_checks_content_counts_and_identity(self):
        baseline_dir = s.ROOT / "reports/local/phase1/baseline_001"
        if not (baseline_dir / "configuration.mat").is_file():
            self.skipTest("Direct Phase1 configuration is local evidence, not public test data")
        config = s.load_json(baseline_dir / "configuration.json")
        identity = {"run_id": expected()["run_id"], "source_identity": expected()["source_identity"]}
        records = {key: deepcopy(identity) for key in ("requested", "configuration", "configuration_comparison", "runtime_calls", "runtime_observer")}
        records["configuration"].update(status="observed", propagation_started=False, configuration=config,
            gain_info_computed_N_total=89814125.93190747, final_N_total=config["N_total_ions_per_um3"])
        for key, shape in (("initial_field", [config["Nt"], 1]), ("time_grid", [1, config["Nt"]]),
                           ("frequency_grid", [config["Nt"], 1]), ("wavelength_grid", [config["Nt"], 1])):
            records["configuration"][key] = {"size": shape, "finite": True, "class": "double"}
        records["configuration_comparison"].update(passed=True, checked_leaves=5, unexpected_differences=[])
        calls, segments = [], []
        for index, name in enumerate(("cavity_1", "cavity_2", "cavity_3", "cavity_4", "pigtail")):
            fiber = deepcopy(config["fiber_cavity"][index if index<4 else 1])
            if name == "pigtail": fiber["L0"] = config["output_fiber_length_m"]
            calls.append({"roundtrip": 1, "segment_id": name, "status": "observed", "fiber": fiber,
                "sim": config["sim_cavity"][index if index<4 else 1], "dt_ps": config["dt_ps"],
                "input_field_size": [config["Nt"], 1], "gain_arrays_match_reference": True,
                "gain_rate_eqn": config["gain_rate_eqn"]})
            segments.append({"round_trip": 1, "segment_id": name, "normal_completion": True,
                "counts_complete": True, "trials": 4, "rejections": 1, "accepted_advanced_steps": 3,
                "pending_trials": 0, "runtime_resolutions": [{"status": "observed", "max_deltaZ": .01,
                    "initial_deltaZ": .001, "threshold": 1e-6}]})
        records["runtime_calls"].update(backend_returned=True, compressor_status="observed", segment_calls=calls,
            compressor_call={"status": "observed", "type": config["compressor_type"],
                "incident_angle_rad": config["grating_incident_angle_rad"],
                "grating_spacing_m": config["grating_spacing_m"], "plot_on": config["plot_on"]})
        records["runtime_observer"].update(counts_complete=True, runtime_resolved_complete=True,
                                          active_segment=None, segments=segments)
        c = candidate(); c["completed_roundtrips"] = 1
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            # A read-only copy is fixture evidence, never a new physical run.
            (folder / "configuration.mat").write_bytes((baseline_dir / "configuration.mat").read_bytes())
            def save(values):
                for key, value in values.items():
                    (folder / (key + ".json")).write_text(json.dumps(value))
                c["observability"]["artifact_integrity"] = [{"path": p.name, "bytes": len(p.read_bytes()),
                    "sha256": hashlib.sha256(p.read_bytes()).hexdigest()} for p in sorted(folder.iterdir())]
            save(records)
            self.assertIsNone(s.verify_real_observability(c, expected(), folder))
            variants = []
            bad = deepcopy(records); bad["configuration_comparison"]["passed"] = False; variants.append(bad)
            bad = deepcopy(records); bad["runtime_observer"]["segments"][0]["trials"] += 1; variants.append(bad)
            bad = deepcopy(records); bad["runtime_observer"]["segments"][0]["trials"] = None; variants.append(bad)
            bad = deepcopy(records); bad["runtime_observer"]["segments"][0]["runtime_resolutions"] = []; variants.append(bad)
            bad = deepcopy(records); bad["runtime_calls"]["segment_calls"] = []; variants.append(bad)
            bad = deepcopy(records); bad["requested"]["run_id"] = "wrong"; variants.append(bad)
            bad = deepcopy(records); del bad["configuration"]["configuration"]; variants.append(bad)
            bad = deepcopy(records); del bad["runtime_calls"]["compressor_call"]; variants.append(bad)
            bad = deepcopy(records); del bad["runtime_calls"]["segment_calls"][0]["fiber"]; variants.append(bad)
            bad = deepcopy(records); bad["runtime_calls"]["segment_calls"][0]["fiber"]["MFD"] += .01; variants.append(bad)
            for bad in variants:
                save(bad); self.assertIsNotNone(s.verify_real_observability(c, expected(), folder))
            save(records); (folder / "configuration.mat").write_text("corrupt fixture")
            self.assertIsNotNone(s.verify_real_observability(c, expected(), folder))
            save(records)  # Even a matching hash cannot substitute a real MAT header.
            self.assertIsNotNone(s.verify_real_observability(c, expected(), folder))
            (folder / "configuration.json").unlink()
            self.assertIsNotNone(s.verify_real_observability(c, expected(), folder))

    def test_atomic_final_refuses_existing_even_corrupt(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "final_result.json"; path.write_bytes(b"previous evidence")
            with self.assertRaises(FileExistsError): s.atomic_json(path, candidate())
            self.assertEqual(path.read_bytes(), b"previous evidence")

    def test_nonstandard_json_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "candidate.json"
            for payload in ('{"value":NaN}', '{"value":1e999}'):
                path.write_text(payload)
                with self.assertRaises(ValueError): s.load_json(path)


class ProcessTest(unittest.TestCase):
    def run_child(self, directory, command, timeout=10):
        with patch.object(s, "source_identity", return_value=expected()["source_identity"]):
            return s.execute_once(command, Path(directory), expected(), timeout)

    def command(self, c=None, exit_code=0, wait=False):
        text = "" if c is None else "printf '%s' " + shlex.quote(json.dumps(c)) + " > matlab_candidate.json; "
        text += "trap 'exit 0' TERM; while :; do sleep 1; done" if wait else "exit " + str(exit_code)
        return ["/bin/sh", "-c", text]

    def test_real_short_child_writes_parent_final(self):
        with tempfile.TemporaryDirectory() as directory:
            result = self.run_child(directory, self.command(candidate()))
            self.assertEqual(result["job_status"], "completed")
            self.assertEqual(s.load_json(Path(directory) / "final_result.json"), result)
            self.assertEqual(s.load_json(Path(directory) / "runner_record.json")["exit_code"], 0)

    def test_real_child_missing_corrupt_and_mismatch(self):
        mismatched = candidate(); mismatched["provenance"]["run_id"] = "wrong"
        commands = [self.command(), ["/bin/sh", "-c", "printf corrupt > matlab_candidate.json"], self.command(mismatched)]
        for cmd in commands:
            with self.subTest(command=cmd), tempfile.TemporaryDirectory() as directory:
                self.assertNotEqual(self.run_child(directory, cmd)["job_status"], "completed")

    def test_real_child_timeout_zero_exit_cannot_override(self):
        with tempfile.TemporaryDirectory() as directory:
            result = self.run_child(directory, self.command(candidate(), wait=True), 7.3)
            self.assertEqual(result["job_status"], "timeout")
            self.assertEqual(result["supervisor"]["exit_code"], 0)
            self.assertIsNone(result["outputs"]["sf1_rejected_raw"]["energy"]["value"])

    def test_real_child_STOP_success_cannot_override(self):
        with tempfile.TemporaryDirectory() as directory:
            cmd = self.command(candidate(), wait=True)
            cmd[2] = cmd[2].replace("trap ", "touch STOP; trap ")
            result = self.run_child(directory, cmd)
            self.assertEqual(result["job_status"], "cancelled")

    def test_final_write_failure_propagates_without_completed_final(self):
        real_write = s.atomic_json
        def fail_final(path, value, **options):
            if Path(path).name == "final_result.json": raise OSError("synthetic disk full")
            return real_write(path, value, **options)
        with tempfile.TemporaryDirectory() as directory, patch.object(s, "atomic_json", side_effect=fail_final):
            with self.assertRaises(OSError): self.run_child(directory, self.command(candidate()))
            folder = Path(directory)
            self.assertFalse((folder / "final_result.json").exists())
            self.assertEqual(s.load_json(folder / "supervisor_error.json")["status"], "failed")
            self.assertIsNotNone(s.load_json(folder / "runner_record.json")["exit_code"])

    def test_runner_write_failure_cleans_owned_group_not_control(self):
        control = subprocess.Popen(["/bin/sleep", "30"], start_new_session=True)
        real_popen = subprocess.Popen; children = []
        def capture(*args, **kwargs):
            value = real_popen(*args, **kwargs); children.append(value); return value
        try:
            with tempfile.TemporaryDirectory() as directory, \
                    patch.object(s.monitor.subprocess, "Popen", side_effect=capture), \
                    patch.object(Path, "write_text", side_effect=OSError("synthetic runner write failure")):
                with self.assertRaises(OSError): self.run_child(directory, ["/bin/sleep", "30"])
                self.assertEqual(len(children), 1)
                self.assertIsNotNone(children[0].poll())
                self.assertIsNone(control.poll())
        finally:
            s.monitor.stop_owned(control)

    def test_final_write_failure_also_cleans_forked_descendant(self):
        real_write = s.atomic_json
        def fail_final(path, value, **options):
            if Path(path).name == "final_result.json": raise OSError("synthetic commit failure")
            return real_write(path, value, **options)
        with tempfile.TemporaryDirectory() as directory:
            command = self.command(candidate())
            command[2] = "sleep 30 & child=$!; printf '%s' \"$child\" > child.pid; " + command[2]
            with patch.object(s, "atomic_json", side_effect=fail_final):
                with self.assertRaises(OSError): self.run_child(directory, command)
            child = int((Path(directory) / "child.pid").read_text())
            # A zombie is no longer running; reaping belongs to its new parent.
            state = subprocess.run(["/bin/ps", "-o", "stat=", "-p", str(child)], capture_output=True, text=True).stdout.strip()
            self.assertTrue(not state or state.startswith("Z"), state)
            self.assertFalse((Path(directory) / "final_result.json").exists())


if __name__ == "__main__":
    unittest.main()
