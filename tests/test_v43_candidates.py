"""Artificial candidate-selection/control fixtures, never a real oracle query."""
import copy
import csv
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from mamyshev_ml import v43_candidates as c


def design(index=0):
    return dict(zip(c.FEATURES,(4.+index/100,10.,3.,4.)))


def scenario_data():
    return c._json(Path(c.ROOT)/c.PACKAGE/"configs/scenarios.json")


def prediction(x):
    did=c.design_id(x); y=dict(zip(c.TARGETS,(120.,30.,3.)))
    identity={"source":"surrogate_prediction","backend":"artificial_component_fixture",
              "numerical_version":"fixture","seed":0,"observation_protocol":{},"metric_definition":c.UNITS}
    return {"kind":"Prediction","prediction_id":"p_fixture_"+did,"design_id":did,"design":x,
            "targets":y,"identity":identity,"model_identity":{"model_id":"artificial_component_fixture","sha256":"fixture"},
            "job_status":"predicted","units":c.UNITS,"diagnostic_intervals":{"status":"artificial_fixture",
            "lower":{k:v*.99 for k,v in y.items()},"upper":{k:v*1.01 for k,v in y.items()},"guaranteed_feasible":False}}


class ArtificialEvaluator:
    """Tagged fabricated values test bookkeeping, never scientific observations."""
    def __init__(self, ledger, *, fail_first=False):
        self.calls=self.unique_computations=self.cache_hits=0;self.cache={};self.ledger=ledger;self.fail_first=fail_first
        self.identity={"source":"artificial_component_fixture","backend":"artificial_component_fixture",
            "numerical_version":"test_only","seed":0,"observation_protocol":{},"metric_definition":c.UNITS}
    def evaluate(self,x,**kwargs):
        self.calls+=1
        latest=json.loads(self.ledger.read_text().splitlines()[-1])
        assert latest["event"]=="reserved" and latest["request_id"]==kwargs["request_id"]
        if self.fail_first and self.calls==1: raise RuntimeError("deliberate artificial failure")
        did=c.design_id(x);hit=did in self.cache
        if hit:self.cache_hits+=1
        else:self.unique_computations+=1;self.cache[did]=True
        return {"kind":"Evaluation","design":x,"design_id":did,"identity":self.identity,
            "source_kind":"artificial_component_fixture","job_status":"completed",
            "targets":dict(zip(c.TARGETS,(121.,30.,3.01))),"units":c.UNITS,"artifacts":[],
            "evaluation_id":"e_fixture_"+did,"cache_hit":hit}


def frozen_fixture(out):
    scenes=c.check_scenarios(scenario_data());p=prediction(design());did=p["design_id"]
    inc={s["id"]:{"design_id":None,"value":None,"targets":None,"missing_reason":"no_artificial_incumbent"} for s in scenes}
    value={"schema_version":"artificial_component_fixture","scenarios":scenes,"seed":c.SEED,"sources":{},
        "max_logical_events":64,"choices":{s["id"]:{"model":[did],"random":[did]} for s in scenes},
        "predictions":{did:p},"logical_events_planned":8,"common_incumbents":inc,
        "pool_prediction_rows":1,"selected_prediction_rows":1,"unique_predicted_designs":1}
    value["expected_synthetic_identity"]=ArtificialEvaluator(out/"oracle_queries.jsonl").identity
    value["constraint_diagnostics"]={s["id"]:{did:[c.interval_constraint(p,k,{"lte":"<=","gte":">="}[op],v)
        for k,conditions in s["output_constraints"].items() for op,v in conditions.items()]} for s in scenes}
    value["plan_hash"]=c.digest(value);path=out/"frozen_candidate_plan.json";c._write(path,value)
    return path,value


