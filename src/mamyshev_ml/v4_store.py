"""SQLite provenance store: evaluations and predictions can never share a label table."""
from __future__ import annotations
import csv
import json
import math
import sqlite3
from pathlib import Path
from .v4_evaluators import FEATURES, TARGETS, canonical, design_id, digest, identity_key, validate_design


class V4Store:
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(self.path)
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA foreign_keys=ON")
        self.db.executescript("""
        CREATE TABLE IF NOT EXISTS designs(design_id TEXT PRIMARY KEY, design_json TEXT NOT NULL UNIQUE);
        CREATE TABLE IF NOT EXISTS evaluations(evaluation_id TEXT PRIMARY KEY, design_id TEXT NOT NULL REFERENCES designs,
          identity_hash TEXT NOT NULL, source TEXT NOT NULL, job_status TEXT NOT NULL, record_json TEXT NOT NULL,
          UNIQUE(design_id,identity_hash,evaluation_id));
        CREATE TABLE IF NOT EXISTS predictions(prediction_id TEXT PRIMARY KEY, design_id TEXT NOT NULL REFERENCES designs,
          model_identity TEXT NOT NULL, record_json TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS attempts(attempt_id TEXT PRIMARY KEY, scan_id TEXT NOT NULL, design_id TEXT NOT NULL REFERENCES designs,
          status TEXT NOT NULL, start_utc TEXT NOT NULL, end_utc TEXT, elapsed_s REAL, record_json TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS scans(scan_id TEXT PRIMARY KEY, plan_hash TEXT NOT NULL, evaluator_identity TEXT NOT NULL,
          budget_json TEXT NOT NULL, authorization_hash TEXT NOT NULL, spent_wall_s REAL NOT NULL DEFAULT 0,
          new_attempts INTEGER NOT NULL DEFAULT 0, status TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS scan_items(scan_id TEXT NOT NULL REFERENCES scans, design_id TEXT NOT NULL REFERENCES designs,
          ordinal INTEGER NOT NULL, status TEXT NOT NULL, evaluation_id TEXT, reason TEXT,
          PRIMARY KEY(scan_id,design_id));
        """)
        self.db.commit()

    def close(self):
        self.db.close()

    def add_design(self, design):
        d = validate_design(design); did = design_id(d)
        with self.db:
            self.db.execute("INSERT OR IGNORE INTO designs VALUES (?,?)", (did, canonical(d)))
        return did

    def save_evaluation(self, record):
        if record.get("kind") != "Evaluation" or record["identity"]["source"] == "surrogate_prediction":
            raise ValueError("Only evaluations enter oracle labels; predictions use the predictions table")
        did = self.add_design(record["design"])
        if did != record["design_id"] or set(record["targets"]) != set(TARGETS):
            raise ValueError("Design or target schema mismatch")
        for value in record["targets"].values():
            if value is not None and (isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value)):
                raise ValueError("Targets must be finite scalar values or explicit null")
        if record["job_status"] != "completed" and any(v is not None for v in record["targets"].values()):
            raise ValueError("Unsuccessful evaluations cannot supply scientific labels")
        eid = record.get("evaluation_id", "e_" + digest(record)[:24])
        stored = dict(record, evaluation_id=eid)
        with self.db:
            row = self.db.execute("SELECT record_json FROM evaluations WHERE evaluation_id=?", (eid,)).fetchone()
            # Cache/logical-event fields are caller accounting, not a new evaluation.
            if row is None:
                self.db.execute("INSERT INTO evaluations VALUES (?,?,?,?,?,?)", (eid, did, identity_key(record["identity"]), record["identity"]["source"], record["job_status"], canonical(stored)))
            elif any(json.loads(row[0]).get(key) != record.get(key) for key in
                     ("design_id", "design", "identity", "job_status", "targets", "units", "artifacts")):
                raise ValueError("Refusing conflicting evaluation identity/value overwrite")
        return eid

    def save_prediction(self, record):
        if record.get("kind") != "Prediction":
            raise ValueError("Prediction record required")
        did = self.add_design(record["design"])
        pid = record["prediction_id"]
        with self.db:
            self.db.execute("INSERT INTO predictions VALUES (?,?,?,?)", (pid, did, canonical(record["model_identity"]), canonical(record)))
        return pid

    def lookup(self, design, identity):
        key = identity_key(identity)
        rows = self.db.execute("SELECT record_json FROM evaluations WHERE design_id=? AND identity_hash=? AND job_status='completed' ORDER BY evaluation_id", (design_id(design), key)).fetchall()
        if not rows:
            return None
        records = [json.loads(row[0]) for row in rows]
        if any(r["targets"] != records[0]["targets"] for r in records[1:]):
            raise ValueError("Multiple exact-identity runs have differing values; explicitly select an evaluation")
        return records[0]

    def training_records(self, *, source, identity=None):
        if not isinstance(source, str) or not source or source == "surrogate_prediction":
            raise ValueError("Explicit non-prediction source filter required")
        sql = "SELECT record_json FROM evaluations WHERE source=? AND job_status='completed'"
        params = [source]
        if identity is not None:
            sql += " AND identity_hash=?"; params.append(identity_key(identity))
        records = [json.loads(row[0]) for row in self.db.execute(sql + " ORDER BY evaluation_id", params)]
        return [r for r in records if all(r["targets"][key] is not None for key in TARGETS)]

    def scan_records(self, scan_id):
        records = []
        for row in self.db.execute("SELECT i.*,d.design_json,e.record_json FROM scan_items i JOIN designs d USING(design_id) LEFT JOIN evaluations e ON e.evaluation_id=i.evaluation_id WHERE i.scan_id=? ORDER BY i.ordinal", (scan_id,)):
            value = dict(row); value["design"] = json.loads(value.pop("design_json"))
            encoded = value.pop("record_json")
            if encoded is None and (value["evaluation_id"] or "").startswith("p_"):
                prediction = self.db.execute("SELECT record_json FROM predictions WHERE prediction_id=?", (value["evaluation_id"],)).fetchone()
                encoded = prediction[0] if prediction else None
            value["evaluation"] = json.loads(encoded) if encoded else None
            records.append(value)
        return records

    def export_scan(self, scan_id, directory):
        import numpy as np
        from scipy.io import savemat
        out = Path(directory); out.mkdir(parents=True, exist_ok=False)
        records = self.scan_records(scan_id)
        rows = []
        for r in records:
            e = r["evaluation"] or {}
            rows.append({"design_id": r["design_id"], **r["design"], "status": r["status"],
                         **{k: e.get("targets", {}).get(k) for k in TARGETS},
                         "source": e.get("identity", {}).get("source", ""),
                         "identity_json": canonical(e.get("identity", {})),
                         "missing_reason": r.get("reason") or e.get("missing_reason", ""),
                         "artifacts_json": canonical(e.get("artifacts", []))})
        columns = ["design_id", *FEATURES, "status", *TARGETS, "source", "identity_json", "missing_reason", "artifacts_json"]
        with (out / "results.csv").open("w", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=columns); writer.writeheader(); writer.writerows(rows)
        X = np.array([[r[k] for k in FEATURES] for r in rows], dtype=float).reshape(-1, 4)
        Y = np.array([[np.nan if r[k] is None else r[k] for k in TARGETS] for r in rows], dtype=float).reshape(-1, 3)
        savemat(out / "results.mat", {"X": X, "Y": Y, "feature_names": FEATURES, "target_names": TARGETS,
                "target_units": ["nJ", "fs", "MW"], "records_json": canonical(rows),
                "missing_values": "NaN denotes missing; see records_json status/reason, never a label"}, do_compression=True)
        return {"csv": str(out / "results.csv"), "mat": str(out / "results.mat"), "rows": len(rows)}
