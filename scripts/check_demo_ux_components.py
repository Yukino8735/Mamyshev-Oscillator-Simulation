#!/usr/bin/env python3
"""One bounded UI component suite: new fixtures and directly affected regressions."""
from pathlib import Path
import unittest

TESTS = Path(__file__).resolve().parents[1] / "tests"
suite = unittest.TestSuite()
for pattern in ("test_demo_ux.py", "test_demo_ui_logic.py", "test_demo_inference.py", "test_demo_chart_padding.py", "test_demo_single_model.py"):
    suite.addTests(unittest.defaultTestLoader.discover(str(TESTS), pattern=pattern))
result = unittest.TextTestRunner(verbosity=2).run(suite)
raise SystemExit(0 if result.wasSuccessful() else 1)
