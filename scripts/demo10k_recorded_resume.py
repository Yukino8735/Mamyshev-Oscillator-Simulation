#!/usr/bin/env python3
"""Replay three already queried train records through the existing durable scan.

This is an exact-source cache demonstration, not new labels or solver results.
Only the newly created demonstration STOP is explicitly cleared to resume.
"""
import csv
import hashlib
import json
from pathlib import Path
import sqlite3
import sys

import numpy as np
from scipy.io import loadmat

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports/local/demo_10k_release_001"
sys.path.insert(0, str(ROOT / "src"))
from mamyshev_ml.v4_evaluators import FEATURES, TARGETS, RecordedEvaluator
from mamyshev_ml.v4_scan import make_plan, execute_scan, write_plan
from mamyshev_ml.v4_store import V4Store


def main():
    plan = json.loads((OUT / "matlab_plan/gmmnlse_pending_plan.json").read_text())
    indices = (0, len(plan["designs"]) // 2, len(plan["designs"]) - 1)
    selected = [plan["designs"][index] for index in indices]
    source_path = OUT / "samples/train/evaluations.sqlite"
    source_hash = hashlib.sha256(source_path.read_bytes()).hexdigest()
    with sqlite3.connect(source_path.resolve().as_uri() + "?mode=ro", uri=True) as database:
        records = []
        for row in selected:
            values = database.execute("SELECT record_json FROM evaluations WHERE design_id=? AND job_status='completed'", (row["design_id"],)).fetchall()
            if len(values) != 1:
                raise ValueError("One exact existing training evaluation required for recorded replay")
            record = json.loads(values[0][0])
            if record["identity"]["source"] != "repository_guided_synthetic":
                raise ValueError("This demonstration consumes existing synthetic source only")
            records.append(record)
    if any(record["identity"] != records[0]["identity"] for record in records):
        raise ValueError("Replay must retain identical original source/backend/version/seed/metric identity")
    folder = OUT / "matlab_plan/recorded_resume"
    folder.mkdir(exist_ok=False)
    source = V4Store(folder / "three_saved_records.sqlite")
    destination = V4Store(folder / "resumable_scan.sqlite")
    try:
        for record in records:
            source.save_evaluation(record)
        replay = RecordedEvaluator(source, records[0]["identity"])
        selected_plan = make_plan(method="candidates", designs=[row["design_config"] for row in selected])
        write_plan(selected_plan, folder / "three_row_recorded_replay_plan.json")
        budget = {"max_new_attempts": 3, "total_wall_s": 60}
        stop = folder / "STOP_recorded_replay"
        first = execute_scan(destination, selected_plan, replay, scan_id="saved_train_replay",
                             budget=budget, stop_path=stop, cancel_after=1)
        assert first["status"] == "cancelled" and first["new_attempts"] == 1
        assert destination.db.execute("SELECT count(*) FROM evaluations").fetchone()[0] == 1
        destination.close()
        # Reopen actual on-disk state; this is between-design resume, never a field checkpoint.
        destination = V4Store(folder / "resumable_scan.sqlite")
        stop.unlink()
        second = execute_scan(destination, selected_plan, replay, scan_id="saved_train_replay", budget=budget, stop_path=stop)
        third = execute_scan(destination, selected_plan, replay, scan_id="saved_train_replay", budget=budget, stop_path=stop)
        assert second["status"] == "completed" and second["new_attempts"] == 3
        assert second["spent_wall_s"] >= first["spent_wall_s"]
        assert third["new_attempts_this_invocation"] == 0 and third["new_attempts"] == 3
        paths = destination.export_scan("saved_train_replay", folder / "export")
        mat = loadmat(paths["mat"])
        with Path(paths["csv"]).open(newline="") as stream:
            csv_rows = list(csv.DictReader(stream))
        expected_x = np.array([[record["design"][key] for key in FEATURES] for record in records])
        expected_y = np.array([[record["targets"][key] for key in TARGETS] for record in records])
        assert np.isfinite(mat["X"]).all() and np.isfinite(mat["Y"]).all()
        np.testing.assert_array_equal(mat["X"], expected_x)
        np.testing.assert_array_equal(mat["Y"], expected_y)
        np.testing.assert_allclose(np.array([[float(row[key]) for key in TARGETS] for row in csv_rows]), expected_y, atol=1e-10, rtol=1e-10)
        assert [row["design_id"] for row in csv_rows] == [record["design_id"] for record in records]
        assert all(row["source"] == "repository_guided_synthetic" for row in csv_rows)
        assert len(destination.training_records(source="repository_guided_synthetic", identity=records[0]["identity"])) == 3
        assert len(destination.training_records(source="repaired_original_backend")) == 0
        wrong_identity = dict(records[0]["identity"], seed=-1)
        missing = RecordedEvaluator(source, wrong_identity).evaluate(records[0]["design"])
        assert missing["job_status"] == "not_available" and all(value is None for value in missing["targets"].values())
        assert hashlib.sha256(source_path.read_bytes()).hexdigest() == source_hash
        report = {"kind": "same_source_recorded_cache_replay_no_new_labels", "original_source": records[0]["identity"],
            "recorded_cache_reads": 3, "new_research_labels": 0, "new_real_attempts": 0, "synthetic_formula_calls": 0,
            "selected_zero_based_indices": list(indices), "cancelled": first, "resumed": second, "completed_skip": third,
            "DB_CSV_MAT_readback": "passed", "wrong_identity_no_fallback": "passed", "export_rows": paths["rows"],
            "original_training_db_unchanged": True, "source_db_sha256": source_hash,
            "limitation": "Three same-source saved labels replayed; not 3 new labels, not full GMMNLSE propagation or resume"}
        (folder / "resume_report.json").write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
        print(json.dumps({"recorded_cache_reads": 3, "new_labels": 0, "readback": "passed"}))
    finally:
        source.close(); destination.close()


if __name__ == "__main__":
    main()
