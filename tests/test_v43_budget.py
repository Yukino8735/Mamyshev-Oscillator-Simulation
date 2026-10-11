"""No processes or models: check the application-only budget settings adapter."""
import argparse
import hashlib
import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('v43_budget_test', ROOT/'scripts/run_v43_budget.py')
wrapper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(wrapper)


class TestV43Budget(unittest.TestCase):
    def test_old_implementation_is_unchanged_and_caps_are_independent(self):
        path = ROOT/'scripts/run_v4_budget.py'
        before = hashlib.sha256(path.read_bytes()).hexdigest()
        module = wrapper.budget_module()
        self.assertEqual(module.CAPS, {'engineering': 300., 'ml': 300.})
        self.assertEqual(module.main.__code__.co_filename, str(path))
        self.assertEqual(before, hashlib.sha256(path.read_bytes()).hexdigest())
        self.assertIs(argparse.ArgumentParser, wrapper.BatchParser.__bases__[0])

    def test_only_new_batch_is_accepted_default_or_explicit(self):
        parser = wrapper.BatchParser()
        parser.add_argument('--batch', choices=['accuracy_v4_001'], default='accuracy_v4_001')
        self.assertEqual(parser.parse_args([]).batch, wrapper.BATCH)
        self.assertEqual(parser.parse_args(['--batch', wrapper.BATCH]).batch, wrapper.BATCH)
        with self.assertRaises(SystemExit):
            parser.parse_args(['--batch', 'accuracy_v4_2_001'])
