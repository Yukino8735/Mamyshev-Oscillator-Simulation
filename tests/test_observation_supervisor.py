"""Observation-only Python record fixtures; never MATLAB or propagation."""
from copy import deepcopy
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from mamyshev_ml import supervisor as s


OPTIONS = {"observation_mode": "fixed_roundtrips", "observation_roundtrips": 20}


def observation_fixture(rounds=20, stop="observation_budget_reached", first=6):
    expected = {"run_id": "observation_python_fixture", "mode": "real",
        "source_identity": {"digest": "synthetic_record_fixture", "files": []},
        "design_config": deepcopy(s.DEFAULT_DESIGN_CONFIG), "save_waveforms": True,
        "observation_options": deepcopy(OPTIONS)}
    history = [{"roundtrip": k, "converged": first is not None and k >= first,
        "force_stop_convergence": False, "force_stop_fluctuation": False,
        "criterion_reason": "energy_converged" if first is not None and k >= first else "insufficient_history" if k <= 5 else "energy_not_converged",
        "stop_reason": stop if k == rounds else ""} for k in range(1, rounds+1)]
    if stop == "legacy_energy_fluctuation_stop":
        history[-1].update(converged=False, force_stop_fluctuation=True, criterion_reason="energy_fluctuation_stop")
    records = {"requested": {"context": {"observation_options": deepcopy(OPTIONS)}},
        "configuration": {"observation_options": deepcopy(OPTIONS), "pulse_death_energy_nJ": .01},
        "runtime_calls": {"observation_options": deepcopy(OPTIONS), "observation_history": history,
                          "observation_first_legacy_convergence_roundtrip": first}}
    candidate = s._blank(expected)
    candidate.update(job_status="completed", completed_roundtrips=rounds, stop_reason=stop,
        observation={"options": deepcopy(OPTIONS), "history": deepcopy(history),
                     "first_legacy_convergence_roundtrip": first, "stop_reason": stop},
        legacy_flags={"converged": history[-1]["converged"], "force_stop": history[-1]["force_stop_convergence"],
                      "pulse_survives": stop != "legacy_energy_below_threshold"})
    manifest = {"completed_roundtrips": rounds, "raw_energy_history_nJ": [1.0]*rounds}
    if stop == "legacy_energy_below_threshold":
        manifest["raw_energy_history_nJ"][-1] = .001
    return candidate, expected, records, manifest


class ObservationOptionsTest(unittest.TestCase):
    def test_options_are_separate_and_integer_bounded(self):
        self.assertEqual(s.validate_observation_options(OPTIONS), OPTIONS)
        for count in (1, 20, 50):
            self.assertEqual(s.validate_observation_options(dict(OPTIONS, observation_roundtrips=count))["observation_roundtrips"], count)
        self.assertEqual(set(s.DEFAULT_DESIGN_CONFIG), {"pump_power_W", "filter_offset_nm", "filter2_bw_nm", "gain_length_m"})

    def test_missing_unknown_invalid_modes_and_noninteger_values_rejected(self):
        values = [None, {}, {"observation_mode": "fixed_roundtrips"}, dict(OPTIONS, pump_power_W=4),
                  dict(OPTIONS, observation_mode="legacy")]
        values += [dict(OPTIONS, observation_roundtrips=value) for value in (True, 0, -1, 51, 20.5, "20", float("inf"), float("nan"))]
        for value in values:
            with self.subTest(value=value), self.assertRaises(ValueError):
                s.validate_observation_options(value)

    def test_stationarity_budget_is_independent_and_old_limits_unchanged(self):
        self.assertEqual(s.monitor.BATCH_LIMITS_S["stationarity_001"], 300)
        self.assertNotEqual(s.monitor.batch_directory("stationarity_001"), s.monitor.batch_directory("config_waveform_001"))
        self.assertEqual(s.monitor.remaining_budget([{"status": "failed", "elapsed_s": 180}], 300), 120)
        self.assertEqual(s.monitor.remaining_budget([]), 600)
        self.assertEqual(s.monitor.PROCESS_LIMIT_S, 180)

    def test_3600_total_reaches_same_monitor_with_30_second_included_reserve(self):
        expected = observation_fixture()[1]
        runner = {"status": "completed", "exit_code": 0, "stop_reason": "process_exit", "stop_events": [], "elapsed_s": .1}
        with tempfile.TemporaryDirectory() as directory, \
                patch.object(s.monitor, "run_isolated", return_value=runner) as monitor, \
                patch.object(s, "source_identity", return_value=expected["source_identity"]), \
                patch.object(s.time, "monotonic", side_effect=[100., 100.25, 100.5]):
            result = s.execute_once(["never_executed_fixture"], Path(directory), expected, 3600)
        self.assertEqual(monitor.call_args.args[3], 3599.75)
        self.assertEqual(monitor.call_args.kwargs["shutdown_reserve_s"], 30)
        self.assertEqual(result["supervisor"]["total_wall_limit_s"], 3600)
        self.assertEqual(result["supervisor"]["shutdown_and_finalization_reserve_s"], 30)


