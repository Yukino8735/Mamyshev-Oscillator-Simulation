"""Small X-only components. No fit, synthetic formula, MATLAB or propagation."""
from copy import deepcopy
import csv
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from mamyshev_ml.demo10k_plan import (INPUT_UNITS, chunk_rows, pending_plan,
    read_input_rows, select_rows, validate_pending_plan, zero_authorization)
from mamyshev_ml.v4_evaluators import FEATURES, TARGETS, design_id, digest
from mamyshev_ml import supervisor


class TestDemo10kPlan(unittest.TestCase):
    def rows(self, count=7):
        designs = [dict(zip(FEATURES, (4 + index / 10, 10., 3., 4.))) for index in range(count)]
        return [{"design_id": design_id(design), "design_config": design} for design in designs]

    def test_generic_n_exact_plan_and_null_solver_targets(self):
        for count in (1, 3, 11):
            plan = pending_plan(self.rows(count))
            validate_pending_plan(plan, expected_count=count)
            self.assertEqual(len(plan["designs"]), count)
            self.assertEqual(plan["input_units"], INPUT_UNITS)
            self.assertEqual(plan["max_new_real_attempts"], 0)
            self.assertTrue(all(row["real_targets"] == dict.fromkeys(TARGETS) for row in plan["designs"]))

    def test_chunk_and_filter_preserve_parent_identity_order_and_count(self):
        plan = pending_plan(self.rows())
        chunks = list(chunk_rows(plan, chunk_size=3))
        self.assertEqual([chunk["row_count"] for chunk in chunks], [3, 3, 1])
        self.assertEqual([identifier for chunk in chunks for identifier in chunk["design_ids"]], [row["design_id"] for row in plan["designs"]])
        ids = [plan["designs"][index]["design_id"] for index in (0, 3, 6)]
        selection = select_rows(plan, design_ids=ids)
        self.assertEqual(selection["design_ids"], ids)
        self.assertEqual(selection["parent_plan_hash"], plan["plan_hash"])
        self.assertEqual(selection["rows_hash"], digest([plan["designs"][index] for index in (0, 3, 6)]))
        with self.assertRaises(ValueError): select_rows(plan, design_ids=[ids[0], ids[0]])
        with self.assertRaises(ValueError): select_rows(plan, start=-1)

    def test_hash_counts_targets_and_units_cannot_be_relabeled(self):
        plan = pending_plan(self.rows())
        bad = deepcopy(plan); bad["designs"][0]["design_config"]["pump_power_W"] = 9
        with self.assertRaises(ValueError): validate_pending_plan(bad, expected_count=7)
        for key, value in (("input_units", dict(INPUT_UNITS, pump_power_W="mW")), ("unique_designs", 8), ("max_new_real_attempts", 1)):
            bad = deepcopy(plan); bad[key] = value
            bad["plan_hash"] = digest({k: v for k, v in bad.items() if k != "plan_hash"})
            with self.assertRaises(ValueError): validate_pending_plan(bad, expected_count=7)
        bad = deepcopy(plan); bad["designs"][0]["real_targets"][TARGETS[0]] = 100.
        bad["plan_hash"] = digest({k: v for k, v in bad.items() if k != "plan_hash"})
        with self.assertRaises(ValueError): validate_pending_plan(bad, expected_count=7)

    def write_csv(self, path, rows, extra=None):
        columns = ["design_id", *FEATURES] + ([extra] if extra else [])
        with path.open("w", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=columns); writer.writeheader()
            for row in rows:
                value = {"design_id": row["design_id"], **row["design_config"]}
                if extra: value[extra] = ""
                writer.writerow(value)

    def test_frozen_csv_id_order_and_count(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "inputs.csv"; rows = self.rows(3)
            self.write_csv(path, rows)
            actual = read_input_rows(path, expected_count=3)
            self.assertEqual([row["design_id"] for row in actual], [row["design_id"] for row in rows])
            with self.assertRaises(ValueError): read_input_rows(path, expected_count=4)

    def test_duplicate_missing_nonfinite_unknown_units_and_labels_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "inputs.csv"; rows = self.rows(3)
            self.write_csv(path, [rows[0], rows[0]])
            with self.assertRaisesRegex(ValueError, "Duplicate"): read_input_rows(path, expected_count=2)
            for extra in ("pump_power_mW", "input_units", TARGETS[0]):
                self.write_csv(path, rows, extra=extra)
                with self.assertRaises(ValueError): read_input_rows(path, expected_count=3)
            path.write_text("pump_power_W,filter_offset_nm,filter2_bw_nm\n4,10,3\n")
            with self.assertRaises(ValueError): read_input_rows(path, expected_count=1)
            path.write_text(",".join(FEATURES) + "\nnan,10,3,4\n")
            with self.assertRaises(ValueError): read_input_rows(path, expected_count=1)
            path.write_text(",".join(FEATURES) + "\n4,10,3,4.01\n")
            with self.assertRaises(ValueError): read_input_rows(path, expected_count=1)

    def test_zero_authorization_uses_real_guard_before_any_process_or_reservation(self):
        plan = pending_plan(self.rows(3)); authorization = zero_authorization(plan)
        with tempfile.TemporaryDirectory() as directory, patch.object(supervisor, "execute_once") as launch:
            folder = Path(directory) / "must_not_exist"
            with self.assertRaises(PermissionError):
                supervisor.execute_authorized_design(matlab="/not_invoked", plan=plan,
                    authorization=authorization, design_id=plan["designs"][0]["design_id"],
                    batch_dir=folder, run_id="blocked", execute_real=True)
            launch.assert_not_called(); self.assertFalse(folder.exists())


if __name__ == "__main__":
    unittest.main()
