"""Read-only V4.2 fixed-data identity checks; never invokes an oracle or fits a model."""
from __future__ import annotations

from collections import Counter
import csv
import hashlib
import json
import math
from pathlib import Path
import re
import sqlite3

from .v4_roles import ROOT, FEATURES, TARGETS, SOURCE, BACKEND, ReleaseData
from .v41_sampling import ExclusionRegistry, canonical, canonical_design, canonical_id, QUOTAS

OLD_REL = Path("reports/local/accuracy_v4_1_001")
PACKAGE_REL = Path("mamyshev_accuracy_v4")
AUTHORIZED_OLD_SOURCE_CHANGE = "scripts/run_v4_budget.py"
UNITS = dict(zip(TARGETS, ("nJ", "fs", "MW")))


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for part in iter(lambda: stream.read(1024*1024), b""): digest.update(part)
    return digest.hexdigest()


def _json(path):
    return json.loads(Path(path).read_text())


def _inside(root, relative):
    value = Path(relative)
    if value.is_absolute() or ".." in value.parts:
        raise ValueError("Expected a safe repository-relative historical path")
    path = (Path(root) / value).resolve()
    if not path.is_relative_to(Path(root).resolve()): raise ValueError("Historical reference escapes repository")
    return path


def verify_uploads(root=ROOT):
    root = Path(root)
    checks_path = root / PACKAGE_REL / "UPLOAD_REVIEW_CHECKS.json"
    checks = _json(checks_path)
    mapping = {
        "ACCURACY_V4_1_TARGETED_REPORT.md": "docs/ACCURACY_V4_1_TARGETED_REPORT.md",
        "selection.json": str(OLD_REL / "development/selection.json"),
        "summary.json": str(OLD_REL / "summary/summary.json"),
    }
    if set(checks["inputs"]) != set(mapping): raise ValueError("Uploaded three-file identity schema changed")
    results = {}
    for name, relative in mapping.items():
        actual = sha(root / relative)
        if actual != checks["inputs"][name]: raise ValueError("Uploaded/local identity differs: " + name)
        results[name] = {"path": relative, "sha256": actual, "matches_uploaded": True}
    return {"scope": "Hash agreement with uploaded files; no independent reproduction of V4.1 fits", "files": results}


def input_manifest(root=ROOT):
    """Only fixed inputs/references; no SCOPE, EXECUTION_STATUS or old holdout scores."""
    root = Path(root)
    paths = [
        "docs/ACCURACY_V4_1_TARGETED_REPORT.md", "configs/accuracy_v4_1_protocol.json",
        str(PACKAGE_REL / "CODEX_V4_2_REPRESENTATION_PROMPT.md"),
        str(PACKAGE_REL / "UPLOAD_REVIEW_CHECKS.json"),
        str(PACKAGE_REL / "configs/domain.json"), str(PACKAGE_REL / "configs/accuracy_protocol.json"),
        str(PACKAGE_REL / "data/development.sqlite"), str(PACKAGE_REL / "data/training_orders.json"),
        "reports/local/accuracy_v4_001/models/selection.json",
        str(OLD_REL / "protocol.json"), str(OLD_REL / "development/selection.json"),
        str(OLD_REL / "summary/summary.json"), str(OLD_REL / "oracle_queries.jsonl"),
        str(OLD_REL / "exclusions_after_development/exclusions.jsonl"),
        str(OLD_REL / "exclusions_after_development/summary.json"),
    ]
    for name in ("B1", "B2"):
        paths.extend(str(OLD_REL / "development" / name / file) for file in
            ("model.joblib", "training_ids.json", "metrics.json", "reference_validation_predictions.csv", "new_dev_predictions.csv"))
    for role in ("train", "dev"):
        paths.extend(str(OLD_REL / "samples" / role / file) for file in
            ("inputs.csv", "labels.csv", "evaluations.sqlite", "accounting.json"))
    return {path: sha(_inside(root, path)) for path in paths}


def verify_manifest(expected, root=ROOT):
    actual = input_manifest(root)
    if actual != expected:
        changed = sorted(set(actual) ^ set(expected) | {k for k in set(actual) & set(expected) if actual[k] != expected[k]})
        raise ValueError("Fixed V4.2 inputs changed: " + ", ".join(changed))
    return actual