class ObservationGateTest(unittest.TestCase):
    def test_full_20_round_history_preserves_earlier_convergence_and_completes_budget(self):
        args = observation_fixture()
        self.assertIsNone(s.verify_observation_records(*args))
        self.assertTrue(args[0]["legacy_flags"]["converged"])
        self.assertEqual(args[0]["observation"]["first_legacy_convergence_roundtrip"], 6)

    def test_no_legacy_convergence_is_explicit_null(self):
        args = observation_fixture(first=None)
        self.assertIsNone(s.verify_observation_records(*args))
        del args[2]["runtime_calls"]["observation_first_legacy_convergence_roundtrip"]
        self.assertIsNotNone(s.verify_observation_records(*args))

    def test_legacy_default_path_does_not_require_new_fields(self):
        self.assertIsNone(s.verify_observation_records({}, {}, {}, {}))

    def test_death_and_fluctuation_stop_before_budget_and_override_budget_on_last_round(self):
        for rounds in (12, 20):
            for reason in ("legacy_energy_below_threshold", "legacy_energy_fluctuation_stop"):
                with self.subTest(rounds=rounds, reason=reason):
                    self.assertIsNone(s.verify_observation_records(*observation_fixture(rounds, reason)))
        args = observation_fixture(12, "legacy_energy_below_threshold")
        args[3]["raw_energy_history_nJ"][-1] = .1
        self.assertIsNotNone(s.verify_observation_records(*args))

    def test_premature_old_convergence_or_maxrt_cannot_be_completed_observation(self):
        for reason in ("legacy_energy_convergence", "legacy_average_energy_convergence", "max_rt_reached", "observation_budget_reached"):
            with self.subTest(reason=reason):
                self.assertIsNotNone(s.verify_observation_records(*observation_fixture(6, reason)))

    def test_request_B_C_candidate_options_and_history_must_agree(self):
        variants = []
        for location in ("requested", "configuration", "runtime_calls"):
            args = observation_fixture(); item = args[2][location]
            if location == "requested": item = item["context"]
            item["observation_options"]["observation_roundtrips"] = 19; variants.append(args)
        args = observation_fixture(); args[0]["observation"]["options"]["observation_roundtrips"] = 19; variants.append(args)
        args = observation_fixture(); args[2]["runtime_calls"]["observation_history"].pop(); variants.append(args)
        args = observation_fixture(); args[0]["observation"]["history"][0]["roundtrip"] = 2; variants.append(args)
        args = observation_fixture(); args[2]["runtime_calls"]["observation_first_legacy_convergence_roundtrip"] = 7; variants.append(args)
        for args in variants:
            with self.subTest(args=args):
                self.assertIsNotNone(s.verify_observation_records(*args))

    def test_average_convergence_is_recorded_and_bypassed_without_changing_legacy_flag(self):
        args = observation_fixture(first=None)
        for history in (args[2]["runtime_calls"]["observation_history"], args[0]["observation"]["history"]):
            for entry in history[9:]:
                entry.update(force_stop_convergence=True, criterion_reason="energy_average_converged")
        args[2]["runtime_calls"]["observation_first_legacy_convergence_roundtrip"] = 10
        args[0]["observation"]["first_legacy_convergence_roundtrip"] = 10
        args[0]["legacy_flags"]["force_stop"] = True
        self.assertIsNone(s.verify_observation_records(*args))

    def test_invalid_flags_reason_sequence_and_energy_fail_closed(self):
        variants = []
        for change in ({"roundtrip": True}, {"converged": 0}, {"criterion_reason": ""},
                       {"force_stop_convergence": True}, {"stop_reason": "legacy_energy_fluctuation_stop"}):
            args = observation_fixture()
            for history in (args[2]["runtime_calls"]["observation_history"], args[0]["observation"]["history"]):
                history[0].update(change)
            variants.append(args)
        for value in (None, float("nan"), -1):
            args = observation_fixture(); args[3]["raw_energy_history_nJ"][1] = value; variants.append(args)
        args = observation_fixture(); args[0]["legacy_flags"]["converged"] = False; variants.append(args)
        args = observation_fixture(); args[0]["legacy_flags"]["pulse_survives"] = False; variants.append(args)
        for args in variants:
            with self.subTest(args=args):
                self.assertIsNotNone(s.verify_observation_records(*args))

    def test_cannot_continue_after_a_real_death_or_fluctuation_stop(self):
        args = observation_fixture()
        args[3]["raw_energy_history_nJ"][11] = .001
        for history in (args[2]["runtime_calls"]["observation_history"], args[0]["observation"]["history"]):
            history[11]["stop_reason"] = "legacy_energy_below_threshold"
        self.assertIsNotNone(s.verify_observation_records(*args))

    def test_parent_timeout_still_overrides_completed_observation(self):
        candidate, expected, _, _ = observation_fixture()
        candidate["outputs"]["sf1_rejected_raw"]["energy"].update(value=1.0, missing_reason="")
        runner = {"status": "failed", "exit_code": 0, "stop_events": [{"reason": "timeout"}], "elapsed_s": 3570}
        final = s.merge_result(candidate, runner, expected)
        self.assertEqual(final["job_status"], "timeout")
        self.assertIsNone(final["outputs"]["sf1_rejected_raw"]["energy"]["value"])
        self.assertFalse(final["observation"]["validated_for_final"])
        self.assertFalse(final["eligible_as_validated_training_truth"])

    def test_existing_completed_gate_stays_compatible_and_calls_new_gate_only_for_opt_in(self):
        folder = s.ROOT / "reports/local/phase2/config_waveform_validation_001/config_waveform_001"
        if not (folder / "matlab_candidate.json").is_file():
            self.skipTest("Historical local completed-run evidence is not public test data")
        candidate = s.load_json(folder / "matlab_candidate.json")
        expected = s.load_json(folder / "launch_request.json")
        # These are read-only historical artifacts, never rewritten or merged.
        self.assertIsNone(s.validate_candidate(candidate, expected))
        with patch.object(s, "verify_observation_records", return_value="synthetic observation gate rejection") as gate:
            self.assertIsNone(s.required_records_error(candidate, expected, folder))
            gate.assert_not_called()
            opt_in = dict(expected, observation_options=deepcopy(OPTIONS))
            self.assertEqual(s.required_records_error(candidate, opt_in, folder), "synthetic observation gate rejection")
            gate.assert_called_once()


if __name__ == "__main__":
    unittest.main()
