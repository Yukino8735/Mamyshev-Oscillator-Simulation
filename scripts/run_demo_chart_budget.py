#!/usr/bin/env python3
"""180 s chart-fix test adapter; reuse the existing serial process monitor."""
import argparse
import importlib.util
from pathlib import Path
from types import SimpleNamespace


def short_timeout(value):
    value = float(value)
    if not 0 < value <= 30:
        raise argparse.ArgumentTypeError("Chart test process limit is 30 seconds")
    return value


class ChartParser(argparse.ArgumentParser):
    def add_argument(self, *args, **kwargs):
        if args == ("--batch",):
            kwargs.update(choices=["demo_chart_fix_001"], default="demo_chart_fix_001")
        if args == ("--timeout-s",):
            kwargs["type"] = short_timeout
        return super().add_argument(*args, **kwargs)


if __name__ == "__main__":
    spec = importlib.util.spec_from_file_location("chart_existing_budget", Path(__file__).with_name("run_v4_budget.py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.CAPS = {"engineering": 180.}
    module.argparse = SimpleNamespace(ArgumentParser=ChartParser, REMAINDER=argparse.REMAINDER)
    module.main()
