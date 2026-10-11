"""Python-only four-input and saved-evidence gates; fixtures are not solver runs."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from mamyshev_ml import supervisor as s


class DesignTest(unittest.TestCase):
    def test_values_and_save_grid_legality(self):
        for key, value in (("pump_power_W", 4.1), ("filter_offset_nm", 9.5),
                           ("filter2_bw_nm", 3.2), ("gain_length_m", 4.1)):
            changed = dict(s.DEFAULT_DESIGN_CONFIG, **{key: value})
            self.assertEqual(s.validate_design_config(changed), changed)
        self.assertEqual(s.validate_design_config(dict(s.DEFAULT_DESIGN_CONFIG, pump_power_W=0))["pump_power_W"], 0)

    def test_illegal_unknown_missing_nonfinite_boolean_and_conflicting_values(self):
        variants = [None, [], {}, dict(s.DEFAULT_DESIGN_CONFIG, cw2=1030)]
        variants += [dict(s.DEFAULT_DESIGN_CONFIG, pump_power_W=n) for n in (True, "4", -1, float("nan"), float("inf"), 1+2j)]
        variants += [dict(s.DEFAULT_DESIGN_CONFIG, **{key: value}) for key, value in
                     (("gain_length_m", 0), ("gain_length_m", .05), ("gain_length_m", 5e-324),
                      ("gain_length_m", 4.15), ("gain_length_m", 1e308),
                      ("filter2_bw_nm", 0), ("filter_offset_nm", 1040))]
        for value in variants:
            with self.subTest(value=value), self.assertRaises(ValueError):
                s.validate_design_config(value)

    def test_duplicate_keys_are_not_silently_accepted(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.json"
            path.write_text('{"pump_power_W":4,"pump_power_W":5}')
            with self.assertRaisesRegex(ValueError, "Duplicate"):
                s.load_json(path)

    def test_default_exact_reference_and_only_declared_dependencies_change(self):
        # Deliberately small reference fixture, not a physical configuration.
        baseline = {"PumpPower_W": 4, "cw2_nm": 1030, "spectral_filter2": {"cw": 1030, "bw": 3},
            "fiber_cavity": [{"L0": n, "betas": [0, 4882.1], "MFD": 10.5} for n in (4, .4, 1.5, 3.2)],
            "gain_rate_eqn": {"copump_power": 4, "t_rep": 4.4427110000000013e-8, "other": "unchanged"}}
        before = deepcopy(baseline)
        self.assertEqual(s.design_reference_configuration(baseline, s.DEFAULT_DESIGN_CONFIG), baseline)
        for key, value in (("pump_power_W", 4.1), ("filter_offset_nm", 9.5),
                           ("filter2_bw_nm", 3.2), ("gain_length_m", 4.1)):
            design = dict(s.DEFAULT_DESIGN_CONFIG, **{key: value})
            changed = s.design_reference_configuration(baseline, design)
            self.assertEqual(changed["fiber_cavity"][1:], baseline["fiber_cavity"][1:])
            self.assertEqual(changed["gain_rate_eqn"]["other"], "unchanged")
            self.assertEqual(changed["PumpPower_W"], design["pump_power_W"])
            self.assertEqual(changed["gain_rate_eqn"]["copump_power"], design["pump_power_W"])
            self.assertEqual(changed["spectral_filter2"], {"cw": 1040-design["filter_offset_nm"], "bw": design["filter2_bw_nm"]})
            self.assertEqual(changed["fiber_cavity"][0]["L0"], design["gain_length_m"])
            if key == "gain_length_m":
                self.assertNotEqual(changed["gain_rate_eqn"]["t_rep"], baseline["gain_rate_eqn"]["t_rep"])
        self.assertEqual(baseline, before)

    def test_new_short_batch_uses_300_seconds_and_keeps_old_600(self):
        records = [{"status": "failed", "elapsed_s": 180}]
        self.assertEqual(s.monitor.BATCH_LIMITS_S["config_waveform_001"], 300)
        self.assertEqual(s.monitor.remaining_budget(records, 300), 120)
        self.assertEqual(s.monitor.remaining_budget(records), 420)
        self.assertEqual(s.monitor.PROCESS_LIMIT_S, 180)

    def test_four_input_gate_checks_actual_request_filter_calls_and_model_rules(self):
        path = s.ROOT / "reports/local/phase1/baseline_001/configuration.json"
        if not path.exists():
            self.skipTest("Historical local reference is not public test data")
        baseline = s.load_json(path)
        for key, value in (("pump_power_W", 4.1), ("filter_offset_nm", 9.5),
                           ("filter2_bw_nm", 3.2), ("gain_length_m", 4.1)):
            design = dict(s.DEFAULT_DESIGN_CONFIG, **{key: value})
            config = s.design_reference_configuration(baseline, design)
            expected = {"design_config": design, "save_waveforms": True,
                "requested": {"PumpPower": design["pump_power_W"], "cw2": 1040-design["filter_offset_nm"], "plot_on": False}}
            rules = {"model_rules_id": "ring_legacy_rules_config_v1", "historical_reference_id": "legacy_ring_phase1_v1",
                "matches_historical_reference": False, "H02_status": "unresolved", "passive_declared_MFD_um": 10.5,
                "passive_SR_derived_MFD_um": 5.95, "passive_actual_SR_m_minus2": baseline["fiber_cavity"][1]["SR"],
                "passive_actual_area_m2": 1/baseline["fiber_cavity"][1]["SR"],
                "passive_lengths_m": [.4, 1.5, 3.2], "pigtail_length_m": .2,
                "N_total_override": 9e7, "output_port": "1-H", "filter_order": 4}
            calls = [{"roundtrip": 1, "filter_id": name, "cw_nm": config["spectral_filter"+name[-1]]["cw"],
                      "bw_nm": config["spectral_filter"+name[-1]]["bw"], "order": 4, "plot_on": False}
                     for name in ("sf1", "sf2")]
            records = {"requested": {"context": deepcopy(expected)},
                "configuration": {"design_config": design, "model_rules": rules},
                "runtime_calls": {"filter_calls": calls}}
            with self.subTest(design=design):
                self.assertIsNone(s.verify_design_records(records, expected, baseline, config, 1))
                bad = deepcopy(records); bad["runtime_calls"]["filter_calls"][1]["bw_nm"] += .1
                self.assertIsNotNone(s.verify_design_records(bad, expected, baseline, config, 1))
                bad = deepcopy(records); bad["configuration"]["model_rules"]["matches_historical_reference"] = True
                self.assertIsNotNone(s.verify_design_records(bad, expected, baseline, config, 1))
                bad = deepcopy(records); bad["requested"]["context"]["requested"]["cw2"] += 1
                self.assertIsNotNone(s.verify_design_records(bad, expected, baseline, config, 1))


class WaveformGateTest(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.folder = Path(temporary.name)
        self.expected = {"run_id": "explicit_python_fixture", "mode": "real",
            "source_identity": {"digest": "synthetic", "files": []},
            "design_config": deepcopy(s.DEFAULT_DESIGN_CONFIG), "save_waveforms": True}
        self.config = {"Nt": 8, "dt_ps": .5, "sim_cavity": [{"f0": 290}]}
        self.candidate = s._blank(self.expected)
        self.candidate.update(job_status="completed", stop_reason="fixture_return", completed_roundtrips=1)
        self.candidate["outputs"]["compressed_analysis"]["energy"]["value"] = 1.25
        self.candidate["outputs"]["compressed_analysis"]["field"].update(
            available=True, artifact="waveforms_final.mat", variable="compressed_field")
        # This is solely a header/integrity fixture. MATLAB read/write behavior
        # and complex values are covered separately by the MATLAB writer test.
        mat = b"MATLAB 5.0 MAT-file synthetic Python header fixture".ljust(126, b" ") + b"IM" + b"fixture payload"
        def entry(name):
            path = self.folder / name; path.write_bytes(mat)
            return {"path": name, "bytes": len(mat), "sha256": hashlib.sha256(mat).hexdigest(),
                    "field_size": [8, 1], "finite": True}
        round_entry = dict(entry("waveforms_round_0001.mat"), roundtrip=1, raw_energy_nJ=1.5)
        final_entry = dict(entry("waveforms_final.mat"), compressed_field_available=True,
                           compressed_field_missing_reason="")
        self.manifest = {"schema_version": "mamyshev_waveforms_v1",
            "run_id": self.expected["run_id"], "source_identity": self.expected["source_identity"],
            "design_config": self.expected["design_config"], "initialized": True, "finalized": True,
            "completed_roundtrips": 1, "raw_energy_history_nJ": [1.5], "rounds": [round_entry], "final": final_entry,
            "units": {"field": "sqrt(W)", "t": "ps", "f": "THz", "f0": "THz", "energy": "nJ", "power": "W"},
            "conventions": {"time_to_frequency": "fftshift(ifft(A,[],1),1)"},
            "planes": {key: "synthetic fixture location" for key in ("pre_tracker_field", "post_tracker_field", "output_field", "pigtail_output_field", "compressed_field")},
            "grid": {"sample_count": 8, "dt_ps": .5, "f0_THz": 290, "time_size": [1, 8], "frequency_size": [8, 1]}}
        self.paths = {"waveform_manifest.json", "waveforms_round_0001.mat", "waveforms_final.mat"}
        self.candidate["waveform_artifacts"] = {"manifest_path": "waveform_manifest.json", "finalized": True,
            "completed_roundtrips": 1, "artifacts": sorted(self.paths)}

    def check(self, manifest=None):
        (self.folder / "waveform_manifest.json").write_text(json.dumps(self.manifest if manifest is None else manifest))
        return s.verify_waveform_records(self.candidate, self.expected, self.folder, self.config)

    def test_complete_saved_reference_and_single_round_json_shape(self):
        self.assertEqual(self.check(), self.paths)
        self.manifest["rounds"] = self.manifest["rounds"][0]
        self.manifest["raw_energy_history_nJ"] = 1.5
        self.assertEqual(self.check(), self.paths)

    def test_identity_dimensions_units_completeness_and_field_references(self):
        variants = []
        for key, value in (("run_id", "wrong"), ("finalized", False), ("completed_roundtrips", 2),
                           ("rounds", []), ("raw_energy_history_nJ", [None])):
            bad = deepcopy(self.manifest); bad[key] = value; variants.append(bad)
        for key, value in (("sample_count", 4), ("dt_ps", 1), ("f0_THz", 291)):
            bad = deepcopy(self.manifest); bad["grid"][key] = value; variants.append(bad)
        bad = deepcopy(self.manifest); bad["units"]["t"] = "fs"; variants.append(bad)
        bad = deepcopy(self.manifest); bad["rounds"][0]["finite"] = False; variants.append(bad)
        bad = deepcopy(self.manifest); bad["final"]["path"] = "../outside.mat"; variants.append(bad)
        for bad in variants:
            with self.subTest(bad=bad), self.assertRaises((ValueError, OSError)):
                self.check(bad)
        self.candidate["outputs"]["compressed_analysis"]["field"]["variable"] = "ideal_transform_limited"
        with self.assertRaisesRegex(ValueError, "compressed"):
            self.check()

    def test_corrupt_missing_and_symlink_artifacts_fail_closed(self):
        path = self.folder / "waveforms_final.mat"
        original = path.read_bytes(); path.write_bytes(b"corrupt")
        with self.assertRaises(ValueError): self.check()
        path.unlink()
        with self.assertRaises(ValueError): self.check()
        elsewhere = self.folder / "fixture.mat"; elsewhere.write_bytes(original)
        path.symlink_to(elsewhere)
        with self.assertRaises(ValueError): self.check()

    def test_header_is_checked_even_when_hash_is_updated(self):
        path = self.folder / "waveforms_final.mat"; path.write_bytes(b"not MAT")
        self.manifest["final"].update(bytes=7, sha256=hashlib.sha256(b"not MAT").hexdigest())
        with self.assertRaisesRegex(ValueError, "MAT header"):
            self.check()

    def test_parent_failure_does_not_promote_waveform_reference(self):
        runner = {"status": "failed", "exit_code": -15, "stop_reason": "timeout",
                  "stop_events": [{"reason": "timeout"}], "elapsed_s": 1}
        result = s.merge_result(self.candidate, runner, self.expected)
        self.assertEqual(result["job_status"], "timeout")
        self.assertIsNone(result["outputs"]["compressed_analysis"]["energy"]["value"])
        self.assertIsNone(result["outputs"]["compressed_analysis"]["field"]["value"])
        self.assertFalse(result["outputs"]["compressed_analysis"]["field"]["available"])
        self.assertNotIn("artifact", result["outputs"]["compressed_analysis"]["field"])
        self.assertFalse(result["waveform_artifacts"]["validated_for_final"])


if __name__ == "__main__":
    unittest.main()
