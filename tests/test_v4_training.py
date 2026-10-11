"""Artificial contract fixtures only: zero oracle calls, MATLAB launches or fits."""
import copy
import csv
import json
from pathlib import Path
import tempfile
import unittest
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from mamyshev_ml.v4_evaluators import TARGETS, UNITS, design_id, import_safe_result, null_evaluation
from mamyshev_ml.v4_store import V4Store
from mamyshev_ml.v4_training import (arrays, export_records, fit_model, load_model, make_split,
                                    qualify_record, read_records, training_records, validate_split)

D = {"pump_power_W": 4., "filter_offset_nm": 10., "filter2_bw_nm": 3., "gain_length_m": 4.}
IDENTITY = {"source": "repository_guided_synthetic", "backend": "mamyshev_repository_guided_synthetic_v3",
    "numerical_version": "artificial_fixture_not_oracle_sha", "seed": 0,
    "observation_protocol": {"kind": "artificial_contract_fixture"},
    "metric_definition": {"plane": "constructed_compressed_scalars", "units": UNITS,
                          "recipe_sha256": "artificial_fixture_not_research"}}


def fixture_record(index=0):
    design = dict(D, pump_power_W=3. + index / 10)
    record = null_evaluation(design, copy.deepcopy(IDENTITY), "", "completed")
    record.update(evaluation_id="fixture_" + str(index),
                  targets=dict(zip(TARGETS, (100. + index, 40. + index, 2. + index / 100))),
                  engineering_fixture=True)
    return record