class V43CandidateTests(unittest.TestCase):
    def test_scenario_mismatch_is_not_rewritten(self):
        value=scenario_data();self.assertEqual(len(c.check_scenarios(value)),4)
        value["scenarios"][1]["input_constraints"]["pump_power_W"]["lte"]=5.1
        with self.assertRaisesRegex(ValueError,"differ"):
            c.check_scenarios(value)

    def test_selection_ties_exclusions_and_random_ignores_prediction_constraints(self):
        rows=[{"design_id":c.design_id(design(i)),"candidate_group":"global",**design(i)} for i in range(20)]
        targets={r["design_id"]:dict(zip(c.TARGETS,(120.,50.,3.))) for r in rows}
        scenes=scenario_data()["scenarios"];scene=scenes[0]
        for r in rows[:12]:targets[r["design_id"]][c.TARGETS[1]]=30.
        exclusion={rows[0]["design_id"]}
        actual=c.select_methods(rows,scene,targets,index=0,exclusions=exclusion)
        expected=sorted(r["design_id"] for r in rows[1:12])[:8]
        self.assertEqual(actual["model"],expected);self.assertEqual(actual["input_feasible_pool_count"],19)
        self.assertEqual(len(set(actual["random"])),8);self.assertNotIn(rows[0]["design_id"],actual["random"])
        none=copy.deepcopy(targets)
        for y in none.values():y[c.TARGETS[1]]=50.
        second=c.select_methods(rows,scene,none,index=0,exclusions=exclusion)
        self.assertEqual(second["model"],[]);self.assertEqual(second["random"],actual["random"])

    def test_fixed_hardware_and_input_constraints_are_enforced(self):
        scenes=scenario_data()["scenarios"];x=design();bad={**x,"gain_length_m":4.1}
        rows=[{"design_id":c.design_id(v),"candidate_group":"fixed_P4_L4",**v} for v in (x,bad)]
        targets={r["design_id"]:dict(zip(c.TARGETS,(120.,30.,3.))) for r in rows}
        actual=c.select_methods(rows,scenes[2],targets,index=2,exclusions=set())
        self.assertEqual(actual["model"],[c.design_id(x)]);self.assertEqual(actual["random"],[c.design_id(x)])

    def test_all_logical_events_count_while_same_origin_cache_is_shared(self):
        with tempfile.TemporaryDirectory() as tmp:
            out=Path(tmp);path,_=frozen_fixture(out);fake=ArtificialEvaluator(out/"oracle_queries.jsonl")
            with patch.object(c,"SyntheticEvaluator",side_effect=AssertionError("Real oracle forbidden in fixture")):
                result=c.confirm_candidates(path,evaluator=fake)
            self.assertTrue(result["pipeline_completed"]);self.assertEqual(result["logical_queries"],8)
            self.assertEqual(result["unique_oracle_computations"],1);self.assertEqual(result["cache_hits"],7)
            self.assertTrue(result["candidate_goal_improved"])
            with sqlite3.connect(out/"candidate_verification.sqlite") as db:
                self.assertEqual(db.execute("SELECT count(*) FROM evaluations").fetchone()[0],1)
                self.assertEqual(db.execute("SELECT count(*) FROM predictions").fetchone()[0],1)
            self.assertEqual(len((out/"oracle_queries.jsonl").read_text().splitlines()),16)
            with self.assertRaises(FileExistsError):c.confirm_candidates(path,evaluator=fake)

    def test_failed_query_is_charged_and_not_retried_or_given_targets(self):
        with tempfile.TemporaryDirectory() as tmp:
            out=Path(tmp);path,_=frozen_fixture(out);fake=ArtificialEvaluator(out/"oracle_queries.jsonl",fail_first=True)
            result=c.confirm_candidates(path,evaluator=fake)
            self.assertFalse(result["pipeline_completed"]);self.assertEqual(result["logical_queries"],8)
            self.assertEqual(result["failed_queries"],1);self.assertEqual(fake.calls,8)
            first=json.loads((out/"events.jsonl").read_text().splitlines()[0])
            self.assertIsNone(first["targets"]);self.assertIsNone(first["prediction_errors"])
            self.assertEqual(first["status"],"failed")

    def test_plan_tamper_and_budget_changes_fail_before_reservation(self):
        with tempfile.TemporaryDirectory() as tmp:
            out=Path(tmp);path,value=frozen_fixture(out)
            value["max_logical_events"]=65;value["plan_hash"]=c.digest({k:v for k,v in value.items() if k!="plan_hash"})
            path.write_text(json.dumps(value))
            with self.assertRaisesRegex(ValueError,"budget"):
                c.confirm_candidates(path,evaluator=ArtificialEvaluator(out/"oracle_queries.jsonl"))
            self.assertFalse((out/"candidate_verification.lock").exists())

    def test_deadline_preserves_one_shot_lock_without_oracle_call(self):
        with tempfile.TemporaryDirectory() as tmp:
            out=Path(tmp);path,_=frozen_fixture(out);fake=ArtificialEvaluator(out/"oracle_queries.jsonl")
            with self.assertRaises(TimeoutError):c.confirm_candidates(path,evaluator=fake,deadline_s=0)
            self.assertEqual(fake.calls,0);self.assertTrue((out/"candidate_verification.lock").exists())
            self.assertFalse(c._json(out/"partial_summary.json")["pipeline_completed"])

    def test_wrong_evaluator_identity_stops_before_any_query(self):
        with tempfile.TemporaryDirectory() as tmp:
            out=Path(tmp);path,_=frozen_fixture(out);fake=ArtificialEvaluator(out/"oracle_queries.jsonl")
            fake.identity["seed"]=1
            with self.assertRaisesRegex(ValueError,"identity"):
                c.confirm_candidates(path,evaluator=fake)
            self.assertEqual(fake.calls,0);self.assertFalse((out/"oracle_queries.jsonl").exists())

    def test_wrong_returned_identity_cannot_enter_evaluation_table(self):
        with tempfile.TemporaryDirectory() as tmp:
            out=Path(tmp);path,_=frozen_fixture(out);fake=ArtificialEvaluator(out/"oracle_queries.jsonl")
            evaluate=fake.evaluate
            def wrong(*args,**kwargs):
                result=evaluate(*args,**kwargs);result["design_id"]="wrong";return result
            with patch.object(fake,"evaluate",side_effect=wrong):
                result=c.confirm_candidates(path,evaluator=fake)
            self.assertEqual(result["failed_queries"],8);self.assertFalse(result["pipeline_completed"])
            with sqlite3.connect(out/"candidate_verification.sqlite") as db:
                self.assertEqual(db.execute("SELECT count(*) FROM evaluations").fetchone()[0],0)

    def test_interval_crossing_is_uncertain_and_never_authorization(self):
        value=prediction(design());value["diagnostic_intervals"]["lower"][c.TARGETS[1]]=39.9
        value["diagnostic_intervals"]["upper"][c.TARGETS[1]]=40.1
        checked=c.interval_constraint(value,c.TARGETS[1],"<=",40.)
        self.assertEqual(checked["relation"],"uncertain");self.assertFalse(checked["guaranteed_feasible"])
        self.assertTrue(checked["evaluator_confirmation_required"])

    def test_export_keeps_real_targets_null_and_existing_mapping_with_zero_permission(self):
        with tempfile.TemporaryDirectory() as tmp:
            out=Path(tmp);path,_=frozen_fixture(out);c.confirm_candidates(path,evaluator=ArtificialEvaluator(out/"oracle_queries.jsonl"))
            value=c._json(out/"requests/matlab_requests.json")
            self.assertEqual(len(value["requests"]),4)
            for row in value["requests"]:
                self.assertIsNone(row["real_targets"]);self.assertEqual(row["max_new_real_attempts"],0)
                self.assertEqual(row["status"],"pending_manual_approval")
            mapping=c._json(out/"requests/request_mapping_check.json")
            self.assertEqual(mapping["MATLAB_starts"],0);self.assertEqual(mapping["mapping_count"],1)

    def test_exclusions_skip_unlabeled_candidates_and_predictions_without_decoding_y(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);package=root/c.PACKAGE;observed=design();unlabeled=design(1)
            for relative in ("data/development.sqlite","evaluation_only/evaluation.sqlite"):
                path=package/relative;path.parent.mkdir(parents=True,exist_ok=True)
                with sqlite3.connect(path) as db:
                    db.execute("CREATE TABLE designs(design_id TEXT,design_json TEXT)")
                    db.execute("CREATE TABLE evaluations(design_id TEXT,targets TEXT)")
                    for x in (observed,unlabeled):db.execute("INSERT INTO designs VALUES(?,?)",(c.design_id(x),json.dumps(x)))
                    db.execute("INSERT INTO evaluations VALUES(?,?)",(c.design_id(observed),"MALFORMED Y MUST NOT BE DECODED"))
            prov=package/"provenance";prov.mkdir()
            for name in ("train_pool_512.csv","validation_128.csv","oracle_parity_cases_24.csv"):
                with (prov/name).open("w",newline="") as stream:
                    w=csv.DictWriter(stream,fieldnames=["design_id",*c.FEATURES,"forbidden_Y"]);w.writeheader()
                    w.writerow({"design_id":c.design_id(observed),**observed,"forbidden_Y":"not-a-number"})
            roles={k:[] for k in ("boundary_test_128.csv","candidates_unlabeled_20000.csv","test_256.csv","train_pool_512.csv","validation_128.csv")}
            roles["candidates_unlabeled_20000.csv"]=[c.design_id(unlabeled)]
            (prov/"v3_design_ids.json").write_text(json.dumps(roles))
            exclusions,evidence=c.project_exclusions(root)
            self.assertIn(c.design_id(observed),exclusions);self.assertNotIn(c.design_id(unlabeled),exclusions)
            self.assertFalse(evidence["target_columns_selected"])


if __name__=="__main__":unittest.main()
