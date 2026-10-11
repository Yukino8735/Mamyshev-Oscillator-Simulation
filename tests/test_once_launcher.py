"""Python-only launcher wiring fixtures; no MATLAB or physical child is started."""
from contextlib import redirect_stderr, redirect_stdout
import importlib.util
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location(
    "mamyshev_once_launcher_under_test", ROOT / "scripts/run_mamyshev_once.py")
launcher = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(launcher)
s = launcher.supervisor


def fixture_identity(run_id, mode):
    return {"run_id": run_id, "mode": mode, "seed": 0,
            "requested": {"PumpPower": 4, "cw2": 1030, "plot_on": False},
            "source_identity": {"digest": "python_wiring_fixture", "files": []}}


class OnceLauncherTest(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.matlab = self.root / "MATLAB/bin/matlab"
        self.script = self.root / "code/ml_bridge/launch_mamyshev_once.m"
        self.component = self.root / "tests/matlab/run_launchprep_candidate.m"
        for path in (self.matlab, self.script, self.component):
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("Python path fixture only; must never be executed.\n")
        self.root_patch = patch.object(launcher, "ROOT", self.root)
        self.root_patch.start()
        self.addCleanup(self.root_patch.stop)

    def argv(self, action="--dry-run", run_id="validation_001", extra=()):
        return ["run_mamyshev_once.py", action, "--run-id", run_id,
                "--matlab", str(self.matlab), *extra]

    def invoke(self, argv):
        output = io.StringIO()
        with patch.object(sys, "argv", argv), redirect_stdout(output):
            launcher.main()
        return json.loads(output.getvalue())

    def extended(self, action="--dry-run"):
        return self.argv(action, "validation_002", (
            "--batch-id", "single_validation_002", "--timeout-s", "1800"))

    def configured(self, action="--dry-run", design=None):
        config = self.root / "design.json"
        config.write_text(json.dumps(s.DEFAULT_DESIGN_CONFIG if design is None else design))
        return self.argv(action, "config_waveform_001", (
            "--batch-id", "config_waveform_validation_001", "--timeout-s", "1800",
            "--design-config", str(config), "--save-waveforms"))

    def observation(self, action="--dry-run"):
        argv = self.configured(action)
        argv[argv.index("--run-id")+1] = "observation_001"
        argv[argv.index("--batch-id")+1] = "observation_validation_001"
        argv[argv.index("--timeout-s")+1] = "3600"
        return argv + ["--observation-mode", "fixed_roundtrips", "--observation-roundtrips", "20"]

    def assert_dry_run(self, value, batch, run_id, timeout):
        folder = self.root / "reports/local/phase2" / batch / run_id
        self.assertEqual(value["mode"], "dry_run")
        self.assertEqual(value["backend_mode"], "real")
        self.assertEqual(value["batch_id"], batch)
        self.assertEqual(value["run_id"], run_id)
        self.assertEqual(value["future_directory"], str(folder))
        self.assertEqual(value["timeout_s"], timeout)
        self.assertEqual(value["shutdown_and_finalization_reserve_s"], 30)
        self.assertEqual(value["max_attempts"], 1)
        self.assertEqual(value["STOP"], str(folder / "STOP"))
        self.assertEqual(value["requested"], {"PumpPower": 4, "cw2": 1030, "plot_on": False})
        self.assertEqual(value["seed"], 0)
        self.assertEqual(value["rng_algorithm"], "twister")
        self.assertIs(value["propagation_started"], False)
        self.assertEqual(value["full_cavity_attempts"], 0)
        self.assertEqual(value["future_command"][0], str(self.matlab.resolve()))
        self.assertEqual(value["future_command"][1], "-batch")
        self.assertIn("launch_mamyshev_once", value["future_command"][2])
        self.assertFalse((self.root / "reports").exists())

    def test_default_dry_run_keeps_old_budget_without_reservation(self):
        with patch.object(s, "execute_once") as execute:
            value = self.invoke(self.argv())
        execute.assert_not_called()
        self.assert_dry_run(value, "single_validation_001", "validation_001", 900)

    def test_extended_dry_run_uses_explicit_budget_without_reservation(self):
        with patch.object(s, "execute_once") as execute:
            value = self.invoke(self.extended())
        execute.assert_not_called()
        self.assert_dry_run(value, "single_validation_002", "validation_002", 1800)

    def test_extended_execute_passes_budget_and_request_identity(self):
        with patch.object(s, "request_identity", side_effect=fixture_identity) as identity, \
                patch.object(s, "execute_once", return_value={"job_status": "completed"}) as execute:
            value = self.invoke(self.extended("--execute-real"))
        identity.assert_called_once_with("validation_002", "real")
        execute.assert_called_once()
        command, folder, expected, timeout = execute.call_args.args
        self.assertEqual(timeout, 1800)
        self.assertEqual(folder, self.root / "reports/local/phase2/single_validation_002/validation_002")
        self.assertTrue(folder.is_dir())
        self.assertEqual(command[0], str(self.matlab.resolve()))
        self.assertIn("launch_mamyshev_once", command[2])
        self.assertEqual(expected["mode"], "real")
        self.assertEqual(expected["batch_id"], "single_validation_002")
        self.assertEqual(expected["total_wall_limit_s"], 1800)
        self.assertEqual(expected["shutdown_and_finalization_reserve_s"], 30)
        self.assertEqual(expected["source_identity"], fixture_identity("validation_002", "real")["source_identity"])
        self.assertEqual(value["run_id"], "validation_002")
        self.assertFalse((folder.parent.parent / "single_validation_001").exists())

    def test_config_dry_run_has_request_and_no_reservation(self):
        with patch.object(s, "execute_once") as execute:
            value = self.invoke(self.configured())
        execute.assert_not_called()
        self.assert_dry_run(value, "config_waveform_validation_001", "config_waveform_001", 1800)
        self.assertEqual(value["design_config"], s.DEFAULT_DESIGN_CONFIG)
        self.assertIs(value["save_waveforms"], True)

    def test_config_execute_preserves_once_limit_and_frozen_design(self):
        with patch.object(s, "request_identity", side_effect=fixture_identity), \
                patch.object(s, "execute_once", return_value={"job_status": "completed"}) as execute:
            self.invoke(self.configured("--execute-real"))
            with self.assertRaisesRegex(SystemExit, "already reserved"):
                self.invoke(self.configured("--execute-real"))
        execute.assert_called_once()
        _, folder, expected, timeout = execute.call_args.args
        self.assertEqual(folder.name, "config_waveform_001")
        self.assertEqual(timeout, 1800)
        self.assertEqual(expected["design_config"], s.DEFAULT_DESIGN_CONFIG)
        self.assertTrue(expected["save_waveforms"])
        self.assertEqual(expected["shutdown_and_finalization_reserve_s"], 30)

    def test_config_rejects_other_designs_invalid_values_and_legacy_flags(self):
        variants = [dict(s.DEFAULT_DESIGN_CONFIG, pump_power_W=4.1),
                    dict(s.DEFAULT_DESIGN_CONFIG, pump_power_W=True),
                    dict(s.DEFAULT_DESIGN_CONFIG, gain_length_m=4.15),
                    dict(s.DEFAULT_DESIGN_CONFIG, cw2=1030)]
        with patch.object(s, "execute_once") as execute:
            for design in variants:
                with self.subTest(design=design), redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                    self.invoke(self.configured("--execute-real", design))
            good = self.configured()
            missing_save = [arg for arg in good if arg != "--save-waveforms"]
            legacy = self.argv(extra=("--save-waveforms",))
            for argv in (missing_save, legacy):
                with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                    self.invoke(argv)
        execute.assert_not_called()
        self.assertFalse((self.root / "reports").exists())

    def test_observation_dry_run_is_explicit_default_design_20_rounds_3600_seconds(self):
        with patch.object(s, "execute_once") as execute:
            value = self.invoke(self.observation())
        execute.assert_not_called()
        self.assert_dry_run(value, "observation_validation_001", "observation_001", 3600)
        self.assertEqual(value["design_config"], s.DEFAULT_DESIGN_CONFIG)
        self.assertTrue(value["save_waveforms"])
        self.assertEqual(value["observation_options"], {"observation_mode": "fixed_roundtrips", "observation_roundtrips": 20})
        self.assertTrue(value["reserve_included_in_timeout"])

    def test_observation_execute_passes_options_and_failure_consumes_only_attempt(self):
        with patch.object(s, "request_identity", side_effect=fixture_identity), \
                patch.object(s, "execute_once", return_value={"job_status": "failed"}) as execute:
            with self.assertRaises(SystemExit) as failed:
                self.invoke(self.observation("--execute-real"))
            self.assertEqual(failed.exception.code, 1)
            with self.assertRaisesRegex(SystemExit, "already reserved"):
                self.invoke(self.observation("--execute-real"))
        execute.assert_called_once()
        _, folder, expected, timeout = execute.call_args.args
        self.assertEqual(folder.name, "observation_001")
        self.assertEqual(timeout, 3600)
        self.assertEqual(expected["observation_options"], {"observation_mode": "fixed_roundtrips", "observation_roundtrips": 20})
        self.assertEqual(expected["design_config"], s.DEFAULT_DESIGN_CONFIG)
        self.assertEqual(expected["shutdown_and_finalization_reserve_s"], 30)

    def test_observation_invalid_options_do_not_reserve_and_legacy_options_rejected(self):
        template = self.observation("--execute-real")
        variants = []
        for key, value in (("--observation-roundtrips", "19"), ("--observation-roundtrips", "21"),
                           ("--observation-roundtrips", "0"), ("--observation-roundtrips", "20.0"),
                           ("--observation-mode", "legacy"), ("--timeout-s", "1800"),
                           ("--run-id", "observation_002")):
            changed = template.copy(); changed[changed.index(key)+1] = value; variants.append(changed)
        for key in ("--observation-mode", "--observation-roundtrips"):
            changed = template.copy(); index = changed.index(key); del changed[index:index+2]; variants.append(changed)
        variants.extend([self.argv(extra=("--observation-mode", "fixed_roundtrips", "--observation-roundtrips", "20")),
                         self.configured()+["--observation-mode", "fixed_roundtrips", "--observation-roundtrips", "20"],
                         self.extended()+["--timeout-s", "3600"]])
        with patch.object(s, "execute_once") as execute:
            for argv in variants:
                with self.subTest(argv=argv), redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as error:
                    self.invoke(argv)
                self.assertEqual(error.exception.code, 2)
        execute.assert_not_called()
        self.assertFalse((self.root / "reports").exists())

    def test_invalid_budget_batch_and_run_combinations_reserve_nothing(self):
        variants = [
            ("validation_001", ("--timeout-s", "1800")),
            ("validation_002", ("--batch-id", "single_validation_002")),
            ("validation_001", ("--batch-id", "single_validation_002", "--timeout-s", "1800")),
            ("validation_002", ("--batch-id", "single_validation_002", "--timeout-s", "900")),
            ("validation_002", ("--batch-id", "single_validation_001", "--timeout-s", "1800")),
            ("validation_002", ("--batch-id", "single_validation_003", "--timeout-s", "1800")),
        ]
        variants += [("validation_002", ("--batch-id", "single_validation_002", "--timeout-s", value))
                     for value in ("-1", "0", "1801", "nan", "inf")]
        with patch.object(s, "execute_once") as execute:
            for run_id, extra in variants:
                with self.subTest(run_id=run_id, extra=extra), redirect_stderr(io.StringIO()):
                    with self.assertRaises(SystemExit) as stopped:
                        self.invoke(self.argv("--execute-real", run_id, extra))
                    self.assertEqual(stopped.exception.code, 2)
        execute.assert_not_called()
        self.assertFalse((self.root / "reports").exists())

    def test_component_mode_rejects_explicit_real_budget_or_batch(self):
        variants = [("--batch-id", "single_validation_001"), ("--timeout-s", "900"),
                    ("--batch-id", "single_validation_002", "--timeout-s", "1800")]
        with patch.object(s, "execute_once") as execute:
            for extra in variants:
                argv = ["run_mamyshev_once.py", "--component-script", str(self.component),
                        "--run-id", "fixture", "--matlab", str(self.matlab), *extra]
                with self.subTest(extra=extra), redirect_stderr(io.StringIO()):
                    with self.assertRaises(SystemExit) as stopped:
                        self.invoke(argv)
                    self.assertEqual(stopped.exception.code, 2)
        execute.assert_not_called()
        self.assertFalse((self.root / "reports").exists())

    def test_any_existing_reservation_blocks_without_overwriting_evidence(self):
        batch = self.root / "reports/local/phase2/single_validation_002"
        previous = batch / "reserved_before_runner_write"
        previous.mkdir(parents=True)
        evidence = previous / "evidence.txt"
        evidence.write_bytes(b"preserve this prior reservation")
        with patch.object(s, "execute_once") as execute:
            with self.assertRaisesRegex(SystemExit, "already reserved"):
                self.invoke(self.extended("--execute-real"))
        execute.assert_not_called()
        self.assertEqual(evidence.read_bytes(), b"preserve this prior reservation")
        self.assertFalse((batch / "validation_002").exists())

    def test_execute_failure_consumes_reservation_and_next_call_is_refused(self):
        with patch.object(s, "request_identity", side_effect=fixture_identity), \
                patch.object(s, "execute_once", side_effect=OSError("Python fixture launch failure")) as execute:
            with self.assertRaisesRegex(OSError, "fixture launch failure"):
                self.invoke(self.extended("--execute-real"))
            with self.assertRaisesRegex(SystemExit, "already reserved"):
                self.invoke(self.extended("--execute-real"))
        execute.assert_called_once()
        self.assertTrue((self.root / "reports/local/phase2/single_validation_002/validation_002").is_dir())


class RealBudgetWiringTest(unittest.TestCase):
    def test_supervisor_passes_total_budget_minus_startup_and_30_second_reserve(self):
        expected = fixture_identity("validation_002", "real")
        expected.update(batch_id="single_validation_002", total_wall_limit_s=1800,
                        shutdown_and_finalization_reserve_s=30)
        runner = {"status": "completed", "exit_code": 0, "stop_reason": "process_exit",
                  "stop_events": [], "elapsed_s": 0.1}
        with tempfile.TemporaryDirectory() as directory, \
                patch.object(s.monitor, "run_isolated", return_value=runner) as monitor, \
                patch.object(s, "source_identity", return_value=expected["source_identity"]), \
                patch.object(s.time, "monotonic", side_effect=[100., 100.25, 100.5]):
            folder = Path(directory)
            result = s.execute_once(["never-executed-python-fixture"], folder, expected, 1800)
            self.assertEqual(s.load_json(folder / "launch_request.json"), expected)
            self.assertEqual(s.load_json(folder / "final_result.json"), result)
        monitor.assert_called_once()
        self.assertEqual(monitor.call_args.args[3], 1799.75)
        self.assertEqual(monitor.call_args.kwargs["shutdown_reserve_s"], 30)
        self.assertEqual(monitor.call_args.kwargs["metadata"]["max_attempts"], 1)
        self.assertEqual(result["supervisor"]["total_wall_limit_s"], 1800)
        self.assertEqual(result["supervisor"]["shutdown_and_finalization_reserve_s"], 30)
        self.assertEqual(result["supervisor"]["precommit_elapsed_s"], 0.5)
        # There was deliberately no MATLAB candidate; mock process exit is not success.
        self.assertEqual(result["job_status"], "failed")
        self.assertEqual(result["stop_reason"], "invalid_candidate")


if __name__ == "__main__":
    unittest.main()
