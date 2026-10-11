"""V4 targeted authorization/cleanup components; never starts MATLAB."""
from copy import deepcopy
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from mamyshev_ml import supervisor as s


def plan_auth():
    design = {**s.DEFAULT_DESIGN_CONFIG, "gain_length_m": 4.1}
    plan = {"designs": [{"design_id": "d_one", "design_config": design}], "method": "component_fixture"}
    plan["plan_hash"] = s.canonical_hash(plan)
    auth = {"authorization_id": "v4_component_only", "plan_hash": plan["plan_hash"],
            "allowed_design_ids": ["d_one"], "max_new_attempts": 1,
            "per_run_timeout_s": 90, "total_wall_limit_s": 180}
    return plan, auth


def identity():
    return {"mode": "synthetic", "run_id": "v4_child", "source_identity": {"kind": "component_fixture"}}


def candidate():
    result = s._blank(identity())
    result.update(job_status="completed", stop_reason="synthetic_fixture_return", completed_roundtrips=1,
                  observability={"kind": "synthetic_component", "required_records_complete": True})
    result["outputs"]["sf1_rejected_raw"]["energy"].update(value=1., missing_reason="")
    return result


class LiveAuthorization(unittest.TestCase):
    def test_nondefault_four_inputs_and_legacy_protocol_are_supported(self):
        plan, auth = plan_auth()
        self.assertEqual(s.validate_live_authorization(plan, auth, "d_one")["gain_length_m"], 4.1)

    def test_default_denial_and_zero_allowance_do_not_reserve(self):
        plan, auth = plan_auth()
        with tempfile.TemporaryDirectory() as directory:
            args = dict(matlab="/missing_matlab", plan=plan, authorization=auth,
                        design_id="d_one", batch_dir=Path(directory)/"never_created", run_id="run_one")
            with self.assertRaises(PermissionError): s.execute_authorized_design(**args)
            auth["max_new_attempts"] = 0
            with self.assertRaises(PermissionError): s.execute_authorized_design(**args, execute_real=True)
            self.assertFalse(args["batch_dir"].exists())

    def test_changed_plan_unauthorized_id_and_unknown_fields_fail(self):
        plan, auth = plan_auth()
        with self.assertRaises(ValueError): s.validate_live_authorization(plan, auth, "other")
        bad = deepcopy(plan); bad["designs"][0]["design_config"]["pump_power_W"] = 9
        with self.assertRaises(ValueError): s.validate_live_authorization(bad, auth, "d_one")
        for key, value in (("extra", 1), ("max_new_attempts", True), ("seed", -1),
                           ("per_run_timeout_s", 29), ("save_waveforms", False),
                           ("observation_protocol", {"mode": "legacy", "roundtrips": 20})):
            bad = {**auth, key: value}
            with self.subTest(key=key), self.assertRaises(ValueError): s.validate_live_authorization(plan, bad, "d_one")

    def test_serial_ledger_refuses_run_or_directory_reset(self):
        plan, auth = plan_auth()
        with tempfile.TemporaryDirectory() as directory, patch.object(s, "ROOT", Path(directory)), \
                patch.object(s, "request_identity", return_value=identity()), \
                patch.object(s, "execute_once", return_value={"job_status": "completed"}) as execute:
            batch = Path(directory)/"reports/local/fixture_batch"
            result = s.execute_authorized_design(matlab="/bin/echo", plan=plan, authorization=auth,
                design_id="d_one", batch_dir=batch, run_id="first", execute_real=True)
            self.assertEqual(result["final_result"]["job_status"], "completed")
            request = execute.call_args.args[2]
            self.assertEqual(request["design_config"]["gain_length_m"], 4.1)
            self.assertEqual(request["requested"], {"PumpPower": 4, "cw2": 1030, "plot_on": False})
            self.assertNotIn("observation_options", request)
            self.assertTrue(request["save_waveforms"])
            with self.assertRaises(PermissionError):
                s.execute_authorized_design(matlab="/bin/echo", plan=plan, authorization=auth,
                    design_id="d_one", batch_dir=batch.with_name("different_batch"), run_id="second", execute_real=True)
            self.assertEqual(execute.call_count, 1)
            self.assertFalse(batch.with_name("different_batch").exists())

    def test_incomplete_attempt_remains_reserved_and_blocks_resume(self):
        plan, auth = plan_auth()
        with tempfile.TemporaryDirectory() as directory, patch.object(s, "ROOT", Path(directory)), \
                patch.object(s, "request_identity", return_value=identity()), \
                patch.object(s, "execute_once", side_effect=OSError("fixture final write failure")):
            args = dict(matlab="/bin/echo", plan=plan, authorization=auth, design_id="d_one",
                        batch_dir=Path(directory)/"reports/local/fixture", execute_real=True)
            with self.assertRaises(OSError): s.execute_authorized_design(**args, run_id="first")
            with self.assertRaises(RuntimeError): s.execute_authorized_design(**args, run_id="second")
            ledger = s.load_json(Path(directory)/"reports/local/live_authorizations/v4_component_only/attempt_000001.json")
            self.assertEqual(ledger["status"], "reserved")
            self.assertEqual(ledger["charged_wall_s"], 90)

    def test_cleanup_failure_requires_group_audit_before_any_next_design(self):
        plan, auth = plan_auth(); auth["max_new_attempts"] = 2
        failed = {"job_status": "failed", "supervisor": {"cleanup_verified": False, "cleanup_error": "fixture EPERM"}}
        with tempfile.TemporaryDirectory() as directory, patch.object(s, "ROOT", Path(directory)), \
                patch.object(s, "request_identity", return_value=identity()), \
                patch.object(s, "execute_once", return_value=failed):
            args = dict(matlab="/bin/echo", plan=plan, authorization=auth, design_id="d_one",
                        batch_dir=Path(directory)/"reports/local/fixture", execute_real=True)
            self.assertEqual(s.execute_authorized_design(**args, run_id="first")["final_result"], failed)
            with self.assertRaises(RuntimeError): s.execute_authorized_design(**args, run_id="second")

    def test_exhausted_cumulative_wall_and_stop_refuse_launch(self):
        plan, auth = plan_auth()
        with tempfile.TemporaryDirectory() as directory, patch.object(s, "ROOT", Path(directory)):
            ledger = Path(directory)/"reports/local/live_authorizations/v4_component_only"; ledger.mkdir(parents=True)
            s.atomic_json(ledger/"authorization.json", auth)
            s.atomic_json(ledger/"attempt_000001.json", {"status": "failed", "design_id": "other", "charged_wall_s": 180})
            auth["max_new_attempts"] = 2
            # A changed allowance requires a new explicit authorization, never mutation.
            with self.assertRaises(PermissionError):
                s.execute_authorized_design(matlab="/bin/echo", plan=plan, authorization=auth, design_id="d_one",
                    batch_dir=Path(directory)/"reports/local/fixture", run_id="blocked", execute_real=True)
            s.atomic_json(ledger/"authorization.json", auth, replace=True)  # artificial fixture setup only
            with self.assertRaises(PermissionError):
                s.execute_authorized_design(matlab="/bin/echo", plan=plan, authorization=auth, design_id="d_one",
                    batch_dir=Path(directory)/"reports/local/fixture", run_id="blocked", execute_real=True)
            (ledger/"STOP").touch()
            with self.assertRaises(PermissionError):
                s.execute_authorized_design(matlab="/bin/echo", plan=plan, authorization=auth, design_id="d_one",
                    batch_dir=Path(directory)/"reports/local/fixture", run_id="blocked", execute_real=True)


