"""Frozen legacy identity checks; no environment changes or physical runs."""
import hashlib
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
SAVED = ROOT / "reports/local/phase1/baseline_001/configuration.json"


class LegacyIdentityTest(unittest.TestCase):
    def setUp(self):
        self.identity = json.loads((ROOT / "configs/legacy_physics_identity.json").read_text())

    def test_physical_derivation_sources_unchanged(self):
        evidence = self.identity["evidence"]
        loader = ROOT / evidence["loader"]
        self.assertEqual(hashlib.sha256(loader.read_bytes()).hexdigest(), evidence["loader_sha256"])
        section = self.identity["preserved_physical_rules"]["cross_section_source"]
        self.assertEqual(hashlib.sha256((ROOT / section["path"]).read_bytes()).hexdigest(), section["sha256"])
        self.assertFalse(self.identity["passive_fiber"]["declaration_is_verified_device_parameter"])
        self.assertFalse(self.identity["passive_fiber"]["diagnostic_counterfactual_only"]["applied_to_production"])

    @unittest.skipUnless(SAVED.exists(), "Private Phase 1 snapshot not present; historical cross-check not executed")
    def test_identity_matches_actual_phase1_resolved_parameters(self):
        saved = json.loads(SAVED.read_text())
        passive = self.identity["passive_fiber"]
        gain = self.identity["gain_fiber"]
        for segment in saved["fiber_cavity"][1:]:
            self.assertEqual(segment["MFD"], passive["declared_MFD_um"])
            self.assertEqual(segment["SR"], passive["SR_per_m2"])
            self.assertEqual(segment["gain_Aeff"], passive["gain_Aeff_m2"])
        for old, new in [("MFD", "MFD_um"), ("SR", "SR_per_m2"), ("gain_Aeff", "gain_Aeff_m2")]:
            self.assertEqual(saved["fiber_cavity"][0][old], gain[new])
        self.assertEqual([v["L0"] for v in saved["fiber_cavity"]],
                         [v["length_m"] for v in self.identity["preserved_physical_rules"]["cavity_segments"]])


if __name__ == "__main__":
    unittest.main()
