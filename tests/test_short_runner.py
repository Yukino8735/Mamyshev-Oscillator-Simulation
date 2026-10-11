"""Budget and process ownership tests; no MATLAB or propagation."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location("short_runner", Path(__file__).with_name("run_matlab_short.py"))
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)


class ShortRunnerTest(unittest.TestCase):
    def test_new_batch_has_distinct_budget_and_evidence_directory(self):
        repair = runner.batch_directory("repair_001")
        readiness = runner.batch_directory("readiness_001")
        self.assertNotEqual(repair, readiness)
        self.assertEqual(runner.remaining_budget([]), 600)
        self.assertEqual(runner.DEFAULT_BATCH, "repair_001")
        with self.assertRaises(ValueError):
            runner.batch_directory("../repair_001")

    def test_retries_and_failures_consume_budget(self):
        records = [{"status": "failed", "elapsed_s": 180},
                   {"status": "completed", "elapsed_s": 25}]
        self.assertEqual(runner.remaining_budget(records), 395)
        with self.assertRaises(RuntimeError):
            runner.remaining_budget([{"status": "running", "elapsed_s": 0}])

    def test_external_reconciliation_only_debits_failed_full_cap(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory) / "attempt"; folder.mkdir()
            original = json.dumps({"status": "running", "elapsed_s": 0})
            (folder / "runner_record.json").write_text(original)
            with self.assertRaises(RuntimeError): runner.remaining_budget(runner.budget_records(Path(directory)))
            audit = {"status": "failed", "cleanup_verified": True, "elapsed_s": 180}
            (folder / "runner_reconciliation.json").write_text(json.dumps(audit))
            self.assertEqual(runner.remaining_budget(runner.budget_records(Path(directory))), 420)
            self.assertEqual((folder / "runner_record.json").read_text(), original)
            audit["status"] = "completed"
            (folder / "runner_reconciliation.json").write_text(json.dumps(audit))
            with self.assertRaises(RuntimeError): runner.budget_records(Path(directory))

    def test_only_owned_process_group_terminated(self):
        control = subprocess.Popen(["/bin/sleep", "30"], start_new_session=True)
        try:
            with tempfile.TemporaryDirectory() as directory:
                # An existing STOP requests cancellation before any timeout.
                folder = Path(directory)
                (folder / "STOP").touch()
                record = runner.run_isolated(["/bin/sleep", "30"], folder, os.environ.copy(), 10)
                self.assertEqual(record["stop_reason"], "cancelled")
                self.assertIsNone(control.poll())
                self.assertLess(record["elapsed_s"], 10)
        finally:
            runner.stop_owned(control)

    def test_nonzero_exit_is_preserved(self):
        with tempfile.TemporaryDirectory() as directory:
            record = runner.run_isolated(["/bin/sh", "-c", "exit 7"], Path(directory), os.environ.copy(), 10)
        self.assertEqual(record["exit_code"], 7)
        self.assertEqual(record["status"], "failed")

    def test_timeout_terminates_owned_group(self):
        with tempfile.TemporaryDirectory() as directory:
            record = runner.run_isolated(["/bin/sleep", "30"], Path(directory), os.environ.copy(), 7.3)
        self.assertEqual(record["stop_reason"], "timeout")
        self.assertLess(record["elapsed_s"], 7.3)

    def test_timeout_overrides_graceful_zero_exit_and_success_candidate(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            candidate = folder / "matlab_candidate.json"
            original = json.dumps({"job_status": "completed", "source_kind": "synthetic_process_fixture"})
            candidate.write_text(original)
            command = ["/bin/sh", "-c", "trap 'exit 0' TERM; while :; do sleep 1; done"]
            record = runner.run_isolated(command, folder, os.environ.copy(), 7.3)
            self.assertEqual(record["exit_code"], 0)
            self.assertEqual(record["stop_reason"], "timeout")
            self.assertEqual(record["status"], "failed")
            self.assertEqual(candidate.read_text(), original)
            self.assertEqual(json.loads((folder / "runner_record.json").read_text())["status"], "failed")

    def test_record_write_failure_still_cleans_up_process(self):
        original_popen = subprocess.Popen
        created = []
        def capture(*args, **kwargs):
            process = original_popen(*args, **kwargs)
            created.append(process)
            return process
        with tempfile.TemporaryDirectory() as directory:
            with patch.object(runner.subprocess, "Popen", side_effect=capture), \
                 patch.object(Path, "write_text", side_effect=OSError("fixture disk failure")):
                with self.assertRaises(OSError):
                    runner.run_isolated(["/bin/sleep", "30"], Path(directory), os.environ.copy(), 10)
        self.assertEqual(len(created), 1)
        self.assertIsNotNone(created[0].poll())

    def test_permission_error_accepted_only_for_confirmed_absent_group(self):
        exited = subprocess.Popen(["/bin/sh", "-c", "exit 0"], start_new_session=True)
        exited.wait()
        with patch.object(runner.os, "killpg", side_effect=PermissionError("synthetic EPERM")):
            runner.stop_owned(exited)  # Successful process-table check confirms absence.
        live = subprocess.Popen(["/bin/sleep", "30"], start_new_session=True)
        try:
            with patch.object(runner.os, "killpg", side_effect=PermissionError("synthetic EPERM")):
                with self.assertRaises(PermissionError): runner.stop_owned(live)
            self.assertIsNone(live.poll())
        finally:
            runner.stop_owned(live)


if __name__ == "__main__":
    unittest.main()