def verify_old_identity(root=ROOT):
    """Verify old identities without calling V4.1's source-locked execution API."""
    root = Path(root); old = root / OLD_REL; package = root / PACKAGE_REL
    uploads = verify_uploads(root)
    protocol = _json(old / "protocol.json"); selection = _json(old / "development/selection.json")
    summary = _json(old / "summary/summary.json")
    if sha(old / "protocol.json") != sha(root / "configs/accuracy_v4_1_protocol.json"):
        raise ValueError("Original V4.1 shared/local protocol differs")
    if not selection.get("frozen") or selection.get("selected") is not None or selection.get("development_accuracy_target_met") is not False:
        raise ValueError("Expected the preserved V4.1 no-selection outcome")
    if selection["protocol_sha256"] != sha(old / "protocol.json") or selection["sources"] != protocol["sources"]:
        raise ValueError("V4.1 selection/protocol identity disagreement")
    authorized_changes = []
    for relative, expected in protocol["sources"].items():
        actual = sha(_inside(root, relative))
        if actual != expected:
            if relative != AUTHORIZED_OLD_SOURCE_CHANGE:
                raise ValueError("Old frozen source unexpectedly changed: " + relative)
            authorized_changes.append({"path": relative, "old_sha256": expected, "current_sha256": actual,
                "reason": "V4.2 explicitly permits the existing budget wrapper's new batch choice; root reviews its diff separately"})
    for relative, expected in protocol["unchanged_package_hashes"].items():
        if sha(_inside(package, relative)) != expected: raise ValueError("Old package identity changed: " + relative)
    old_selection_path = root / "reports/local/accuracy_v4_001/models/selection.json"
    if sha(old_selection_path) != protocol["old_selection_sha256"]:
        raise ValueError("Original V4 selection changed")
    old_selection = _json(old_selection_path)
    for relative in ("data/development.sqlite", "data/training_orders.json", "configs/domain.json"):
        if sha(package / relative) != old_selection["split_hashes"][relative]:
            raise ValueError("Original development data identity changed: " + relative)
    models = {}
    for name in ("B1", "B2"):
        matches = [v for v in selection["candidates"] if v["name"] == name]
        if len(matches) != 1: raise ValueError("Missing or ambiguous old baseline " + name)
        candidate = matches[0]; expected_relative = OLD_REL / "development" / name / "model.joblib"
        if Path(candidate["model_path"]) != expected_relative or candidate["n"] != 1024:
            raise ValueError("Old baseline model/path/count mismatch: " + name)
        model_path = _inside(root, candidate["model_path"])
        if sha(model_path) != candidate["model_sha256"]:
            raise ValueError("Missing/changed baseline weights; do not refit " + name)
        models[name] = {"path": str(model_path), "relative_path": candidate["model_path"],
                        "sha256": candidate["model_sha256"], "n_train": 1024,
                        "training_ids": str(old / "development" / name / "training_ids.json"),
                        "reference_predictions": str(old / "development" / name / "reference_validation_predictions.csv"),
                        "dev_predictions": str(old / "development" / name / "new_dev_predictions.csv"),
                        "retrain_authorized": False}
    return {"uploads": uploads, "protocol": protocol, "selection": selection, "summary": summary,
            "models": models, "authorized_old_source_changes": authorized_changes}