class CleanupSafety(unittest.TestCase):
    def test_process_table_absence_present_and_unknown_are_distinct(self):
        samples = [(0, "1 1\n12 8\n", "absent"), (0, "1 1\n12 99\n", "present"),
                   (1, "", "unknown"), (0, "", "unknown"), (0, "unparseable\n", "unknown")]
        for code, output, state in samples:
            with self.subTest(state=state), patch.object(s.monitor.subprocess, "run", return_value=Mock(returncode=code, stdout=output)):
                self.assertEqual(s.monitor.process_group_state(99), state)

    def test_exited_leader_does_not_discharge_eperm_for_live_or_unknown_group(self):
        process = Mock(pid=99); process.poll.return_value = 0
        for state in ("present", "unknown"):
            with self.subTest(state=state), patch.object(s.monitor.os, "killpg", side_effect=PermissionError("fixture EPERM")), \
                    patch.object(s.monitor, "process_group_state", return_value=state):
                with self.assertRaises(PermissionError): s.monitor.stop_owned(process)
        with patch.object(s.monitor.os, "killpg", side_effect=PermissionError("fixture EPERM")), \
                patch.object(s.monitor, "process_group_state", return_value="absent"):
            s.monitor.stop_owned(process)

    def test_own_short_child_cleanup_error_commits_failed_final(self):
        command = ["/bin/sh", "-c", "printf '%s' " + shlex.quote(json.dumps(candidate())) + " > matlab_candidate.json"]
        with tempfile.TemporaryDirectory() as directory, patch.object(s, "source_identity", return_value=identity()["source_identity"]), \
                patch.object(s.monitor, "stop_owned", side_effect=PermissionError("fixture cleanup EPERM after child exit")):
            folder = Path(directory)
            final = s.execute_once(command, folder, identity(), 10)
            runner = s.load_json(folder/"runner_record.json")
            self.assertEqual(runner["exit_code"], 0)
            self.assertFalse(runner["cleanup_verified"])
            self.assertEqual(final["job_status"], "failed")
            self.assertEqual(final["stop_reason"], "cleanup_error")
            self.assertIn("EPERM", final["supervisor"]["cleanup_error"])
            self.assertIsNone(final["outputs"]["sf1_rejected_raw"]["energy"]["value"])
            self.assertEqual(s.load_json(folder/"final_result.json"), final)

    def test_stop_precedes_cleanup_error(self):
        for first in ("timeout", "cancelled"):
            runner = {"status": "failed", "exit_code": 0, "cleanup_error": "fixture EPERM", "cleanup_verified": False,
                      "stop_events": [{"reason": first}], "stop_reason": first}
            final = s.merge_result(candidate(), runner, identity())
            self.assertEqual(final["job_status"], first)
            self.assertEqual(final["supervisor"]["cleanup_error"], "fixture EPERM")

    def test_failed_final_write_stays_failed_without_repairing_history(self):
        real_write = s.atomic_json
        def fail_final(path, value, **kwargs):
            if Path(path).name == "final_result.json": raise OSError("fixture full disk")
            return real_write(path, value, **kwargs)
        with tempfile.TemporaryDirectory() as directory, patch.object(s, "atomic_json", side_effect=fail_final), \
                patch.object(s, "source_identity", return_value=identity()["source_identity"]), \
                patch.object(s.monitor, "stop_owned", side_effect=PermissionError("fixture EPERM")):
            folder = Path(directory)
            with self.assertRaises(OSError): s.execute_once(["/bin/sh", "-c", "exit 0"], folder, identity(), 10)
            self.assertFalse((folder/"final_result.json").exists())
            self.assertEqual(s.load_json(folder/"runner_record.json")["status"], "failed")


if __name__ == "__main__":
    unittest.main()
