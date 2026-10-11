"""Short artificial-fixture checks, never the released synthetic oracle or labels."""
import csv
import json
from pathlib import Path
import sys
import tempfile
import time
import unittest

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from mamyshev_ml.v4_search import (FEATURES, TARGETS, acquisition, best_actual,
    eligible_rows, gp_batch, load_candidates, paired_pool, rank_acquisition,
    run_experiment, scaled_inputs, summarize_experiment)

BOUNDS = dict(zip(FEATURES, ([2, 10], [2, 16], [.5, 8], [1, 8])))
SCENARIO = {"id": "artificial_fixture", "candidate_group": "global", "fixed_inputs": {},
            "input_constraints": {"pump_power_W": {"lte": 5}},
            "output_constraints": {"compressed_duration_fs": {"lte": 40}},
            "objective": {"target": "compressed_peak_power_MW", "direction": "maximize"}}


def fixture_pool():
    return [{"design_id": f"artificial_{i:03d}", "candidate_group": "global",
             "pump_power_W": 2 + i / 40, "filter_offset_nm": 2 + i / 10,
             "filter2_bw_nm": 1 + i / 100, "gain_length_m": 2 + (i % 40) / 10}
            for i in range(100)]


class ArtificialEvaluator:
    """Deliberately simple positive labels, explicitly unrelated to release oracle."""
    def __init__(self, directory):
        self.directory = directory
        self.calls = self.unique_computations = self.cache_hits = 0
        self.cache = {}

    def evaluate(self, design, *, request_id, design_id):
        # Verify the *whole* batch is durable before the first queried member.
        locks = [json.loads(line) for line in (self.directory / "batch_locks.jsonl").read_text().splitlines()]
        lock = locks[-1]
        assert design_id in lock["design_ids"]
        assert len(lock["design_ids"]) == (16 if lock["batch_index"] == 0 else 4)
        self.calls += 1
        hit = design_id in self.cache
        self.cache_hits += int(hit)
        self.unique_computations += int(not hit)
        targets = {"compressed_energy_nJ": 100 + design["pump_power_W"],
                   "compressed_duration_fs": 37 + design["filter2_bw_nm"],
                   "compressed_peak_power_MW": .5 + design["filter_offset_nm"] / 10}
        self.cache[design_id] = targets
        return {"targets": targets, "job_status": "completed", "cache_hit": hit,
                "evaluation_id": f"artificial_evaluation_{design_id}",
                "identity": {"source_kind": "artificial_search_test_fixture"},
                "source_kind": "artificial_search_test_fixture"}


