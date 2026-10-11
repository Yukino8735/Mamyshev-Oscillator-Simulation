"""Targeted protocol/sampling/gate components; no labels or model fitting."""
import copy
import json
from pathlib import Path
import tempfile
import unittest

import numpy as np

from mamyshev_ml.demo10k_experiment import (CONFIG, PACKAGE, FEATURES, GROUPS, ROLES,
    validate_protocol, sample_rows, exclusive, score, canonical_id)


class Demo10kProtocolTests(unittest.TestCase):
    def setUp(self):
        self.p = json.loads(CONFIG.read_text())
        self.domain = json.loads((PACKAGE / "configs/domain.json").read_text())

    def test_fixed_counts_and_single_fit(self):
        p = validate_protocol(self.p)
        self.assertEqual(sum(sum(p["role_quotas"][r].values()) for r in ROLES), 14096)
        self.assertEqual(sum(p["role_quotas"]["train"].values()), 10000)
        self.assertEqual(p["formal_three_target_fit_attempts_max"], 1)

    def test_changed_hyperparameter_and_split_rejected(self):
        for location, key, value in (("parameters", "alpha", .1), ("sampling_seeds", "train", 1)):
            p = copy.deepcopy(self.p); p[location][key] = value
            with self.assertRaises(ValueError): validate_protocol(p)

    def test_x_only_fixture_geometry_and_cross_role_exclusion(self):
        # Fixture quotas only exercise the sampler, not the authorized runner.
        p = copy.deepcopy(self.p)
        for role in ROLES: p["role_quotas"][role] = dict.fromkeys(GROUPS, 3)
        excluded = set(); seen = set()
        for role in ROLES:
            rows, _ = sample_rows(role, p, excluded, self.domain)
            self.assertEqual(len(rows), 18)
            ids = {r["design_id"] for r in rows}
            self.assertFalse(ids & seen); seen |= ids
            for row in rows:
                self.assertEqual(row["design_id"], canonical_id({k: row[k] for k in FEATURES}))
                self.assertAlmostEqual(row["gain_length_m"] * 10, round(row["gain_length_m"] * 10))
                self.assertFalse(any(k.startswith("compressed_") for k in row))
                if row["group"] == "slice":
                    self.assertEqual((row["pump_power_W"], row["gain_length_m"]), (4, 4))
        self.assertEqual(len(seen), 72)

    def test_deterministic_x_stream_and_collision_retained(self):
        p = copy.deepcopy(self.p); p["role_quotas"]["train"] = dict.fromkeys(GROUPS, 2)
        first, _ = sample_rows("train", p, set(), self.domain)
        same, _ = sample_rows("train", p, set(), self.domain)
        self.assertEqual(first, same)
        forbidden = {first[0]["design_id"]}
        other, rejected = sample_rows("train", p, forbidden, self.domain)
        self.assertNotIn(first[0]["design_id"], {r["design_id"] for r in other})
        self.assertTrue(any(r["reason"] == "existing_X_or_ID" for r in rejected))

    def test_exclusive_reservation_rejects_second_attempt(self):
        with tempfile.TemporaryDirectory() as name:
            path = Path(name) / "fit.lock"
            exclusive(path, {"attempt": 1})
            with self.assertRaises(FileExistsError): exclusive(path, {"attempt": 2})
            self.assertEqual(json.loads(path.read_text()), {"attempt": 1})

    def test_exact_synthetic_metric_fixture_gate(self):
        from mamyshev_ml.v4_ml import protocol
        rows = [{"group": group} for group in GROUPS for _ in range(20)]
        y = np.column_stack((np.arange(120) + 100, np.arange(120) + 20, np.arange(120) + 1)).astype(float)
        exact = score(rows, y, y.copy(), protocol())
        self.assertTrue(exact["gate"]["passed"])
        bad = y.copy(); bad[40:42] *= 2
        self.assertFalse(score(rows, y, bad, protocol())["gate"]["passed"])


if __name__ == "__main__": unittest.main()