def guard_holdout_isolation(root=ROOT, additional_roots=()):
    """Inspect only V4.1 new-role paths and query ledger, not V4 holdout labels/scores."""
    root = Path(root); old = root / OLD_REL
    roots = [old, *(Path(p) for p in additional_roots)]
    for base in roots:
        forbidden = [base / "samples/calibration", base / "samples/test", base / "evaluation",
                     base / "final_evaluation.lock", base / "calibration", base / "test"]
        if any(path.exists() for path in forbidden):
            raise PermissionError("V4.1 planned holdout may already have been generated/evaluated: " + str(base))
        sample_dir = base / "samples"
        if sample_dir.exists() and any(path.is_dir() and path.name not in ("train", "dev") for path in sample_dir.iterdir()):
            raise PermissionError("Unknown prior sample role requires an isolation audit")
    summary = _json(old / "summary/summary.json")
    if any(summary.get(key) != "not_run" for key in ("calibration_status", "test_status")):
        raise PermissionError("Historical summary does not establish unopened planned holdout")
    if any(summary.get("new_oracle_by_role", {}).get(role) != 0 for role in ("calibration", "test")):
        raise PermissionError("Historical summary contains holdout queries")
    reservations, completed = {}, {}
    with (old / "oracle_queries.jsonl").open() as stream:
        for line in stream:
            event = json.loads(line); role, did = event.get("role"), event.get("design_id")
            if role not in ("train", "dev") or event.get("event") not in ("reserved", "completed"):
                raise PermissionError("Unexpected/holdout event in V4.1 query ledger")
            if event["event"] == "reserved":
                if did in reservations: raise ValueError("Repeated old reservation")
                reservations[did] = role
            else:
                if did in completed or reservations.get(did) != role: raise ValueError("Old query completion has no unique matching reservation")
                completed[did] = {"role": role, "evaluation_id": event["evaluation_id"]}
    if set(reservations) != set(completed) or Counter(reservations.values()) != Counter({"train": 512, "dev": 512}):
        raise ValueError("V4.1 query ledger is incomplete or not the fixed train/dev allocation")
    return {"planned_holdout_untouched": True, "checked_roots": [str(p) for p in roots],
            "old_query_counts": dict(Counter(reservations.values())), "completed": completed,
            "old_V4_holdout_labels_or_scores_read": False}


def _read_role_csv(path, role, targets):
    with Path(path).open(newline="") as stream:
        rows = list(csv.DictReader(stream))
    seen = set()
    for index, row in enumerate(rows, 1):
        if row.get("role") != role or int(row["order_in_role"]) != index:
            raise ValueError("Saved role/order differs from its fixed original ordering")
        for name in (*FEATURES, *(TARGETS if targets else ())):
            row[name] = float(row[name])
            if not math.isfinite(row[name]) or (name in TARGETS and row[name] <= 0):
                raise ValueError("Nonfinite/nonpositive saved scalar")
        x = {k: row[k] for k in FEATURES}; did = row["design_id"]
        if canonical_id(x) != did or did in seen: raise ValueError("Role contains duplicated/mismatched canonical X")
        seen.add(did); row["order_in_role"] = index
        if targets and (row.get("source_kind") != SOURCE or row.get("region") != row["group"]):
            raise ValueError("Saved CSV source/group mismatch")
    return rows


def _load_saved_role(folder, role, *, expected_identity, completed, expected_count=512):
    folder = Path(folder)
    labels = _read_role_csv(folder / "labels.csv", role, True)
    inputs = _read_role_csv(folder / "inputs.csv", role, False)
    if len(labels) != expected_count or len(inputs) != expected_count:
        raise ValueError("Fixed saved role count mismatch")
    for row, xrow in zip(labels, inputs):
        if any(row.get(k) != xrow.get(k) for k in ("design_id", "role", "group", "order_in_role", *FEATURES)):
            raise ValueError("Labels/inputs CSV X, ID, group or ordering mismatch")
    accounting = _json(folder / "accounting.json")
    if accounting["role"] != role or accounting["identity"] != expected_identity or any(accounting[k] != expected_count for k in ("new_labels", "oracle_calls", "unique_computations")) or accounting["cache_hits"] != 0:
        raise ValueError("Saved role accounting/source identity mismatch")
    identity_hash = hashlib.sha256(canonical(expected_identity).encode()).hexdigest()
    sql = """SELECT d.design_id,d.design_json,e.evaluation_id,e.identity_hash,e.source,e.job_status,e.record_json
             FROM designs d JOIN evaluations e ON e.design_id=d.design_id ORDER BY d.design_id"""
    with sqlite3.connect((folder / "evaluations.sqlite").resolve().as_uri() + "?mode=ro", uri=True) as db:
        records = list(db.execute(sql))
    by_id = {}
    for did, xjson, eid, ihash, source, status, encoded in records:
        record = json.loads(encoded); x = json.loads(xjson)
        if did in by_id or did != canonical_id(x) or ihash != identity_hash or source != SOURCE or status != "completed":
            raise ValueError("SQLite design/status/source identity mismatch")
        if record.get("kind") != "Evaluation" or record.get("design_id") != did or record.get("design") != x or record.get("identity") != expected_identity or record.get("source_kind") != SOURCE or record.get("job_status") != "completed" or record.get("units") != UNITS:
            raise ValueError("SQLite evaluation provenance mismatch")
        if record.get("request_id") != f"v41/{role}/{did}" or record.get("evaluation_id") != eid or record.get("cache_hit") is not False:
            raise ValueError("SQLite original query identity mismatch")
        if completed.get(did) != {"role": role, "evaluation_id": eid}:
            raise ValueError("SQLite and historical query ledger differ")
        by_id[did] = (x, record["targets"])
    if set(by_id) != {r["design_id"] for r in labels}: raise ValueError("CSV/SQLite role membership mismatch")
    for row in labels:
        x, y = by_id[row["design_id"]]
        if x != {k: row[k] for k in FEATURES} or y != {k: row[k] for k in TARGETS}:
            raise ValueError("CSV/SQLite input or target values differ; no oracle fallback")
    return labels


