"""Artificial data-identity fixtures; no oracle, fit or real-data label queries."""
import csv
import hashlib
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from mamyshev_ml import v42_data as data


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value))


def design(index=0):
    return dict(zip(data.FEATURES, (4.0 + index / 10000, 10.0, 3.0, 4.0)))


def role_fixture(folder, role="train"):
    """One artificial stored Evaluation with independently checked CSV and SQL."""
    folder.mkdir(parents=True)
    x = design(); did = data.canonical_id(x); eid = "artificial-component-evaluation"
    identity = {"source": data.SOURCE, "backend": data.BACKEND, "seed": 0,
                "numerical_version": "artificial_component_fixture", "observation_protocol": {},
                "metric_definition": {"units": data.UNITS}}
    row = {"design_id": did, "role": role, "group": "slice", **x, "order_in_role": 1}
    labels = {**row, **dict(zip(data.TARGETS, (120.0, 30.0, 3.0))),
              "source_kind": data.SOURCE, "region": "slice"}
    for name, value in (("inputs.csv", row), ("labels.csv", labels)):
        with (folder / name).open("w", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(value)); writer.writeheader(); writer.writerow(value)
    write_json(folder / "accounting.json", {"role": role, "identity": identity, "new_labels": 1,
        "oracle_calls": 1, "unique_computations": 1, "cache_hits": 0})
    record = {"kind": "Evaluation", "design_id": did, "design": x, "identity": identity,
        "source_kind": data.SOURCE, "job_status": "completed", "units": data.UNITS,
        "request_id": f"v41/{role}/{did}", "evaluation_id": eid, "cache_hit": False,
        "targets": {k: labels[k] for k in data.TARGETS}}
    with sqlite3.connect(folder / "evaluations.sqlite") as db:
        db.execute("CREATE TABLE designs(design_id TEXT,design_json TEXT)")
        db.execute("CREATE TABLE evaluations(evaluation_id TEXT,design_id TEXT,identity_hash TEXT,source TEXT,job_status TEXT,record_json TEXT)")
        db.execute("INSERT INTO designs VALUES(?,?)", (did, json.dumps(x)))
        db.execute("INSERT INTO evaluations VALUES(?,?,?,?,?,?)", (eid, did,
            hashlib.sha256(data.canonical(identity).encode()).hexdigest(), data.SOURCE, "completed", json.dumps(record)))
    return identity, {did: {"role": role, "evaluation_id": eid}}, record


