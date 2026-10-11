#!/usr/bin/env python3
"""300 s UX batch adapter around the existing serial owned-process monitor."""
import argparse
import importlib.util
from pathlib import Path
from types import SimpleNamespace


def short_timeout(value):
    value = float(value)
    if not 0 < value <= 60:
        raise argparse.ArgumentTypeError("UX child process limit is 60 seconds")
    return value


class UXParser(argparse.ArgumentParser):
    def add_argument(self, *args, **kwargs):
        if args == ("--batch",):
            kwargs.update(choices=["demo_ux_001"], default="demo_ux_001")
        if args == ("--timeout-s",):
            kwargs["type"] = short_timeout
        return super().add_argument(*args, **kwargs)


if __name__ == "__main__":
    spec = importlib.util.spec_from_file_location("ux_existing_budget", Path(__file__).with_name("run_v4_budget.py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.CAPS = {"engineering": 300.}
    module.argparse = SimpleNamespace(ArgumentParser=UXParser, REMAINDER=argparse.REMAINDER)
    module.main()
