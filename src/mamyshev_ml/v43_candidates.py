"""One frozen-model candidate application; no fitting, BO or live propagation.

Old excluded data are read through X/ID projections. Only the selected model's
1024 training observations may supply the shared incumbent. New labels belong
to candidate_verification, never to a test, calibration or training role.
"""
from __future__ import annotations

import csv
import json
import math
from pathlib import Path
import re
import sqlite3
import time
from datetime import datetime, timezone

import numpy as np

from .v4_evaluators import ROOT, FEATURES, TARGETS, UNITS, SyntheticEvaluator, design_id, digest, validate_design
from .v4_roles import ReleaseData, SOURCE
from .v4_search import load_candidates, eligible_rows, satisfies, best_actual, export_recommendations, sha256, append_json
from .v4_scan import make_plan, verify_plan, write_plan
from .v4_store import V4Store
from .v41_sampling import _csv_x_rows, _search_x_rows, canonical_id
from .v43_adapter import interval_constraint

SEED = 43043
PER_METHOD = 8
MAX_EVENTS = 64
PACKAGE = Path("mamyshev_accuracy_v4")
V42 = Path("reports/local/accuracy_v4_2_001")
EXPECTED_MODEL = "c236c2d2dd6cb5b59e32bd5ab4f8c3823f7fefc10d7571108a3d6339ee46b2e0"


def _json(path):
    return json.loads(Path(path).read_text())


def _utc():
    return datetime.now(timezone.utc).isoformat()


def synthetic_identity(root=ROOT):
    """Hash source bytes only; never load or inspect the generator to rank X."""
    package = Path(root)/PACKAGE
    return {"source":"repository_guided_synthetic","backend":"mamyshev_repository_guided_synthetic_v3",
        "numerical_version":sha256(package/"reference/oracle.py"),"seed":0,
        "observation_protocol":{"kind":"deterministic_scalar_formula","noise":False},
        "metric_definition":{"plane":"constructed_compressed_scalars","units":UNITS,
                             "recipe_sha256":sha256(package/"configs/generator_recipe.json")}}


def _write(path, value):
    """Exclusive evidence write; never replace a plan or an old result."""
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x") as stream:
        stream.write(json.dumps(value, indent=2, allow_nan=False) + "\n")


def check_scenarios(value):
    scenarios = value["scenarios"]
    wanted = [
        ("S1_peak_under_40fs", "global", {}, {}, TARGETS[2], "maximize", {TARGETS[1]: {"lte": 40}}),
        ("S2_low_pump", "global", {}, {FEATURES[0]: {"lte": 5}}, TARGETS[2], "maximize", {TARGETS[1]: {"lte": 40}}),
        ("S3_fixed_hardware", "fixed_P4_L4", {FEATURES[0]: 4, FEATURES[3]: 4}, {}, TARGETS[2], "maximize", {TARGETS[1]: {"lte": 40}}),
        ("S4_short_pulse", "global", {}, {FEATURES[0]: {"lte": 7}}, TARGETS[1], "minimize", {TARGETS[0]: {"gte": 100}}),
    ]
    actual = [(s["id"], s["candidate_group"], s["fixed_inputs"], s["input_constraints"],
               s["objective"]["target"], s["objective"]["direction"], s["output_constraints"]) for s in scenarios]
    if actual != wanted:
        raise ValueError("Historical scenario definitions differ from the V4.3 instruction; no silent rewrite")
    return scenarios