def _assert_canonical_rows(rows, role):
    ids = []
    for row in rows:
        if row.get("source_kind") != SOURCE or canonical_id({k: row[k] for k in FEATURES}) != row["design_id"]:
            raise ValueError("Old/new data source or canonical identity mismatch: " + role)
        if any(not math.isfinite(row[k]) or row[k] <= 0 for k in TARGETS): raise ValueError("Invalid saved targets")
        ids.append(row["design_id"])
    if len(ids) != len(set(ids)): raise ValueError("Duplicate canonical design in " + role)
    return ids


def _assert_fixed_membership(t1_ids, t2_ids, old_ids, new_ids, reference_ids, dev_ids):
    if len(t1_ids) != 1024 or t1_ids != old_ids[:1024]: raise ValueError("T1 differs from original B1 order11 prefix")
    if len(t2_ids) != 1024 or t2_ids != old_ids[:512] + new_ids: raise ValueError("T2 differs from original B2 row ordering")
    union = set(t1_ids) | set(t2_ids)
    if len(union) != 1536 or len(set(t1_ids)) != 1024 or len(set(t2_ids)) != 1024:
        raise ValueError("Expected 1536 unique canonical training designs across two 1024-design sets")
    if union & (set(reference_ids) | set(dev_ids)) or set(reference_ids) & set(dev_ids):
        raise ValueError("Training/reference/dev canonical design overlap")
    return union