class TestTrainingBridge(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def real_contract_fixture(self):
        """Hand-written parent-contract JSON, explicitly not a physical simulation."""
        from mamyshev_ml.supervisor import _blank
        folder = self.path / "artificial_parent_fixture"
        folder.mkdir()
        request = {"run_id": "artificial_contract_fixture", "mode": "real", "seed": 0,
            "source_identity": {"digest": "fixture_not_production", "files": []}, "design_config": D,
            "engineering_fixture_description": "Contract test only, no solver was executed"}
        final = _blank(request)
        final["job_status"] = "completed"
        final["provenance"]["backend_entrypoint"] = "run_mamyshev_config"
        final["outputs"]["compressed_analysis"].update(
            plane="After output pigtail and compressor analysis", processing="Legacy idealized Treacy-t compression analysis")
        for key, unit, source, value in (
            ("energy", "nJ", "run_mamyshev.compressed_field and t", 101.),
            ("fwhm", "fs", "run_mamyshev.dechirped_fwhm_fs", 40.),
            ("peak_power", "W", "run_mamyshev.dechirped_peak_power_W", 2e6)):
            final["outputs"]["compressed_analysis"][key] = {
                "value": value, "unit": unit, "source": source,
                "definition": "Artificial fixture metric, never a research sample", "missing_reason": ""}
        runner = {"run_id": request["run_id"], "source_identity": request["source_identity"],
                  "exit_code": 0, "status": "completed", "cleanup_verified": True,
                  "stop_events": [], "stop_reason": "process_exit"}
        final["supervisor"] = {"final_writer": "parent_supervisor", "runner_record": "runner_record.json",
            "candidate_valid": True, "required_records_error": None, "exit_code": 0, "stop_events": []}
        for name, value in (("launch_request.json", request), ("runner_record.json", runner), ("final_result.json", final)):
            (folder / name).write_text(json.dumps(value))
        return folder, import_safe_result(folder / "final_result.json")

    def test_completed_solver_emulation_does_not_claim_physical_truth(self):
        folder, record = self.real_contract_fixture()
        before = (folder / "final_result.json").read_bytes()
        result = qualify_record(record, record["identity"])
        self.assertEqual(result["task"], "solver_emulation")
        self.assertTrue(result["eligible_for_source_emulation"])
        self.assertFalse(result["physical_validation_claim"])
        self.assertFalse(record["eligible_as_validated_training_truth"])
        self.assertEqual(record["physical_state"], "undetermined")
        self.assertEqual(before, (folder / "final_result.json").read_bytes())
        self.assertEqual(arrays([record])[1].tolist(), [[101., 40., 2.]])

    def test_missing_final_and_modified_record_rejected(self):
        folder, record = self.real_contract_fixture()
        edited = copy.deepcopy(record)
        edited["targets"][TARGETS[0]] += 1
        with self.assertRaisesRegex(ValueError, "original verified final"):
            qualify_record(edited, edited["identity"])
        (folder / "final_result.json").unlink()
        with self.assertRaises(FileNotFoundError):
            qualify_record(record, record["identity"])

    def test_wrong_plane_upstream_energy_and_nonreal_request_rejected(self):
        folder, record = self.real_contract_fixture()
        final_path = folder / "final_result.json"
        final = json.loads(final_path.read_text())
        final["outputs"]["compressed_analysis"]["energy"]["source"] = "run_mamyshev.output_energy"
        final_path.write_text(json.dumps(final))
        record = import_safe_result(final_path)
        with self.assertRaisesRegex(ValueError, "upstream"):
            qualify_record(record, record["identity"])
        request_path = folder / "launch_request.json"
        request = json.loads(request_path.read_text())
        request["mode"] = "synthetic_wrapper_component"
        request_path.write_text(json.dumps(request))
        with self.assertRaisesRegex(ValueError, "Component fixtures"):
            qualify_record(record, record["identity"])

    def test_prediction_failure_null_boolean_nonfinite_and_units_rejected(self):
        original = fixture_record()
        variants = [dict(original, kind="Prediction"), dict(original, job_status="timeout"),
                    dict(original, units=dict(UNITS, compressed_energy_nJ="J"))]
        for value in (None, float("nan"), True, 0., -1.):
            variants.append(dict(original, targets=dict(original["targets"], compressed_energy_nJ=value)))
        for record in variants:
            with self.subTest(record=record):
                with self.assertRaises(ValueError):
                    qualify_record(record, IDENTITY)

    def test_every_identity_field_is_explicit_and_not_mixed(self):
        record = fixture_record()
        for key in IDENTITY:
            wrong = copy.deepcopy(IDENTITY)
            wrong[key] = "different"
            with self.subTest(key=key):
                with self.assertRaises(ValueError):
                    qualify_record(record, wrong)
        with self.assertRaises(ValueError):
            qualify_record(record, {"source": IDENTITY["source"]})

    def test_readonly_db_lossless_csv_and_qualified_store_path(self):
        database = self.path / "fixture.sqlite"
        store = V4Store(database)
        records = [fixture_record(i) for i in range(12)]
        for row in records:
            store.save_evaluation(row)
        failed = fixture_record(20)
        failed.update(job_status="failed", targets=dict.fromkeys(TARGETS))
        store.save_evaluation(failed)
        self.assertEqual(len(training_records(store, identity=IDENTITY)), 12)
        store.close()
        before = database.read_bytes()
        selected, audit = read_records(db=database, identity=IDENTITY)
        self.assertEqual(len(selected), 12)
        self.assertEqual(len(audit["excluded"]), 1)
        path = self.path / "training.csv"
        export_records(selected, path, identity=IDENTITY)
        restored, restored_audit = read_records(csv_path=path, identity=IDENTITY)
        self.assertEqual(selected, restored)
        self.assertEqual(restored_audit["unique_designs"], 12)
        self.assertEqual(database.read_bytes(), before)
        with self.assertRaises(FileExistsError):
            export_records(selected, path, identity=IDENTITY)

    def test_csv_cannot_silently_relabel_or_change_targets(self):
        path = self.path / "training.csv"
        export_records([fixture_record()], path, identity=IDENTITY)
        with path.open(newline="") as stream:
            reader = csv.DictReader(stream)
            fields, rows = reader.fieldnames, list(reader)
        rows[0][TARGETS[0]] = "999"
        with path.open("w", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=fields)
            writer.writeheader(); writer.writerows(rows)
        with self.assertRaisesRegex(ValueError, "differs"):
            read_records(csv_path=path, identity=IDENTITY)

    def test_grouped_split_same_design_repeats_never_cross_roles(self):
        records = [fixture_record(i) for i in range(12)]
        repeated = copy.deepcopy(records[0]); repeated["evaluation_id"] += "_second"
        records.append(repeated)
        split = make_split(records, seed=31)
        self.assertEqual(split, make_split(records, seed=31))
        groups = validate_split(records, split)
        self.assertEqual(sum(len(group) for group in groups), 12)
        self.assertEqual(sum(records[0]["design_id"] in group for group in groups), 1)
        bad = copy.deepcopy(split); bad["development"].append(bad["train"][0])
        with self.assertRaisesRegex(ValueError, "cross"):
            validate_split(records, bad)

    def test_insufficient_data_and_unknown_split_are_not_fit_or_scored(self):
        records = [fixture_record()]
        with self.assertRaisesRegex(ValueError, "Insufficient"):
            make_split(records)
        out = self.path / "not_created"
        split = {"schema_version": "design_group_split_v1", "group_by": "design_id",
                 "train": [records[0]["design_id"]], "development": [], "test": []}
        with self.assertRaisesRegex(ValueError, "Insufficient"):
            fit_model(records, split, out, identity=IDENTITY, model_id="fixture_must_not_fit")
        self.assertFalse(out.exists())
        split["unknown"] = True
        with self.assertRaisesRegex(ValueError, "unknown"):
            validate_split(records, split)

    def test_model_loading_requires_explicit_trust_before_deserialization(self):
        with self.assertRaises(PermissionError):
            load_model(self.path / "absent")


if __name__ == "__main__":
    unittest.main()