def project_exclusions(root=ROOT, *, current_output=None):
    """Use recorded evaluated/role X and IDs, excluding pure X-only candidate plans.

    V4.2's holdout exclusion includes all 20000 unevaluated candidate inputs;
    applying that whole set here would incorrectly mark the entire pool queried.
    """
    root = Path(root).resolve(); excluded = set(); sources = []
    def collect(path, kind, rows):
        count = 0; canonical_only = 0
        for original, x in rows:
            if x is None:
                if not re.fullmatch(r"d_[0-9a-f]{24}", str(original)):
                    raise ValueError("Unresolved historical noncanonical ID without X")
                key = original; canonical_only += 1
            else:
                key = canonical_id({k: x[k] for k in FEATURES})
            excluded.add(key); count += 1
        sources.append({"path": str(Path(path).relative_to(root)), "sha256": sha256(path),
                        "kind": kind, "rows": count, "ID_only_rows": canonical_only,
                        "target_columns_selected": False})

    databases = {root/PACKAGE/"data/development.sqlite", root/PACKAGE/"evaluation_only/evaluation.sqlite"}
    databases |= set((root/"reports/local").rglob("*.sqlite")) | set((root/"reports/local").rglob("*.db"))
    for path in sorted(databases):
        if current_output and path.resolve().is_relative_to(Path(current_output).resolve()):
            continue
        with sqlite3.connect(path.resolve().as_uri()+"?mode=ro", uri=True) as db:
            tables = {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            if "designs" not in tables or "evaluations" not in tables:
                raise ValueError("Unrecognized prior database requires X/ID audit: " + str(path))
            columns = {r[1] for r in db.execute("PRAGMA table_info(designs)")}
            if "design_json" in columns:
                # predictions and unexecuted plans do not make an input evaluated.
                sql = "SELECT DISTINCT d.design_id,d.design_json FROM designs d JOIN evaluations e USING(design_id)"
                rows = [(did, json.loads(x)) for did, x in db.execute(sql)]
            elif set(FEATURES) <= columns:
                sql = "SELECT DISTINCT d.design_id,"+",".join("d."+k for k in FEATURES)+" FROM designs d JOIN evaluations e USING(design_id)"
                rows = [(r[0], dict(zip(FEATURES, r[1:]))) for r in db.execute(sql)]
            else:
                raise ValueError("Unknown historical design schema")
        collect(path, "SQLite_X_ID_projection_of_Evaluations", rows)
    for name in ("train_pool_512.csv", "validation_128.csv", "oracle_parity_cases_24.csv"):
        path = root/PACKAGE/"provenance"/name
        collect(path, "legacy_labeled_X_ID_projection", ((did, x) for _, did, x in _csv_x_rows(path)))
    path = root/PACKAGE/"provenance/v3_design_ids.json"
    legacy = _json(path)
    if set(legacy) != {"boundary_test_128.csv", "candidates_unlabeled_20000.csv", "test_256.csv", "train_pool_512.csv", "validation_128.csv"}:
        raise ValueError("Unknown legacy provenance role; resolve before candidate screening")
    collect(path, "legacy_labeled_ID_only_excluding_unlabeled_pool",
            ((did, None) for role, ids in legacy.items() if role != "candidates_unlabeled_20000.csv" for did in ids))
    for path in sorted((root/"reports/local/accuracy_v4_001/search").glob("**/events.jsonl")):
        collect(path, "old_search_X_ID_projection", ((did, x) for _, did, x in _search_x_rows(path)))
    for path in sorted((root/"reports/local").rglob("oracle_queries.jsonl")):
        if current_output and path.resolve().is_relative_to(Path(current_output).resolve()):
            continue
        # The regex reads only the flat design and ID, never oracle targets.
        def ledger_rows():
            for line in path.read_text().splitlines():
                match = re.search(r'"design_id"\s*:\s*("(?:[^"\\]|\\.)*")', line)
                x = re.search(r'"design"\s*:\s*(\{[^{}]*\})', line)
                if not match: raise ValueError("Old query ledger missing canonical identity")
                yield json.loads(match.group(1)), json.loads(x.group(1)) if x else None
        collect(path, "query_reservations_and_completions_X_ID_only", ledger_rows())
    return excluded, {"canonical_exclusions": len(excluded), "sources": sources,
        "target_columns_selected": False, "pure_unlabeled_pool_excluded_as_evaluated": False,
        "scope": "Persisted package labeled roles, archived labeled IDs, old search events and local Evaluation/query ledgers; unrecorded or external queries cannot be established"}


def load_training_incumbents(scenarios, root=ROOT):
    """Read only the frozen T2 train observations, not dev/test/candidate Y."""
    root = Path(root); manifest = _json(root/V42/"release/selection.json")
    ids_path = root/manifest["training_ids_path"]
    if sha256(ids_path) != manifest["training_ids_sha256"]:
        raise ValueError("Frozen T2 training ID hash mismatch")
    ids = _json(ids_path)
    if len(ids) != 1024 or len(set(ids)) != 1024:
        raise ValueError("Expected exactly 1024 distinct T2 training observations")
    if root.resolve() != Path(ROOT).resolve():
        raise ValueError("Real training loader only supports this verified local repository")
    old = ReleaseData().read("train", source_kind=SOURCE, ids=ids[:512])
    relative = "reports/local/accuracy_v4_1_001/samples/train/labels.csv"
    if sha256(root/relative) != manifest["data_hashes"][relative]:
        raise ValueError("Frozen new-half T2 training labels changed")
    with (root/relative).open(newline="") as stream:
        new = list(csv.DictReader(stream))
    if [r["design_id"] for r in new] != ids[512:]:
        raise ValueError("T2 training order mismatch")
    rows = old + [{**r, **{k: float(r[k]) for k in (*FEATURES, *TARGETS)}} for r in new]
    incumbents = {}
    for s in scenarios:
        events = []
        for r in rows:
            if any(r[k] != v for k, v in s["fixed_inputs"].items()) or not satisfies(r, s["input_constraints"]): continue
            targets = {k: r[k] for k in TARGETS}
            if any(not math.isfinite(v) or v <= 0 for v in targets.values()): raise ValueError("Invalid saved training target")
            events.append({"design_id": r["design_id"], "targets": targets, "actual_feasible": satisfies(targets, s["output_constraints"])})
        incumbents[s["id"]] = {**best_actual(events, s), "source": "existing_T2_training_observations_only", "prior_training_design_count": 1024}
    return incumbents


def select_methods(rows, scenario, prediction_targets, *, index, exclusions):
    pool = sorted([r for r in eligible_rows(rows, scenario) if r["design_id"] not in exclusions], key=lambda r:r["design_id"])
    feasible = [r for r in pool if satisfies(prediction_targets[r["design_id"]], scenario["output_constraints"])]
    obj = scenario["objective"]; sign = -1 if obj["direction"] == "maximize" else 1
    ranked = sorted(feasible, key=lambda r:(sign*prediction_targets[r["design_id"]][obj["target"]], r["design_id"]))[:PER_METHOD]
    rng = np.random.default_rng(np.random.SeedSequence([SEED, index]))
    random = [pool[int(i)] for i in rng.choice(len(pool), size=min(PER_METHOD, len(pool)), replace=False)]
    return {"input_feasible_pool_count": len(pool), "predicted_feasible_count": len(feasible),
            "model": [r["design_id"] for r in ranked], "random": [r["design_id"] for r in random]}


def freeze_candidate_plan(*, predictor, output, root=ROOT):
    root = Path(root); out = Path(output)
    if out.exists(): raise FileExistsError("New candidate batch required; no overwrite")
    package = root/PACKAGE; pool_path = package/"data/candidates_unlabeled_20000.csv"
    scenarios_path = package/"configs/scenarios.json"; domain_path = package/"configs/domain.json"
    manifest_path=package/"manifest.json"; published={r["path"]:r["sha256"] for r in _json(manifest_path)["files"]}
    for relative in ("data/candidates_unlabeled_20000.csv","configs/scenarios.json","configs/domain.json",
                     "reference/oracle.py","configs/generator_recipe.json","configs/accuracy_protocol.json"):
        if sha256(package/relative) != published[relative]: raise ValueError("Published package identity mismatch: "+relative)
    scenarios = check_scenarios(_json(scenarios_path)); bounds = _json(domain_path)["bounds"]
    rows = load_candidates(pool_path, bounds)
    if len(rows) != 20000: raise ValueError("The published candidate pool must have 20000 X-only rows")
    for row in rows:
        if design_id({k:row[k] for k in FEATURES}) != row["design_id"]: raise ValueError("Pool canonical ID or legal length grid mismatch")
    exclusions, evidence = project_exclusions(root, current_output=out.parent)
    eligible = [r for r in rows if r["design_id"] not in exclusions]
    designs = [{k:r[k] for k in FEATURES} for r in eligible]
    arrays = predictor.predict_arrays(designs)
    if arrays["targets"].shape != (len(eligible), 3) or not np.isfinite(arrays["targets"]).all():
        raise ValueError("Nonfinite/incomplete pool prediction")
    predictions = {r["design_id"]:dict(zip(TARGETS, map(float, y))) for r,y in zip(eligible, arrays["targets"])}
    choices = {s["id"]: select_methods(rows, s, predictions, index=i, exclusions=exclusions) for i,s in enumerate(scenarios)}
    selected = sorted({did for v in choices.values() for method in ("model", "random") for did in v[method]})
    row_by_id = {r["design_id"]: r for r in eligible}; records = {}
    for did in selected:
        record = predictor.evaluate({k:row_by_id[did][k] for k in FEATURES})
        if record["kind"] != "Prediction" or record["design_id"] != did or record.get("job_status") != "predicted":
            raise ValueError("Selected candidate has no valid Prediction")
        if not np.allclose([record["targets"][k] for k in TARGETS], [predictions[did][k] for k in TARGETS], atol=1e-10, rtol=1e-10):
            raise ValueError("Batch/selected point prediction mismatch")
        interval = record.get("diagnostic_intervals")
        if not interval or interval.get("lower") is None or interval.get("upper") is None:
            raise ValueError("Candidate confirmation requires saved finite diagnostic intervals")
        if any(not math.isfinite(interval[side][k]) or interval[side][k] <= 0 for side in ("lower", "upper") for k in TARGETS):
            raise ValueError("Nonfinite selected diagnostic interval")
        records[did] = record
    incumbent = load_training_incumbents(scenarios, root)
    sources = {s["path"]:s["sha256"] for s in evidence["sources"]}
    for path in (pool_path,scenarios_path,domain_path,package/"reference/oracle.py",package/"configs/generator_recipe.json",
                 manifest_path,package/"configs/accuracy_protocol.json",root/V42/"evaluation/calibration.json",
                 root/V42/"release/model.joblib",root/V42/"release/selection.json",
                 *(root/"src/mamyshev_ml"/name for name in ("v43_candidates.py","v43_adapter.py","v4_evaluators.py",
                                                          "v4_search.py","v4_scan.py","v4_store.py"))):
        sources[str(path.relative_to(root))] = sha256(path)
    if sha256(root/V42/"release/model.joblib") != EXPECTED_MODEL: raise ValueError("Frozen model differs")
    plan = {"schema_version": "v43_frozen_candidate_application_v1", "role": "candidate_verification",
        "frozen_utc":_utc(),"expected_synthetic_identity":synthetic_identity(root),
        "seed": SEED, "random_rule": "Independent SeedSequence([43043, zero_based_scenario_index]); sorted same input-feasible unseen pool; uniform without replacement; no predicted constraint filter",
        "ranking_rule": "Point-predicted feasible, original objective, exact objective ties by canonical ID; no interval gate",
        "adapter_identity": arrays["adapter_identity"],
        "max_logical_events": MAX_EVENTS, "per_method_maximum": PER_METHOD, "model_identity": arrays["model_identity"],
        "sources": sources, "exclusions": evidence, "scenarios": scenarios, "choices": choices,
        "predictions": records, "common_incumbents": incumbent, "prior_model_training_designs": 1024,
        "pool_count": len(rows), "pool_unseen_count": len(eligible), "pool_prediction_rows": len(eligible),
        "unique_predicted_designs": len(eligible),
        "selected_prediction_rows": len(selected), "selected_unique_designs": len(selected),
        "logical_events_planned": sum(len(v[m]) for v in choices.values() for m in ("model","random")),
        "new_training_development_calibration_test_labels": 0, "new_fits": 0, "BO_runs": 0,
        "max_new_real_attempts": 0, "test_reopened": False}
    plan["constraint_diagnostics"]={s["id"]:{did:[interval_constraint(records[did],target,{"lte":"<=","gte":">="}[op],threshold)
        for target,conditions in s["output_constraints"].items() for op,threshold in conditions.items()]
        for did in sorted(set(choices[s["id"]]["model"]+choices[s["id"]]["random"]))} for s in scenarios}
    plan["plan_hash"] = digest(plan)
    out.mkdir(parents=True, exist_ok=False)
    with (out/"pool_predictions.csv").open("x", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=["design_id","candidate_group",*FEATURES,*TARGETS]);writer.writeheader()
        for row in eligible: writer.writerow({**row, **predictions[row["design_id"]]})
    _write(out/"exclusions.json", evidence); _write(out/"frozen_candidate_plan.json", plan)
    return plan


def _validate_plan(plan, root):
    if plan.get("plan_hash") != digest({k:v for k,v in plan.items() if k != "plan_hash"}): raise ValueError("Candidate plan hash mismatch")
    if plan["max_logical_events"] != MAX_EVENTS or plan["seed"] != SEED: raise ValueError("Changed fixed candidate budget/seed")
    for relative, expected in plan["sources"].items():
        if sha256(Path(root)/relative) != expected: raise ValueError("Frozen candidate input/source changed: "+relative)
    if plan.get("schema_version")=="v43_frozen_candidate_application_v1" and plan["expected_synthetic_identity"]!=synthetic_identity(root):
        raise ValueError("Frozen evaluator identity disagrees with current unchanged source bytes")
    check_scenarios({"scenarios":plan["scenarios"]})
    total = 0
    for scenario in plan["scenarios"]:
        for method in ("model","random"):
            ids = plan["choices"][scenario["id"]][method]
            if len(ids)>PER_METHOD or len(set(ids))!=len(ids): raise ValueError("Per-method IDs repeated or over budget")
            if any(did not in plan["predictions"] for did in ids): raise ValueError("Selected prediction missing")
            total += len(ids)
    if total>MAX_EVENTS or total != plan["logical_events_planned"]: raise ValueError("Logical query budget mismatch")


def export_pending_requests(directory, events, scenarios):
    directory = Path(directory); directory.mkdir(parents=True, exist_ok=False)
    requests = export_recommendations(directory, events, scenarios)
    plan = make_plan(method="candidates", designs=[r["design"] for r in requests]); verify_plan(plan)
    write_plan(plan, directory/"candidate_scan_plan.json")
    from .supervisor import validate_live_authorization
    auth = {"authorization_id":"v43_pending_manual_approval", "plan_hash":plan["plan_hash"],
            "allowed_design_ids":[r["design_id"] for r in plan["designs"]], "max_new_attempts":0,
            "per_run_timeout_s":900, "total_wall_limit_s":900, "seed":0, "save_waveforms":True}
    mapping = []
    for row in plan["designs"]:
        actual = validate_live_authorization(plan, auth, row["design_id"])
        if actual != row["design_config"]: raise ValueError("Existing MATLAB four-field mapping changed")
        mapping.append({"design_id":row["design_id"],"design_config":actual,"mapping_valid":True})
    _write(directory/"zero_attempt_authorization.json", auth)
    _write(directory/"request_mapping_check.json", {"status":"pending_manual_approval","mapping":mapping,
        "mapping_count":len(mapping),"MATLAB_starts":0,"max_new_real_attempts":0,"real_targets":None,
        "validation":"existing make_plan -> verify_plan -> validate_live_authorization, pure Python; no execute method called",
        "timeout_fields":"Future draft schema values only; max_new_attempts=0 permits no live task"})
    return requests


def confirm_candidates(plan_path, *, evaluator=None, deadline_s=120, root=ROOT):
    """Exactly one reserved invocation; even a failed/interrupted run cannot retry."""
    path = Path(plan_path); out = path.parent; plan = _json(path); _validate_plan(plan, root)
    _write(out/"candidate_verification.lock", {"plan_hash":plan["plan_hash"],"maximum_logical_queries":MAX_EVENTS,
        "no_automatic_retry":True,"role":"candidate_verification","reserved_utc":_utc()})
    if (out/"events.jsonl").exists() or (out/"candidate_verification.sqlite").exists(): raise FileExistsError("Prior candidate evidence exists")
    evaluator = SyntheticEvaluator(seed=0) if evaluator is None else evaluator
    if getattr(evaluator,"calls",0): raise ValueError("Candidate evaluator must have no prior calls/cache")
    if evaluator.identity != plan["expected_synthetic_identity"]:
        raise ValueError("Candidate evaluator identity does not match the frozen source/recipe/seed")
    store = V4Store(out/"candidate_verification.sqlite"); events=[]; started=time.monotonic()
    protocol = _json(Path(root)/PACKAGE/"configs/accuracy_protocol.json")["tolerances"]
    try:
        for record in plan["predictions"].values(): store.save_prediction(record)
        for scenario in plan["scenarios"]:
            for method in ("model","random"):
                for index,did in enumerate(plan["choices"][scenario["id"]][method],1):
                    if time.monotonic()-started >= deadline_s: raise TimeoutError("Candidate application internal deadline; no retry")
                    if len(events)>=MAX_EVENTS: raise RuntimeError("Logical candidate event cap reached")
                    predicted=plan["predictions"][did]; request_id=f"v43/{scenario['id']}/{method}/{index:02d}"
                    reserved={"event":"reserved","role":"candidate_verification","request_id":request_id,
                              "design_id":did,"design":predicted["design"],"logical_index":len(events)+1,"query_utc":_utc()}
                    append_json(out/"oracle_queries.jsonl",reserved)
                    tick=time.monotonic(); result=None; error=None
                    try:
                        result=evaluator.evaluate(predicted["design"],request_id=request_id,design_id=did)
                        if (result.get("kind")!="Evaluation" or result.get("identity")!=plan["expected_synthetic_identity"]
                                or result.get("source_kind")!=evaluator.identity["source"] or result.get("design_id")!=did
                                or result.get("design")!=predicted["design"] or result.get("units")!=UNITS):
                            raise ValueError("Returned candidate Evaluation source/design/units identity mismatch")
                        y=result.get("targets",{})
                        if result.get("job_status")!="completed" or set(y)!=set(TARGETS) or any(not isinstance(y[k],(float,int)) or isinstance(y[k],bool) or not math.isfinite(y[k]) or y[k]<=0 for k in TARGETS):
                            raise ValueError("Candidate evaluator returned no finite positive completed targets")
                        store.save_evaluation(result)
                    except Exception as exc: error=f"{type(exc).__name__}: {exc}"
                    successful=error is None
                    event={"role":"candidate_verification","request_id":request_id,"scenario_id":scenario["id"],
                        "method":method,"method_index":index,"design_id":did,"design":predicted["design"],
                        "query_utc":reserved["query_utc"],"completed_utc":_utc(),
                        "constraint_diagnostics":plan["constraint_diagnostics"][scenario["id"]][did],
                        "prediction":predicted,"predicted_feasible":satisfies(predicted["targets"],scenario["output_constraints"]),
                        "status":"completed" if successful else "failed","targets":result["targets"] if successful else None,
                        "actual_feasible":satisfies(result["targets"],scenario["output_constraints"]) if successful else False,
                        "cache_hit":bool(result.get("cache_hit")) if result else False,
                        "identity":result.get("identity") if result else getattr(evaluator,"identity",None),
                        "source_kind":result.get("source_kind") if result else None,
                        "evaluation_id":result.get("evaluation_id") if successful else None,
                        "missing_reason":error,"elapsed_s":time.monotonic()-tick}
                    if successful:
                        event["prediction_errors"]={k:{"absolute_error":abs(predicted["targets"][k]-result["targets"][k]),
                            "relative_error":abs(predicted["targets"][k]-result["targets"][k])/abs(result["targets"][k]),
                            "tolerance_pass":abs(predicted["targets"][k]-result["targets"][k])<=max(protocol[k]["absolute"],protocol[k]["relative"]*abs(result["targets"][k]))} for k in TARGETS}
                    else: event["prediction_errors"]=None
                    append_json(out/"events.jsonl",event); events.append(event)
                    append_json(out/"oracle_queries.jsonl",{**reserved,"event":"completed" if successful else "failed","cache_hit":event["cache_hit"],"missing_reason":error})
    except Exception as exc:
        _write(out/"partial_summary.json",{"pipeline_completed":False,"status":"interrupted_or_failed",
            "reason":f"{type(exc).__name__}: {exc}","resolved_logical_events":len(events),
            "evaluator_calls":getattr(evaluator,"calls",None),"unique_oracle_computations":getattr(evaluator,"unique_computations",None),
            "no_retry":True,"events_path":"events.jsonl","lock_retained":True,"elapsed_s":time.monotonic()-started})
        raise
    finally: store.close()
    comparisons=[]
    for scenario in plan["scenarios"]:
        inc=plan["common_incumbents"][scenario["id"]]; obj=scenario["objective"]
        direction=1 if obj["direction"]=="maximize" else -1
        for method in ("model","random"):
            own=[e for e in events if e["scenario_id"]==scenario["id"] and e["method"]==method]
            best=best_actual(own,scenario)
            improved=best["value"] is not None and (inc["value"] is None or direction*best["value"]>direction*inc["value"])
            combined=best if improved else inc
            comparisons.append({"scenario_id":scenario["id"],"method":method,"logical_queries":len(own),
                "actual_feasible":sum(e["actual_feasible"] for e in own),"false_feasible":sum(e["predicted_feasible"] and not e["actual_feasible"] and e["status"]=="completed" for e in own),
                "failures":sum(e["status"]!="completed" for e in own),"cache_hits":sum(e["cache_hit"] for e in own),
                "common_incumbent":inc,"best_newly_evaluated":best,"best_evaluated_on_synthetic":combined,
                "candidate_goal_improved":improved,"not_statistically_significant_comparison":True})
    requests=export_pending_requests(out/"requests",events,plan["scenarios"])
    fields=["scenario_id","method","method_index","design_id",*FEATURES,"status","predicted_feasible","actual_feasible","cache_hit","missing_reason"]
    fields += [k+s for k in TARGETS for s in ("_prediction","_actual","_absolute_error","_tolerance_pass")]
    with (out/"candidate_results.csv").open("x",newline="") as stream:
        writer=csv.DictWriter(stream,fieldnames=fields);writer.writeheader()
        for e in events:
            row={k:e[k] for k in fields if k in e};row.update(e["design"])
            for k in TARGETS:
                row[k+"_prediction"]=e["prediction"]["targets"][k];row[k+"_actual"]=e["targets"][k] if e["targets"] else None
                row[k+"_absolute_error"]=e["prediction_errors"][k]["absolute_error"] if e["prediction_errors"] else None
                row[k+"_tolerance_pass"]=e["prediction_errors"][k]["tolerance_pass"] if e["prediction_errors"] else None
            writer.writerow(row)
    summary={"pipeline_completed":len(events)==plan["logical_events_planned"] and all(e["status"]=="completed" for e in events),
        "candidate_goal_improved":any(r["candidate_goal_improved"] for r in comparisons),"comparisons":comparisons,
        "logical_queries":len(events),"unique_oracle_computations":evaluator.unique_computations,"cache_hits":evaluator.cache_hits,
        "failed_queries":sum(e["status"]!="completed" for e in events),"unique_queried_designs":len({e["design_id"] for e in events}),
        "role":"candidate_verification","test_reopened":False,"new_training_development_calibration_test_labels":0,
        "prior_model_training_designs":1024,"prediction_rows":plan["pool_prediction_rows"]+plan["selected_prediction_rows"],
        "unique_predicted_designs":plan["unique_predicted_designs"],
        "candidate_goal_improved_definition":"Strict objective-direction improvement over the same scenario's feasible T2 training incumbent; absent incumbent may be replaced by a newly evaluated feasible point",
        "requests_exported":len(requests),"MATLAB_starts":0,"max_new_real_attempts":0,"elapsed_s":time.monotonic()-started,
        "physical_state":"undetermined","numerical_validation":"not_verified","eligible_as_validated_training_truth":False}
    _write(out/"candidate_summary.json",summary)
    return summary