class SearchTests(unittest.TestCase):
    def test_x_only_loader_rejects_label_columns_and_nonfinite(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "candidate.csv"
            with path.open("w", newline="") as stream:
                writer = csv.DictWriter(stream, fieldnames=["design_id", "candidate_group", *FEATURES, "compressed_energy_nJ"])
                writer.writeheader()
            with self.assertRaisesRegex(ValueError, "X-only"):
                load_candidates(path, BOUNDS)
            with path.open("w", newline="") as stream:
                writer = csv.DictWriter(stream, fieldnames=["design_id", "candidate_group", *FEATURES])
                writer.writeheader()
                writer.writerow({**fixture_pool()[0], "pump_power_W": "nan"})
            with self.assertRaisesRegex(ValueError, "nonfinite"):
                load_candidates(path, BOUNDS)

    def test_pairing_input_constraints_and_declared_scaling(self):
        rows = fixture_pool()
        rows[-1]["pump_power_W"] = 9
        self.assertEqual(len(eligible_rows(rows, SCENARIO)), 99)
        p1, i1, r1 = paired_pool(rows, SCENARIO, 11, 0)
        p2, i2, r2 = paired_pool(rows, SCENARIO, 11, 0)
        self.assertEqual(p1, p2)
        self.assertEqual(i1, i2)
        self.assertEqual(r1, r2)
        self.assertEqual(len(set(i1)), 16)
        x = scaled_inputs([rows[0]], BOUNDS)[0]
        np.testing.assert_array_equal(x, [0, 0, .5 / 7.5, 1 / 7])

    def test_predeclared_acquisition_fallbacks(self):
        order, rule = rank_acquisition(np.zeros(3), np.array([[1, 1, 1], [2, 2, 2], [2, 2, 2]]), ["z", "b", "a"])
        self.assertEqual(order.tolist(), [2, 1, 0])
        self.assertEqual(rule, "uncertainty_then_id_fallback")
        order, rule = rank_acquisition(np.array([np.nan, 0]), np.zeros((2, 3)), ["b", "a"])
        self.assertEqual(order.tolist(), [1, 0])
        self.assertEqual(rule, "design_id_fallback")
        order, rule = rank_acquisition(np.array([1, 1, .5]), np.ones((3, 3)), ["b", "a", "c"])
        self.assertEqual(order.tolist(), [1, 0, 2])
        self.assertEqual(rule, "acquisition_then_id")
        order, rule = rank_acquisition(np.ones(2), np.array([[2, 2, 2], [1, 1, 1]]), ["b", "a"])
        self.assertEqual(order.tolist(), [0, 1])
        self.assertEqual(rule, "uncertainty_then_id_fallback")

    def test_find_feasibility_then_objective_for_both_directions(self):
        mean = np.log([[110, 35, 1], [110, 50, 2]])
        std = np.full_like(mean, .1)
        score, probability = acquisition(mean, std, np.array([[110, 50, 1]]), SCENARIO)
        np.testing.assert_array_equal(score, probability)
        self.assertGreater(score[0], score[1])
        score, _ = acquisition(mean, std, np.array([[110, 35, .5]]), SCENARIO)
        self.assertTrue(np.isfinite(score).all())
        self.assertGreater(score[0], score[1])
        minimization = {**SCENARIO, "objective": {"target": "compressed_duration_fs", "direction": "minimize"},
                        "output_constraints": {"compressed_energy_nJ": {"gte": 100}}}
        score, _ = acquisition(mean, std, np.array([[110, 45, .5]]), minimization)
        self.assertGreater(score[0], score[1])

    def test_gp_queries_only_provided_observations(self):
        pool = fixture_pool()
        chosen = list(range(16))
        y = [dict(zip(TARGETS, [110 + i, 38 + .01 * i, 1 + .05 * i])) for i in chosen]
        picked, predictions, rule = gp_batch(scaled_inputs(pool, BOUNDS), chosen, y,
            list(range(16, 100)), pool, SCENARIO)
        self.assertEqual(len(picked), 4)
        self.assertEqual(len(set(picked)), 4)
        self.assertFalse(set(picked) & set(chosen))
        self.assertTrue(all(set(predictions[i]["targets"]) == set(TARGETS) for i in picked))
        self.assertTrue(all(np.isfinite(list(predictions[i]["targets"].values())).all() for i in picked))

    def test_64_logical_events_durable_batch_lock_and_cache_count(self):
        pool = fixture_pool()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "experiment"
            evaluator = ArtificialEvaluator(path)
            events = []
            result = run_experiment(evaluator=evaluator, pool=pool, initial=list(range(16)), scenario=SCENARIO,
                bounds=BOUNDS, method="random", seed=11, scenario_index=0, directory=path,
                deadline=time.monotonic() + 30, global_events=events)
            self.assertEqual(result["status"], "completed")
            self.assertEqual(len(events), 64)
            self.assertEqual(evaluator.calls, 64)
            self.assertEqual(evaluator.unique_computations, 64)
            self.assertEqual(len({e["design_id"] for e in events}), 64)
            self.assertEqual(len((path / "batch_locks.jsonl").read_text().splitlines()), 13)
            self.assertIsNone(result["false_feasible"]["count"])
            second = Path(directory) / "second"
            evaluator.directory = second
            again = run_experiment(evaluator=evaluator, pool=pool, initial=list(range(16)), scenario=SCENARIO,
                bounds=BOUNDS, method="random", seed=11, scenario_index=0, directory=second,
                deadline=time.monotonic() + 30, global_events=events)
            self.assertEqual(again["cache_hits"], 64)
            self.assertEqual(evaluator.calls, 128)
            self.assertEqual(evaluator.unique_computations, 64)

    def test_deadline_preserves_partial_not_completed(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "expired"
            evaluator = ArtificialEvaluator(path)
            result = run_experiment(evaluator=evaluator, pool=fixture_pool(), initial=list(range(16)), scenario=SCENARIO,
                bounds=BOUNDS, method="random", seed=11, scenario_index=0, directory=path,
                deadline=time.monotonic() - 1, global_events=[])
            self.assertEqual(result["status"], "budget_exhausted")
            self.assertEqual(evaluator.calls, 0)
            self.assertIsNone(result["best_actual_feasible"]["64"]["value"])

    def test_no_feasible_and_false_feasible_are_not_filled(self):
        event = {"design_id": "artificial", "targets": dict(zip(TARGETS, [110, 45, 1])),
                 "actual_feasible": False, "cache_hit": False, "prediction": {"targets": {}},
                 "predicted_feasible": True,
                 "prediction_errors": {t: {"absolute_error": 1, "relative_error": .1} for t in TARGETS}}
        self.assertIsNone(best_actual([event], SCENARIO)["value"])
        result = summarize_experiment([event], SCENARIO, "gp", 11, "failed", "fixture", 0, 0)
        self.assertEqual(result["false_feasible"]["count"], 1)
        self.assertEqual(result["false_feasible"]["predicted_feasible_count"], 1)
        self.assertEqual(result["best_actual_feasible"]["16"]["missing_reason"], "budget_not_reached")


if __name__ == "__main__":
    unittest.main()
