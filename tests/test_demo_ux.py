"""Task-oriented Demo tests. Handwritten numbers here are UI fixtures, not labels."""
from pathlib import Path
import copy
import json
import sys
import unittest
from unittest.mock import patch

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "demo"))
from mamyshev_ml.v4_evaluators import FEATURES, TARGETS, canonical
from ui_logic import (DEFAULT, scan_plan, candidate_plan, rank_predictions,
                      constraint_rows, compare_predictions, pending_requests)
from ui_charts import response_chart

SCENARIOS = json.loads((ROOT / "demo/assets/scenarios.json").read_text())["scenarios"]


def fixture_result(designs):
    """Asymmetric, nonuniform fixture values expose cell/coordinate swaps."""
    rows = []
    for index, design in enumerate(designs):
        values = dict(zip(TARGETS, (100. + index * 3, 28. + index, 1. + index * .13)))
        rows.append({"kind": "Prediction", "source_kind": "surrogate_prediction",
                     "design": design, "targets": values,
                     "lower": {k: v * .99 for k, v in values.items()},
                     "upper": {k: v * 1.01 for k, v in values.items()}})
    return {"kind": "Prediction", "model_id": "handwritten_ui_fixture", "model_sha256": "fixture",
            "n_train": 0, "interval_status": "limited", "predictions": rows,
            "n_predictions": len(rows)}


def chart_dict(result, axes, baseline=None):
    return response_chart(result, axes, TARGETS[2], SCENARIOS[2], baseline)


