"""App-level padding compatibility; handwritten UI fixtures are not labels.

These component/schema checks do not execute a browser or claim visual acceptance.
The existing task-oriented fixtures supply chart rows, without fitting or oracle
calls. Final Streamlit serialization and real-model parity are checked separately.
"""
from pathlib import Path
import copy
import json
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "demo"))
sys.path.insert(0, str(ROOT / "tests"))

import altair as alt
from test_demo_ux import DEFAULT, SCENARIOS, TARGETS, fixture_result, scan_plan
from ui_charts import normalize_streamlit_padding, response_chart


class StreamlitPaddingCompatibility(unittest.TestCase):
    def test_numeric_padding_preserves_each_side_including_zero(self):
        for value in (0, 16, 1.5):
            with self.subTest(value=value):
                spec = {"padding": value, "layer": [{"mark": "point"}]}
                before = copy.deepcopy(spec)
                actual = normalize_streamlit_padding(spec)
                self.assertEqual(actual["padding"],
                                 dict.fromkeys(("left", "right", "top", "bottom"), value))
                self.assertEqual(spec, before)
                self.assertIsNot(actual, spec)
                self.assertNotIn("padding", actual["layer"][0])
                self.assertEqual(actual["layer"], before["layer"])

    def test_existing_edges_preserved_without_filling_missing_edges(self):
        for padding in ({"left": 0, "right": 9, "top": 1.5, "bottom": 22},
                        {"bottom": 0}, {"left": 7}, {}):
            with self.subTest(padding=padding):
                spec = {"padding": padding, "layer": [{"mark": "point"}]}
                before = copy.deepcopy(spec)
                actual = normalize_streamlit_padding(spec)
                self.assertEqual(actual["padding"], padding)
                self.assertEqual(actual, before)
                self.assertEqual(spec, before)
                self.assertIsNot(actual["padding"], padding)

    def test_absent_padding_and_child_content_are_not_rewritten(self):
        # A child's arbitrary content is intentionally not traversed: padding
        # is a top-level chart property, never inserted into individual layers.
        spec = {"layer": [{"mark": "point", "usermeta": {"padding": 7}}],
                "usermeta": {"source_kind": "synthetic_ui_fixture"}}
        before = copy.deepcopy(spec)
        actual = normalize_streamlit_padding(spec)
        self.assertEqual(actual, before)
        self.assertEqual(spec, before)
        self.assertNotIn("padding", actual)
        self.assertNotIn("padding", actual["layer"][0])

    def test_invalid_padding_fails_explicitly_without_mutation(self):
        cases = [None, "16", [], True, False, -1, float("nan"),
                 float("inf"), float("-inf"), {"horizontal": 4},
                 {"left": None}, {"right": "1"}, {"top": False},
                 {"bottom": -1}, {"left": float("nan")},
                 {"right": float("inf")}, {"top": []}]
        for padding in cases:
            with self.subTest(padding=repr(padding)):
                spec = {"padding": padding, "layer": [{"mark": "point"}]}
                before = repr(spec)
                with self.assertRaises(ValueError):
                    normalize_streamlit_padding(spec)
                self.assertEqual(repr(spec), before)

    def test_response_fixture_specs_have_only_top_level_object_padding(self):
        for second_axis in (None, "filter_offset_nm"):
            plan = scan_plan(DEFAULT, "filter2_bw_nm", second_axis, count=9)
            designs = [row["design_config"] for row in plan["designs"]]
            self.assertEqual(len(designs), 9 if second_axis is None else 81)
            result = fixture_result(designs)
            before = copy.deepcopy(result)
            baseline = fixture_result([DEFAULT])["predictions"][0]
            axes = ["filter2_bw_nm"] + ([second_axis] if second_axis else [])
            for target in TARGETS:
                with self.subTest(axes=axes, target=target):
                    spec = response_chart(result, axes, target, SCENARIOS[2], baseline)
                    # Check a serialized copy as well as Vega-Lite's schema;
                    # schema alone also accepts the problematic numeric form.
                    serialized = json.loads(json.dumps(spec, allow_nan=False))
                    self.assertEqual(serialized["padding"],
                                     dict.fromkeys(("left", "right", "top", "bottom"), 16))
                    self.assertTrue(all("padding" not in layer for layer in serialized["layer"]))
                    alt.LayerChart.from_dict(serialized, validate=True)
                    first = serialized["layer"][0]
                    self.assertEqual(first["mark"]["type"], "line" if second_axis is None else "rect")
                    self.assertEqual(len(first["data"]["values"]), len(designs))
                    for cell, row in zip(first["data"]["values"], result["predictions"]):
                        for name, value in row["targets"].items():
                            self.assertEqual(cell[name], value)
                    self.assertEqual(result, before)


if __name__ == "__main__":
    unittest.main()
