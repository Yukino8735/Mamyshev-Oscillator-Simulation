#!/usr/bin/env python3
"""Batch settings only: invoke the unchanged V4 budget/owned-process implementation.

The V4.2 release binds run_v4_budget.py bytes. A module-local parser adapter
supplies this explicitly authorized batch and tighter application cap; no locks,
accounting, process cleanup or timeout code is replaced.
"""
import argparse
import importlib.util
from pathlib import Path
from types import SimpleNamespace

BATCH = 'application_v4_3_001'


class BatchParser(argparse.ArgumentParser):
    def add_argument(self, *args, **kwargs):
        if args == ('--batch',):
            kwargs.update(choices=[BATCH], default=BATCH)
        return super().add_argument(*args, **kwargs)


def budget_module():
    path = Path(__file__).with_name('run_v4_budget.py')
    spec = importlib.util.spec_from_file_location('v43_existing_budget', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.CAPS = {'engineering': 300., 'ml': 300.}
    module.argparse = SimpleNamespace(ArgumentParser=BatchParser, REMAINDER=argparse.REMAINDER)
    return module


if __name__ == '__main__':
    budget_module().main()