class V42DataTests(unittest.TestCase):
    def test_three_uploaded_hashes_and_tamper(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            mapping = {"ACCURACY_V4_1_TARGETED_REPORT.md": Path("docs/ACCURACY_V4_1_TARGETED_REPORT.md"),
                       "selection.json": data.OLD_REL / "development/selection.json",
                       "summary.json": data.OLD_REL / "summary/summary.json"}
            hashes = {}
            for name, relative in mapping.items():
                write_json(root / relative, {"artificial": name}); hashes[name] = data.sha(root / relative)
            write_json(root / data.PACKAGE_REL / "UPLOAD_REVIEW_CHECKS.json", {"inputs": hashes})
            self.assertEqual(len(data.verify_uploads(root)["files"]), 3)
            (root / mapping["selection.json"]).write_text("changed")
            with self.assertRaisesRegex(ValueError, "identity differs"):
                data.verify_uploads(root)

    def test_saved_csv_sql_and_ledger_exact_agreement(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp) / "train"; identity, completed, record = role_fixture(folder)
            rows = data._load_saved_role(folder, "train", expected_identity=identity, completed=completed, expected_count=1)
            self.assertEqual({k: rows[0][k] for k in data.TARGETS}, record["targets"])
            self.assertEqual(rows[0]["design_id"], record["design_id"])
            self.assertEqual(rows[0]["order_in_role"], 1)

    def test_saved_source_target_identity_and_ledger_mismatch_fail_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            for case in ("target", "source", "identity", "ledger"):
                with self.subTest(case=case):
                    folder = Path(tmp) / case; identity, completed, record = role_fixture(folder)
                    if case == "target": record["targets"][data.TARGETS[0]] += 1
                    elif case == "source": record["source_kind"] = "surrogate_prediction"
                    elif case == "identity": record["identity"] = {**identity, "seed": 9}
                    else: completed = {}
                    with sqlite3.connect(folder / "evaluations.sqlite") as db:
                        db.execute("UPDATE evaluations SET record_json=?", (json.dumps(record),))
                    with self.assertRaises(ValueError):
                        data._load_saved_role(folder, "train", expected_identity=identity, completed=completed, expected_count=1)

    def test_fixed_training_order_union_and_role_separation(self):
        old = [data.canonical_id(design(i)) for i in range(1024)]
        new = [data.canonical_id(design(i)) for i in range(1024, 1536)]
        reference = [data.canonical_id(design(2000))]; dev = [data.canonical_id(design(3000))]
        t2 = old[:512] + new
        self.assertEqual(len(data._assert_fixed_membership(old, t2, old, new, reference, dev)), 1536)
        with self.assertRaisesRegex(ValueError, "original B1 order"):
            data._assert_fixed_membership(list(reversed(old)), t2, old, new, reference, dev)
        with self.assertRaisesRegex(ValueError, "overlap"):
            data._assert_fixed_membership(old, t2, old, new, reference, [new[0]])
        with self.assertRaisesRegex(ValueError, "overlap"):
            data._assert_fixed_membership(old, t2, old, new, reference, reference)

    def test_inherited_registry_uses_compact_reference_without_mapping_copy(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); registry = data.ExclusionRegistry({"artificial_fixture": True})
            registry.add(design(), original_id="old-other-name", source="fixture", reason="previously_used")
            registry.add_canonical_id_only("d_" + "e" * 24, source="legacy_fixture", reason="X_unavailable")
            registry.sampled_roles = {"train": {"count": 512}, "dev": {"count": 512}}
            registry.save(root / data.OLD_REL / "exclusions_after_development")
            domain = data.PACKAGE_REL / "configs/domain.json"
            write_json(root / domain, registry.domain)
            # This expanded mapping is deliberately unreadable as JSON; loading it would fail.
            (root / data.OLD_REL / "exclusions_after_development/id_mappings.jsonl").write_text("not-json-do-not-load")
            relative = data.OLD_REL / "exclusions_after_development/exclusions.jsonl"
            summary = relative.parent / "summary.json"
            expected = {str(p): data.sha(root / p) for p in (relative, summary, domain)}
            restored, metadata = data.inherited_registry(expected, root)
            self.assertEqual(restored.entries, registry.entries)
            self.assertTrue(restored.contains(design()))
            self.assertEqual(restored.mappings, [])
            self.assertEqual(metadata["missing_X_entries"], 1)
            self.assertEqual(metadata["inherited_mapping_rows_copied"], 0)
            (root / relative).write_text("changed")
            with self.assertRaisesRegex(ValueError, "reference hash"):
                data.inherited_registry(expected, root)

    def test_holdout_guard_rejects_generated_holdout_and_ledger_leak(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); old = root / data.OLD_REL
            write_json(old / "summary/summary.json", {"calibration_status": "not_run", "test_status": "not_run",
                "new_oracle_by_role": {"train": 512, "dev": 512, "calibration": 0, "test": 0}})
            ledger = old / "oracle_queries.jsonl"
            with ledger.open("w") as stream:
                for index in range(1024):
                    role = "train" if index < 512 else "dev"; did = f"d_{index:024x}"
                    stream.write(json.dumps({"event": "reserved", "role": role, "design_id": did}) + "\n")
                    stream.write(json.dumps({"event": "completed", "role": role, "design_id": did, "evaluation_id": f"fixture_{index}"}) + "\n")
            self.assertTrue(data.guard_holdout_isolation(root)["planned_holdout_untouched"])
            leaked = old / "samples/calibration"; leaked.mkdir(parents=True)
            with self.assertRaises(PermissionError): data.guard_holdout_isolation(root)
            leaked.rmdir()
            with ledger.open("a") as stream:
                stream.write(json.dumps({"event": "reserved", "role": "test", "design_id": "d_" + "f" * 24}) + "\n")
            with self.assertRaises(PermissionError): data.guard_holdout_isolation(root)

    def test_manifest_has_fixed_models_predictions_and_no_mutable_or_holdout_scores(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(data, "sha", return_value="fixture_hash"):
            manifest = data.input_manifest(Path(tmp))
        self.assertIn(str(data.OLD_REL / "development/B1/model.joblib"), manifest)
        self.assertIn(str(data.OLD_REL / "development/B2/training_ids.json"), manifest)
        self.assertIn(str(data.OLD_REL / "development/B2/new_dev_predictions.csv"), manifest)
        self.assertFalse(any("EXECUTION_STATUS" in p or "SCOPE" in p or "id_mappings" in p or "evaluation_only" in p for p in manifest))

    def test_holdout_scan_recomputes_alias_X_and_excludes_current_batch(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); row = {**design(), "design_id": data.canonical_id(design())}
            current = root / "reports/local/accuracy_v4_2_001"
            write_json(current / "oracle_queries.jsonl", {"design_id": row["design_id"]})
            self.assertEqual(data.ensure_unseen_holdout_designs([row], root)["matches"], [])
            folder = root / "reports/local/other_experiment"; folder.mkdir()
            with sqlite3.connect(folder / "queried.sqlite") as db:
                db.execute("CREATE TABLE designs(design_id TEXT,design_json TEXT)")
                db.execute("INSERT INTO designs VALUES(?,?)", ("another-ID-same-X", json.dumps(design())))
                db.execute("CREATE TABLE evaluations(secret_unread_target TEXT)")
            with self.assertRaisesRegex(PermissionError, "already appears"):
                data.ensure_unseen_holdout_designs([row], root)


if __name__ == "__main__":
    unittest.main()
