"""X-only synthetic geometry/registry tests. No oracle, target evaluation or fitting."""
import copy
import csv
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from mamyshev_ml import v41_sampling as sampling

DOMAIN = {"bounds": dict(zip(sampling.FEATURES, ([2,10],[2,16],[.5,8],[1,8]))),
          "historical_core": dict(zip(sampling.FEATURES, ([3,7],[4,12],[1,6],[2.5,5.6]))),
          "gain_length_step_m": .1}


def protocol(cap=100000):
    return {"role_quotas": copy.deepcopy(sampling.QUOTAS), "sampling_seeds": sampling.SEEDS.copy(),
            "max_sampling_proposals_per_group": cap}


class TestV41Sampling(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.root = Path(self.tmp.name)
    def tearDown(self): self.tmp.cleanup()

    def test_canonical_X_not_names_controls_duplicate_registry(self):
        registry = sampling.ExclusionRegistry(DOMAIN)
        key, duplicate = registry.add(sampling.ANCHOR, original_id="old_scheme_A", source="a", reason="old_labeled")
        self.assertFalse(duplicate)
        strings = {k: str(v) for k,v in sampling.ANCHOR.items()}
        second, duplicate = registry.add(strings, original_id="new_scheme_B", source="b", reason="candidate")
        self.assertEqual(key, second); self.assertTrue(duplicate); self.assertEqual(len(registry.entries), 1)
        self.assertEqual(registry.entries[key]["original_ids"], ["old_scheme_A","new_scheme_B"])
        # Canonicalization must never snap a supplied length to the grid.
        different = dict(sampling.ANCHOR, gain_length_m=4.01)
        self.assertEqual(sampling.canonical_design(different)["gain_length_m"], 4.01)
        self.assertNotEqual(key, sampling.canonical_id(different))

    def test_legacy_ID_only_excludes_without_fabricating_coordinates(self):
        registry = sampling.ExclusionRegistry(DOMAIN); key=sampling.canonical_id(sampling.ANCHOR)
        registry.add_canonical_id_only(key,source="legacy_missing_X",reason="legacy")
        self.assertTrue(registry.contains(sampling.ANCHOR)); self.assertIsNone(registry.entries[key]["design"])
        self.assertEqual(registry.summary()["canonical_entries_missing_X"], 1)
        with self.assertRaises(ValueError): registry.add_canonical_id_only("different_schema_name",source="x",reason="bad")

    def test_all_role_quotas_geometries_and_global_nonoverlap(self):
        registry = sampling.ExclusionRegistry(DOMAIN); seen=set()
        for role in sampling.QUOTAS:
            rows, rejections = sampling.sample_role(role,sampling.SEEDS[role],registry,protocol())
            self.assertEqual(len(rows),sum(sampling.QUOTAS[role].values()))
            self.assertEqual(dict(sampling.Counter(r["group"] for r in rows)),sampling.QUOTAS[role])
            for row in rows:
                x={k:row[k] for k in sampling.FEATURES}; group=row["group"]
                self.assertNotIn(row["design_id"],seen); seen.add(row["design_id"])
                self.assertEqual(sampling.canonical_id(x),row["design_id"])
                self.assertTrue(all(lo<=x[k]<=hi for k,(lo,hi) in DOMAIN["bounds"].items()))
                self.assertLess(abs(x["gain_length_m"]*10-round(x["gain_length_m"]*10)),1e-9)
                if group=="slice": self.assertEqual((x["pump_power_W"],x["gain_length_m"]),(4.,4.))
                elif group=="near_slice":
                    self.assertTrue(3.5<=x["pump_power_W"]<=4.5 and 3.7<=x["gain_length_m"]<=4.3)
                    self.assertNotEqual((x["pump_power_W"],x["gain_length_m"]),(4.,4.))
                elif group=="outer_faces": self.assertTrue(any(x[k] in bounds for k,bounds in DOMAIN["bounds"].items()))
                elif group=="corners":
                    for k in sampling.FEATURES[:3]:
                        lo,hi=DOMAIN["bounds"][k]; distance=min(x[k]-lo,hi-x[k])
                        self.assertLessEqual(distance,.05*(hi-lo)+.000001)
                    self.assertIn(x["gain_length_m"],[1.,1.1,1.2,1.3,7.7,7.8,7.9,8.])
                elif group=="reference_core": self.assertTrue(sampling.in_core(x,DOMAIN))
                elif group=="reference_expanded": self.assertFalse(sampling.in_core(x,DOMAIN))
                self.assertFalse(any("energy" in k or "duration" in k or "target" in k for k in row))
        self.assertEqual(len(seen),4096)

    def test_determinism_fixed_seeds_and_no_role_reroll(self):
        first=sampling.ExclusionRegistry(DOMAIN); second=sampling.ExclusionRegistry(DOMAIN)
        a,al=sampling.sample_role("dev",41022,first,protocol())
        b,bl=sampling.sample_role("dev",41022,second,protocol())
        self.assertEqual((a,al),(b,bl))
        with self.assertRaises(ValueError): sampling.sample_role("dev",41022,first,protocol())
        with self.assertRaises(ValueError): sampling.sample_role("train",0,second,protocol())
        changed=protocol(); changed["role_quotas"]["train"]["slice"]+=1
        with self.assertRaises(ValueError): sampling.sample_role("train",41011,second,changed)

    def test_collision_logs_and_X_only_proposal_cap_preserve_partial_state(self):
        registry=sampling.ExclusionRegistry(DOMAIN)
        registry.add(sampling.ANCHOR,original_id="previous",source="fixture",reason="existing")
        with patch.object(sampling,"_draw",return_value=sampling.ANCHOR.copy()):
            with self.assertRaisesRegex(RuntimeError,"proposal budget"):
                sampling.sample_role("train",41011,registry,protocol(cap=2))
        self.assertEqual(registry.sampled_roles["train"]["status"],"failed_partial_no_resampling")
        self.assertEqual(registry.sampled_roles["train"]["accepted"],0)
        self.assertEqual(len(registry.rejection_events),2)
        self.assertEqual(registry.sampled_roles["train"]["groups"]["slice"]["proposals"],2)
        with self.assertRaises(ValueError): sampling.sample_role("train",41011,registry,protocol())

    def test_SQL_CSV_search_only_project_X_ID_and_preserve_aliases(self):
        registry=sampling.ExclusionRegistry(DOMAIN)
        csv_path=self.root/"old.csv"
        with csv_path.open("w",newline="") as stream:
            writer=csv.DictWriter(stream,fieldnames=["design_id",*sampling.FEATURES,"target_forbidden"])
            writer.writeheader(); writer.writerow({"design_id":"different_id",**sampling.ANCHOR,"target_forbidden":"not_a_numeric_label"})
        sampling._include_source(registry,{"path":csv_path,"kind":"csv","reason":"old"})
        db_path=self.root/"old.sqlite"
        with sqlite3.connect(db_path) as db:
            db.execute("CREATE TABLE designs(design_id TEXT,design_json TEXT)")
            db.execute("CREATE TABLE evaluations(design_id TEXT,target_forbidden TEXT)")
            db.execute("INSERT INTO designs VALUES (?,?)",("database_other_id",json.dumps(sampling.ANCHOR)))
            db.execute("INSERT INTO evaluations VALUES (?,?)",("database_other_id","do_not_select"))
        sampling._include_source(registry,{"path":db_path,"kind":"sqlite","reason":"old"})
        event_path=self.root/"events.jsonl"
        # Invalid target payload proves the search projection does not decode it.
        event_path.write_text('{"design":'+json.dumps(sampling.ANCHOR)+',"design_id":"search_id","targets": DO_NOT_DECODE}\n')
        sampling._include_source(registry,{"path":event_path,"kind":"search_jsonl","reason":"queried"})
        self.assertEqual(len(registry.entries),1); self.assertEqual(len(registry.mappings),3)
        self.assertTrue(all(not s["target_columns_selected"] for s in registry.sources))
        self.assertNotIn("DO_NOT_DECODE",json.dumps(registry.summary()))

    def test_explicit_legacy_column_mapping_and_conflicting_ID_fail(self):
        path=self.root/"aliases.csv"; names=("P","D","B","L")
        with path.open("w",newline="") as stream:
            writer=csv.writer(stream); writer.writerow(["id",*names]); writer.writerow(["v1-name",4,10,3,4])
        registry=sampling.ExclusionRegistry(DOMAIN)
        sampling._include_source(registry,{"path":path,"kind":"csv","reason":"legacy", "columns":dict(zip(sampling.FEATURES,names))})
        self.assertTrue(registry.contains(sampling.ANCHOR))
        with self.assertRaises(ValueError):
            registry.add(dict(sampling.ANCHOR,pump_power_W=5),original_id="v1-name",source=path,reason="conflict")

    def test_evidence_outputs_refuse_overwrite_and_remain_X_only(self):
        registry=sampling.ExclusionRegistry(DOMAIN)
        rows,logs=sampling.sample_role("train",41011,registry,protocol())
        evidence=sampling.write_role(rows,logs,self.root/"inputs")
        self.assertEqual(evidence["rows"],512)
        self.assertEqual(sampling.sha_file(evidence["inputs"]),evidence["inputs_sha256"])
        with self.assertRaises(FileExistsError): sampling.write_role(rows,logs,self.root/"inputs")
        registry.save(self.root/"registry")
        with self.assertRaises(FileExistsError): registry.save(self.root/"registry")


if __name__=="__main__": unittest.main()
