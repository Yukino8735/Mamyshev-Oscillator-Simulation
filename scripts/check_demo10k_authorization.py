#!/usr/bin/env python3
"""Five existing authorization regressions; all real execution is mocked."""
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tests"))
names = (
    "test_default_denial_and_zero_allowance_do_not_reserve",
    "test_changed_plan_unauthorized_id_and_unknown_fields_fail",
    "test_serial_ledger_refuses_run_or_directory_reset",
    "test_incomplete_attempt_remains_reserved_and_blocks_resume",
    "test_exhausted_cumulative_wall_and_stop_refuse_launch",
)
suite = unittest.defaultTestLoader.loadTestsFromNames(
    [f"test_v4_live_supervisor.LiveAuthorization.{name}" for name in names]
)
result = unittest.TextTestRunner(verbosity=2).run(suite)
raise SystemExit(0 if result.wasSuccessful() else 1)