def load_data(root=ROOT, expected_manifest=None):
    root = Path(root); old = root / OLD_REL; package = root / PACKAGE_REL
    manifest = verify_manifest(expected_manifest, root) if expected_manifest is not None else input_manifest(root)
    identity = verify_old_identity(root); isolation = guard_holdout_isolation(root)
    p = identity["protocol"]
    expected_identity = {"source": SOURCE, "backend": BACKEND,
        "numerical_version": p["unchanged_package_hashes"]["reference/oracle.py"], "seed": p["oracle_seed"],
        "observation_protocol": {"kind": "deterministic_scalar_formula", "noise": False},
        "metric_definition": {"plane": "constructed_compressed_scalars", "units": UNITS,
                              "recipe_sha256": p["unchanged_package_hashes"]["configs/generator_recipe.json"]}}
    new = _load_saved_role(old / "samples/train", "train", expected_identity=expected_identity, completed=isolation["completed"])
    dev = _load_saved_role(old / "samples/dev", "dev", expected_identity=expected_identity, completed=isolation["completed"])
    for role, rows in (("train", new), ("dev", dev)):
        if Counter(r["group"] for r in rows) != Counter(QUOTAS[role]): raise ValueError("Saved group allocation changed")
    orders = _json(package / "data/training_orders.json")["orders"]["11"]
    loader = ReleaseData()
    loader.path = package / "data/development.sqlite"  # Remains the guarded development-only DB.
    old_rows = loader.read("train", source_kind=SOURCE, ids=orders[:1024])
    reference = loader.read("validation", source_kind=SOURCE)
    if len(reference) != 1024 or Counter(r["region"] for r in reference) != Counter({"historical_core":512,"expanded_proposal":512}):
        raise ValueError("Fixed reference validation count/group allocation mismatch")
    lookup = {r["design_id"]: r for r in old_rows + new}
    if len(lookup) != 1536: raise ValueError("Old and new training sets have unexpected canonical overlap")
    t1_ids = _json(old / "development/B1/training_ids.json"); t2_ids = _json(old / "development/B2/training_ids.json")
    for role, rows in (("old_train", old_rows), ("new_train", new), ("reference", reference), ("dev", dev)):
        _assert_canonical_rows(rows, role)
    union = _assert_fixed_membership(t1_ids, t2_ids, orders, [r["design_id"] for r in new],
        [r["design_id"] for r in reference], [r["design_id"] for r in dev])
    t1, t2 = [lookup[k] for k in t1_ids], [lookup[k] for k in t2_ids]
    metadata = {"input_manifest": manifest, "uploads": identity["uploads"], "models": identity["models"],
        "authorized_old_source_changes": identity["authorized_old_source_changes"],
        "training_sizes": {"T1":len(t1),"T2":len(t2)}, "unique_training_union":len(union),
        "training_union_ids_sha256":hashlib.sha256(canonical(sorted(union)).encode()).hexdigest(),
        "ordered_ids_sha256": {name:hashlib.sha256(canonical(ids).encode()).hexdigest() for name,ids in (("T1",t1_ids),("T2",t2_ids))},
        "csv_sql_cross_validation": {"train":512,"dev":512,"value_comparison":"exact saved float equality; no oracle calls"},
        "holdout_isolation": {k:v for k,v in isolation.items() if k!="completed"},
        "development_roles_previously_used":True,"old_data_accesses":loader.accesses,
        "new_training_labels":0,"new_development_labels":0,"oracle_calls":0,"models_loaded":False}
    return {"T1":t1,"T2":t2,"reference":reference,"dev":dev,"metadata":metadata}


def inherited_registry(expected_manifest=None, root=ROOT):
    """Restore the compact exclusion set by reference, without the 67 MB mapping log.

    `registry.mappings` starts empty and contains only future incremental entries.
    Do not call registry.save to duplicate the inherited set; preserve the returned
    reference metadata and save only new mappings/rejection events in this batch.
    """
    if expected_manifest is None: raise ValueError("The new frozen input manifest is required before inheriting exclusions")
    root=Path(root); relative=OLD_REL/"exclusions_after_development/exclusions.jsonl"
    summary_relative=OLD_REL/"exclusions_after_development/summary.json"
    domain_relative=PACKAGE_REL/"configs/domain.json"
    for name in (relative,summary_relative,domain_relative):
        if str(name) not in expected_manifest or sha(root/name)!=expected_manifest[str(name)]:
            raise ValueError("Inherited exclusion/domain reference hash mismatch")
    summary=_json(root/summary_relative); registry=ExclusionRegistry(_json(root/domain_relative))
    with (root/relative).open() as stream:
        for line in stream:
            entry=json.loads(line); key=entry["canonical_id"]; design=entry["design"]
            if not re.fullmatch(r"d_[0-9a-f]{24}",key) or key in registry.entries:
                raise ValueError("Malformed/duplicate inherited canonical ID")
            if design is not None and canonical_id(design)!=key: raise ValueError("Inherited X/ID mismatch")
            if any(not isinstance(entry[k],list) or not all(isinstance(v,str) for v in entry[k]) for k in ("original_ids","reasons","sources")):
                raise ValueError("Malformed inherited alias/provenance metadata")
            registry.entries[key]=entry
    if len(registry.entries)!=summary["canonical_exclusions"] or sum(v["design"] is None for v in registry.entries.values())!=summary["canonical_entries_missing_X"]:
        raise ValueError("Inherited exclusion counts differ from original summary")
    if set(summary["sampled_roles"]) != {"train", "dev"}:
        raise PermissionError("Inherited sampling state is not the preserved train/dev-only snapshot")
    registry.sampled_roles=dict(summary["sampled_roles"])
    metadata={"path":str(root/relative),"sha256":expected_manifest[str(relative)],
        "summary_path":str(root/summary_relative),"summary_sha256":expected_manifest[str(summary_relative)],
        "inherited_canonical_entries":len(registry.entries),"missing_X_entries":summary["canonical_entries_missing_X"],
        "original_mapping_rows_not_loaded":summary["source_mapping_rows"],"inherited_mapping_rows_copied":0,
        "incremental_mapping_rows_initial":0,"holdout_labels_read":False}
    registry.sources=[{"kind":"inherited_X_ID_reference","path":metadata["path"],"sha256":metadata["sha256"],"target_columns_selected":False}]
    return registry,metadata