class TaskOrientedUIControls(unittest.TestCase):
    def test_scan_nonuniform_legal_length_and_rejections(self):
        plan = scan_plan(DEFAULT, "gain_length_m", "filter_offset_nm", count=4,
                         ranges={"gain_length_m": [3.9, 4.6], "filter_offset_nm": [7., 11.]},
                         counts={"gain_length_m": 4, "filter_offset_nm": 3})
        rows = [r["design_config"] for r in plan["designs"]]
        self.assertEqual(len(rows), 12)
        self.assertEqual(len({canonical(r) for r in rows}), 12)
        lengths = sorted({r["gain_length_m"] for r in rows})
        self.assertEqual(len(lengths), 4)
        self.assertEqual((lengths[0], lengths[-1]), (3.9, 4.6))
        self.assertTrue(all(abs(10 * v - round(10 * v)) < 1e-8 for v in lengths))
        self.assertTrue(all(r["pump_power_W"] == 4 and r["filter2_bw_nm"] == 3 for r in rows))
        for args, kwargs in [((DEFAULT, "gain_length_m", "gain_length_m"), {}),
                             ((DEFAULT, "gain_length_m"), {"ranges": {"gain_length_m": [4.05, 4.5]}}),
                             ((DEFAULT, "gain_length_m"), {"count": 4, "ranges": {"gain_length_m": [4., 4.1]}}),
                             ((DEFAULT, "filter_offset_nm"), {"count": 22}),
                             ((DEFAULT, "filter_offset_nm"), {"ranges": {"filter_offset_nm": [11., 7.]}})]:
            with self.subTest(args=args, kwargs=kwargs), self.assertRaises(ValueError):
                scan_plan(*args, **kwargs)

    def test_candidate_ranges_seed_fixed_inputs_and_all_scenarios(self):
        ranges = {"filter_offset_nm": [8., 12.], "filter2_bw_nm": [2., 5.]}
        first = candidate_plan(SCENARIOS[2], 32, 10., {}, seed=72001, ranges=ranges)
        repeat = candidate_plan(SCENARIOS[2], 32, 10., {}, seed=72001, ranges=ranges)
        other = candidate_plan(SCENARIOS[2], 32, 10., {}, seed=72002, ranges=ranges)
        self.assertEqual(first["designs"], repeat["designs"])
        self.assertNotEqual(first["designs"], other["designs"])
        for row in first["designs"]:
            self.assertEqual(set(row), {"design_id", "design_config"})
            d = row["design_config"]
            self.assertEqual((d["pump_power_W"], d["gain_length_m"]), (4., 4.))
            for key, bounds in ranges.items():
                self.assertLessEqual(bounds[0], d[key]); self.assertLessEqual(d[key], bounds[1])
        for scenario in SCENARIOS:
            p = candidate_plan(scenario, 16, 10., {}, seed=72001)
            self.assertTrue(0 < p["unique_designs"] <= 16)
            for row in p["designs"]:
                for key, value in scenario["fixed_inputs"].items():
                    self.assertEqual(row["design_config"][key], value)
        with self.assertRaises(ValueError):
            candidate_plan(SCENARIOS[2], 4097, 10., {}, ranges=ranges)
        with self.assertRaises(ValueError):
            candidate_plan(SCENARIOS[2], 32, 10., {"gain_length_m": 4.1})

    @patch("ui_logic.require_current_model")
    def test_constraints_no_feasible_and_export_at_most_three(self, identity_guard):
        designs = [{**DEFAULT, "filter_offset_nm": float(8 + i)} for i in range(4)]
        result = fixture_result(designs)
        ranked = rank_predictions(result, SCENARIOS[2])
        self.assertEqual([r["targets"][TARGETS[2]] for r in ranked], sorted([r["targets"][TARGETS[2]] for r in ranked], reverse=True))
        impossible = copy.deepcopy(SCENARIOS[2]); impossible["output_constraints"][TARGETS[1]]["lte"] = 1.
        self.assertEqual(rank_predictions(result, impossible), [])
        threshold = copy.deepcopy(SCENARIOS[2]); threshold["output_constraints"][TARGETS[1]]["lte"] = 28.
        diagnostics = constraint_rows(result["predictions"][0], threshold)
        duration = next(d for d in diagnostics if d["field"] == TARGETS[1])
        self.assertTrue(duration["point_pass"])
        self.assertEqual(duration["interval_status"], "crosses_threshold")
        pending = pending_requests(result, ranked[:3], SCENARIOS[2]["id"])
        self.assertEqual(len(pending["requests"]), 3)
        self.assertEqual(pending["max_new_real_attempts"], 0)
        self.assertTrue(all(r["real_targets"] is None and r["evaluation_id"] is None for r in pending["requests"]))
        with self.assertRaises(ValueError):
            pending_requests(result, ranked, SCENARIOS[2]["id"])
        forged = copy.deepcopy(ranked[0]); forged["targets"][TARGETS[2]] += .1
        with self.assertRaises(ValueError):
            pending_requests(result, [forged], SCENARIOS[2]["id"])

    def test_rect_cells_numeric_boundaries_and_actual_values(self):
        designs = [{**DEFAULT, "filter_offset_nm": x, "filter2_bw_nm": y}
                   for x in (8., 10., 13.) for y in (1., 3., 6.)]
        result = fixture_result(designs)
        spec = chart_dict(result, ["filter_offset_nm", "filter2_bw_nm"], result["predictions"][4])
        layer = next(v for v in spec["layer"] if v.get("name") == "prediction_cells")
        mark = layer["mark"]
        self.assertEqual(mark["type"] if isinstance(mark, dict) else mark, "rect")
        enc = layer["encoding"]
        self.assertTrue(all(k in enc for k in ("x", "x2", "y", "y2", "color")))
        self.assertEqual(enc["x"]["type"], "quantitative")
        self.assertEqual(enc["y"]["type"], "quantitative")
        self.assertIn("MW", json.dumps(enc["color"]))
        self.assertIn("nm", json.dumps(enc["x"]))
        self.assertIn("nm", json.dumps(enc["y"]))
        data = layer.get("data", spec.get("data", {}))
        values = data.get("values", spec.get("datasets", {}).get(data.get("name")))
        self.assertEqual(len(values), 9)
        color = enc["color"]["field"]
        for cell, row in zip(values, result["predictions"]):
            self.assertEqual(cell[color], row["targets"][TARGETS[2]])
            for axis, feature in (("x", "filter_offset_nm"), ("y", "filter2_bw_nm")):
                self.assertLess(cell[enc[axis]["field"]], row["design"][feature])
                self.assertGreater(cell[enc[axis + "2"]["field"]], row["design"][feature])
        names = {v.get("name") for v in spec["layer"]}
        self.assertIn("baseline_marker", names)
        self.assertIn("best_feasible_marker", names)
        markers = {v["name"]: v["data"]["values"][0] for v in spec["layer"] if v.get("name", "").endswith("_marker")}
        self.assertEqual(markers["baseline_marker"]["filter_offset_nm"], 10.)
        self.assertEqual(markers["baseline_marker"]["filter2_bw_nm"], 3.)
        self.assertEqual(markers["best_feasible_marker"][TARGETS[2]], result["predictions"][-1]["targets"][TARGETS[2]])
        self.assertEqual(enc["x"]["scale"]["domain"], [7., 14.5])
        self.assertEqual(enc["y"]["scale"]["domain"], [0., 7.5])
        absent = chart_dict(result, ["filter_offset_nm", "filter2_bw_nm"], fixture_result([{**DEFAULT, "pump_power_W": 5.}])["predictions"][0])
        self.assertEqual(absent["usermeta"]["response_summary"]["baseline_marker"]["status"], "omitted")
        incomplete = copy.deepcopy(result); incomplete["predictions"].pop(2)
        gap = chart_dict(incomplete, ["filter_offset_nm", "filter2_bw_nm"])
        self.assertEqual(gap["usermeta"]["response_summary"]["missing_cells"], 1)
        bad = copy.deepcopy(result); bad["predictions"][0]["targets"][TARGETS[2]] = float("nan")
        with self.assertRaises(ValueError):
            chart_dict(bad, ["filter_offset_nm", "filter2_bw_nm"])

    def test_comparison_uses_raw_baseline_and_objective_direction(self):
        baseline, candidate = fixture_result([DEFAULT, {**DEFAULT, "filter_offset_nm": 11.}])["predictions"]
        values = compare_predictions(baseline, candidate, SCENARIOS[3]["objective"])
        for target in TARGETS:
            delta = candidate["targets"][target] - baseline["targets"][target]
            self.assertEqual(values[target]["absolute_change"], delta)
            self.assertEqual(values[target]["relative_change"], delta / baseline["targets"][target])
        self.assertLess(values[TARGETS[1]]["directional_improvement"], 0)
        zero = copy.deepcopy(baseline); zero["targets"][TARGETS[2]] = 0
        self.assertIsNone(compare_predictions(zero, candidate, SCENARIOS[2]["objective"])[TARGETS[2]]["relative_change"])


if __name__ == "__main__":
    unittest.main()
