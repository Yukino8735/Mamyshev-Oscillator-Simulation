"""Engineering tests use only tiny explicitly synthetic scalar evaluations."""
import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/"src"))
from mamyshev_ml.v4_evaluators import SyntheticEvaluator, RecordedEvaluator, SurrogateEvaluator, GMMNLSEEvaluator, validate_design, design_id, identity_key, import_safe_result
from mamyshev_ml.v4_scan import make_plan, verify_plan, execute_scan, read_saved_waveform
from mamyshev_ml.v4_store import V4Store

D = {"pump_power_W":4.,"filter_offset_nm":10.,"filter2_bw_nm":3.,"gain_length_m":4.}


class TestV4DataChain(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.root=Path(self.tmp.name); self.store=V4Store(self.root/"test.sqlite")
    def tearDown(self): self.store.close(); self.tmp.cleanup()
    def plan(self):
        return make_plan(axes={"pump_power_W":[3.,4.,5.]},fixed={k:v for k,v in D.items() if k!="pump_power_W"})
    def test_validation_no_rounding_or_unknown_fields(self):
        for change in ({"gain_length_m":4.01},{"pump_power_W":float("nan")},{"cw2":1030},{"pump_power_W":True}):
            with self.assertRaises(ValueError): validate_design(dict(D,**change))
    def test_synthetic_cache_events_are_not_new_designs(self):
        e=SyntheticEvaluator(); a=e.evaluate(D); b=e.evaluate(D)
        self.assertFalse(a["cache_hit"]); self.assertTrue(b["cache_hit"])
        self.assertEqual((e.calls,e.unique_computations,e.cache_hits),(2,1,1)); self.assertIsNone(a["waveforms"])
    def test_recorded_exact_identity_all_components(self):
        e=SyntheticEvaluator(); record=e.evaluate(D); self.store.save_evaluation(record)
        self.assertEqual(RecordedEvaluator(self.store,e.identity).evaluate(D)["targets"],record["targets"])
        for key in e.identity:
            identity=copy.deepcopy(e.identity); identity[key]="different"
            self.assertEqual(RecordedEvaluator(self.store,identity).evaluate(D)["job_status"],"not_available")
        with self.assertRaises(ValueError): identity_key({"source":"only"})
    def test_prediction_cannot_enter_labels_and_source_required(self):
        class Model:
            def predict(self, X): return [[100.,40.,2.]]
        prediction=SurrogateEvaluator(Model(),{"model_id":"engineering_fixture","sha256":"fixture"}).evaluate(D)
        with self.assertRaises(ValueError): self.store.save_evaluation(prediction)
        self.store.save_prediction(prediction)
        with self.assertRaises(TypeError): self.store.training_records()
        self.assertEqual(self.store.training_records(source="repository_guided_synthetic"),[])
    def test_plan_shapes_dedup_and_hash(self):
        for method in ("lhs","random"):
            p=make_plan(method=method,count=5,seed=11,fixed={}); verify_plan(p); self.assertEqual(p["unique_designs"],5)
        p=make_plan(method="candidates",designs=[D,D]); self.assertEqual(p["duplicates_removed"],1)
        p["designs"][0]["design_config"]["pump_power_W"]=5
        with self.assertRaises(ValueError): verify_plan(p)
    def test_cancel_resume_cumulative_and_completed_skip(self):
        p=self.plan(); e=SyntheticEvaluator(); stop=self.root/"STOP"; budget={"max_new_attempts":3,"total_wall_s":30}
        a=execute_scan(self.store,p,e,scan_id="s",budget=budget,stop_path=stop,cancel_after=1)
        self.assertEqual(a["status"],"cancelled"); self.assertEqual(a["new_attempts"],1); stop.unlink()
        b=execute_scan(self.store,p,e,scan_id="s",budget=budget,stop_path=stop)
        self.assertEqual(b["new_attempts"],3); self.assertGreaterEqual(b["spent_wall_s"],a["spent_wall_s"])
        c=execute_scan(self.store,p,e,scan_id="s",budget=budget,stop_path=stop)
        self.assertEqual(c["new_attempts_this_invocation"],0)
        with self.assertRaises(ValueError): execute_scan(self.store,p,e,scan_id="s",budget={"max_new_attempts":4,"total_wall_s":30},stop_path=stop)
    def test_failed_does_not_retry(self):
        e=SyntheticEvaluator()
        with patch.object(e,"evaluate",side_effect=RuntimeError("explicit component failure")):
            first=execute_scan(self.store,self.plan(),e,scan_id="f",budget={"max_new_attempts":3,"total_wall_s":30},stop_path=self.root/"STOP")
        second=execute_scan(self.store,self.plan(),e,scan_id="f",budget={"max_new_attempts":3,"total_wall_s":30},stop_path=self.root/"STOP")
        self.assertEqual(first["state_counts"],{"failed":3}); self.assertEqual(second["new_attempts_this_invocation"],0)
    def test_unknown_running_refuses_resume(self):
        e=SyntheticEvaluator(); p=self.plan(); stop=self.root/"STOP"; stop.touch()
        execute_scan(self.store,p,e,scan_id="u",budget={"max_new_attempts":3,"total_wall_s":30},stop_path=stop)
        self.store.db.execute("INSERT INTO attempts VALUES (?,?,?,?,?,?,?,?)",("unknown","u",p["designs"][0]["design_id"],"running","now",None,None,"{}")); self.store.db.commit(); stop.unlink()
        with self.assertRaises(RuntimeError): execute_scan(self.store,p,e,scan_id="u",budget={"max_new_attempts":3,"total_wall_s":30},stop_path=stop)
    def test_budget_not_reset_and_missing_targets_export(self):
        p=self.plan(); e=SyntheticEvaluator(); budget={"max_new_attempts":1,"total_wall_s":30}; stop=self.root/"STOP"
        a=execute_scan(self.store,p,e,scan_id="b",budget=budget,stop_path=stop)
        b=execute_scan(self.store,p,e,scan_id="b",budget=budget,stop_path=stop)
        self.assertEqual((a["status"],b["status"]),("budget_stopped","budget_stopped")); self.assertEqual(b["new_attempts"],1)
        paths=self.store.export_scan("b",self.root/"export"); self.assertEqual(paths["rows"],3)
        from scipy.io import loadmat
        import numpy as np
        self.assertTrue(np.isnan(loadmat(paths["mat"])["Y"][1:]).all())

    def parent_fixture(self, status="failed"):
        from mamyshev_ml.supervisor import _blank
        folder=self.root/"parent_fixture"; folder.mkdir()
        expected={"run_id":"parent_fixture","mode":"synthetic_wrapper_component", "seed":0,
                  "source_identity":{"digest":"component_fixture","files":[]},"design_config":D}
        final=_blank(expected); final["job_status"]=status
        runner={"run_id":expected["run_id"],"source_identity":expected["source_identity"],
                "exit_code":0 if status=="completed" else 1,"status":"completed" if status=="completed" else "failed",
                "cleanup_verified":True,"stop_events":[],"stop_reason":"process_exit"}
        final["supervisor"]={"final_writer":"parent_supervisor","runner_record":"runner_record.json",
                             "candidate_valid":status=="completed","required_records_error":None,
                             "exit_code":runner["exit_code"],"stop_events":[]}
        if status=="completed": final["provenance"]["backend_entrypoint"]="component_fixture_not_a_physical_backend"
        for name,record in (("launch_request.json",expected),("runner_record.json",runner),("final_result.json",final)):
            (folder/name).write_text(json.dumps(record))
        return folder,final,runner

    def test_candidate_never_imported_as_parent_and_runner_mismatch_rejected(self):
        folder,final,runner=self.parent_fixture("completed")
        candidate=folder/"matlab_candidate.json"; candidate.write_text(json.dumps(final))
        with self.assertRaises(ValueError): import_safe_result(candidate)
        runner["exit_code"]=9; (folder/"runner_record.json").write_text(json.dumps(runner))
        with self.assertRaises(ValueError): import_safe_result(folder/"final_result.json")

    def test_blank_parent_failure_preserves_unknown_execution_and_null_targets(self):
        folder,final,runner=self.parent_fixture()
        record=import_safe_result(folder/"final_result.json")
        self.assertEqual(record["job_status"],"failed"); self.assertTrue(all(v is None for v in record["targets"].values()))
        self.assertEqual(record["identity"]["backend"]["actual_entrypoint"],"not_observed")
        self.assertEqual(record["identity"]["source"],"synthetic_wrapper_component_fixture")
        self.assertEqual(len(record["artifacts"]),3); self.store.save_evaluation(record)
        self.assertEqual(self.store.training_records(source=record["identity"]["source"]),[])

    def test_manifest_path_escape_rejected_before_read(self):
        folder,final,runner=self.parent_fixture()
        final["waveform_artifacts"]={"manifest_path":"../escaped_manifest.json"}
        (folder/"final_result.json").write_text(json.dumps(final))
        with self.assertRaisesRegex(ValueError,"Unsafe waveform"): import_safe_result(folder/"final_result.json")

    def test_failed_surrogate_stays_out_of_oracle_table_and_finalizes_attempt(self):
        class BrokenModel:
            def predict(self,X): raise RuntimeError("synthetic component prediction failure")
        e=SurrogateEvaluator(BrokenModel(),{"model_id":"broken_fixture","sha256":"fixture"})
        result=execute_scan(self.store,self.plan(),e,scan_id="prediction_failure",budget={"max_new_attempts":3,"total_wall_s":30},stop_path=self.root/"STOP")
        self.assertEqual(result["state_counts"],{"failed":3})
        self.assertEqual(self.store.db.execute("SELECT count(*) FROM evaluations").fetchone()[0],0)
        self.assertEqual(self.store.db.execute("SELECT count(*) FROM predictions").fetchone()[0],3)
        self.assertEqual(self.store.db.execute("SELECT count(*) FROM attempts WHERE status='running'").fetchone()[0],0)

    def test_tighter_scan_budget_refuses_live_before_supervisor(self):
        plan=self.plan(); authorization={"authorization_id":"no_live_fixture","plan_hash":plan["plan_hash"],
            "allowed_design_ids":[r["design_id"] for r in plan["designs"]],"max_new_attempts":0,
            "per_run_timeout_s":1800,"total_wall_limit_s":1800}
        with patch("mamyshev_ml.supervisor.source_identity",return_value={"digest":"fixture"}):
            evaluator=GMMNLSEEvaluator(plan=plan,authorization=authorization,batch_dir=self.root/"unused",execute_real=False)
        with patch("mamyshev_ml.supervisor.execute_authorized_design") as launch:
            with self.assertRaisesRegex(ValueError,"tighter"):
                execute_scan(self.store,plan,evaluator,scan_id="budget_conflict",budget={"max_new_attempts":1,"total_wall_s":60},stop_path=self.root/"STOP",authorization=authorization)
            launch.assert_not_called()
        self.assertEqual(self.store.db.execute("SELECT count(*) FROM attempts").fetchone()[0],0)

    def test_actual_artificial_complex_mat_read_numpy_trapezoid(self):
        import numpy as np
        from scipy.io import savemat
        folder=self.root/"synthetic_mat_fixture"; folder.mkdir()
        t=np.arange(8,dtype=float)*0.25; f=250+(np.arange(8)-4)/(8*0.25)
        field=(np.arange(1,9,dtype=float)*np.exp(1j*np.arange(8)/3))[:,None]
        mat=folder/"waveforms_final.mat"
        savemat(mat,{"t_ps":t[None,:],"f_THz":f[:,None],"output_field":field,
                     "pigtail_output_field":field*2,"compressed_field":field*3})
        manifest=folder/"waveform_manifest.json"
        manifest.write_text(json.dumps({"final":{"path":mat.name}}))
        record={"kind":"Evaluation","run_id":"artificial_mat_not_physical", "waveforms":{
                "manifest":str(manifest),"final":{"path":mat.name}},"waveforms_missing_reason":""}
        # NumPy 2.4 has trapezoid but no trapz; do not eagerly resolve the fallback.
        original_trapezoid=np.trapezoid
        calls=[]
        def traced(*args,**kwargs):
            calls.append(True); return original_trapezoid(*args,**kwargs)
        with patch.object(np,"trapezoid",side_effect=traced):
            result=read_saved_waveform(record,self.root/"mat_read")
        expected=float(original_trapezoid(np.abs(field[:,0])**2,t)/1000)
        self.assertEqual(len(calls),3)
        self.assertAlmostEqual(result["summaries"]["output_field"]["energy_nJ"],expected)
        self.assertAlmostEqual(result["summaries"]["pigtail_output_field"]["energy_nJ"],4*expected)
        self.assertAlmostEqual(result["summaries"]["compressed_field"]["energy_nJ"],9*expected)
        self.assertTrue((self.root/"mat_read/saved_waveforms.png").is_file())
        self.assertEqual(result["new_physical_runs"],0)

    def cli_module(self):
        script=Path(__file__).resolve().parents[1]/"scripts/v4_scan.py"
        spec=importlib.util.spec_from_file_location("v4_scan_cli_component",script)
        module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
        return module

    def test_surrogate_cli_freeze_and_hash_gates_before_pickle_loading(self):
        cli=self.cli_module()
        frozen={"model_family":"component_fixture","n_train":1,"production_order":11,"model_sha256":"verified"}
        with patch("mamyshev_ml.v4_roles.verify_frozen",side_effect=ValueError("freeze rejected")) as gate, patch("joblib.load") as loader:
            with self.assertRaisesRegex(ValueError,"freeze rejected"):
                cli.load_frozen_surrogate(self.root/"model.joblib",self.root/"selection.json")
            gate.assert_called_once(); loader.assert_not_called()
        with patch("mamyshev_ml.v4_roles.verify_frozen",return_value=frozen), patch("joblib.load") as loader:
            with self.assertRaisesRegex(ValueError,"identity"):
                cli.load_frozen_surrogate(self.root/"model.joblib",self.root/"selection.json",{"model_id":"fixture","sha256":"wrong"})
            loader.assert_not_called()

    def test_surrogate_cli_verified_reference_path_precedes_deserialization(self):
        cli=self.cli_module()
        from mamyshev_ml.v4_roles import PACKAGE
        reference=str((PACKAGE/"reference").resolve())
        frozen={"model_family":"component_fixture","n_train":1,"production_order":11,"model_sha256":"verified"}
        original=list(sys.path); events=[]
        class Model:
            def predict(self,X): return [[100.,40.,2.]]
        def verified(*args): events.append("verified"); return frozen
        def loaded(*args):
            self.assertIn(reference,sys.path); self.assertEqual(events,["verified"])
            events.append("loaded"); return Model()
        try:
            sys.path[:]=[p for p in sys.path if p!=reference]
            with patch("mamyshev_ml.v4_roles.verify_frozen",side_effect=verified), patch("joblib.load",side_effect=loaded):
                evaluator=cli.load_frozen_surrogate(self.root/"model.joblib",self.root/"selection.json")
            self.assertEqual(events,["verified","loaded"])
            record=evaluator.evaluate(D)
            self.assertEqual(record["kind"],"Prediction"); self.assertEqual(record["model_identity"]["sha256"],"verified")
        finally:
            sys.path[:]=original


if __name__ == "__main__": unittest.main()