def ensure_unseen_holdout_designs(rows, root=ROOT):
    """Fail closed on X/ID matches in this repository's other persisted queries.

    This is an additional, just-before-query check. The frozen inherited registry
    remains authoritative for historic release/search/candidate exclusions. Only
    identifiers and design columns are selected from SQLite; no target table or
    old test score is read. The current batch is excluded because its shared
    registry checks calibration/test mutual exclusion before this call.
    """
    root = Path(root).resolve()
    current = root / "reports/local/accuracy_v4_2_001"
    local = root / "reports/local"
    wanted = set()
    for row in rows:
        key = canonical_id({k: row[k] for k in FEATURES})
        if row.get("design_id") != key or key in wanted:
            raise ValueError("Planned holdout contains a mismatched or repeated canonical design")
        wanted.add(key)
    sources, matches = [], []

    def outside_current(path):
        resolved = path.resolve()
        if not resolved.is_relative_to(root):
            raise PermissionError("Persisted query evidence escapes this repository")
        return not resolved.is_relative_to(current)

    def inspect(original_id, design, path):
        if design is None:
            key = str(original_id)
            if not re.fullmatch(r"d_[0-9a-f]{24}", key):
                raise PermissionError("Noncanonical query ID without X prevents an isolation check: " + str(path))
        else:
            key = canonical_id({k: design[k] for k in FEATURES})
        if key in wanted:
            matches.append({"canonical_id": key, "original_id": original_id,
                            "path": str(path.relative_to(root))})

    for path in sorted(local.rglob("oracle_queries.jsonl")):
        if not outside_current(path): continue
        count = 0
        with path.open() as stream:
            for line in stream:
                event = json.loads(line)
                inspect(event.get("design_id"), event.get("design"), path)
                count += 1
        sources.append({"path": str(path.relative_to(root)), "kind": "query_ledger_ID_X_only", "rows": count})
    databases = set(local.rglob("*.sqlite")) | set(local.rglob("*.db"))
    for path in sorted(databases):
        if not outside_current(path): continue
        count = 0
        with sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True) as db:
            tables = {row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            if "designs" not in tables:
                raise PermissionError("Unrecognized local database requires an X-only isolation audit: " + str(path))
            columns = {row[1] for row in db.execute("PRAGMA table_info(designs)")}
            if {"design_id", "design_json"}.issubset(columns):
                for did, encoded in db.execute("SELECT design_id,design_json FROM designs"):
                    inspect(did, json.loads(encoded), path); count += 1
            elif {"design_id", *FEATURES}.issubset(columns):
                sql = 'SELECT design_id,' + ','.join(FEATURES) + ' FROM designs'
                for row in db.execute(sql):
                    inspect(row[0], dict(zip(FEATURES, row[1:])), path); count += 1
            else:
                raise PermissionError("Local design table lacks canonical X/ID schema: " + str(path))
        sources.append({"path": str(path.relative_to(root)), "kind": "SQLite_design_X_ID_only", "rows": count})
    if matches:
        raise PermissionError("Planned holdout already appears in persisted local query/design evidence: " + canonical(matches))
    return {"planned_designs_checked": len(wanted), "matches": [], "sources": sources,
            "scope": "Recorded oracle ledgers and SQLite design tables under this repository reports/local; earlier release/search/candidate identities remain covered by the frozen inherited exclusions. Unrecorded or external queries cannot be established.",
            "excluded_current_batch": str(current.relative_to(root)), "target_columns_selected": False,
            "old_holdout_scores_read": False, "seed_changed": False}
