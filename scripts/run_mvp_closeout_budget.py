#!/usr/bin/env python3
"""Closeout settings only; all work shares the unchanged owned-process monitor."""
import argparse
import importlib.util
from pathlib import Path
from types import SimpleNamespace


def short_timeout(value):
    number=float(value)
    if not 0<number<=60:raise argparse.ArgumentTypeError('Closeout subprocess cap is 60 seconds')
    return number


class CloseoutParser(argparse.ArgumentParser):
    def add_argument(self,*args,**kwargs):
        if args==('--batch',):kwargs.update(choices=['mvp_closeout_001'],default='mvp_closeout_001')
        if args==('--timeout-s',):kwargs['type']=short_timeout
        return super().add_argument(*args,**kwargs)


def budget_module():
    path=Path(__file__).with_name('run_v4_budget.py')
    spec=importlib.util.spec_from_file_location('closeout_existing_budget',path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    module.CAPS={'engineering':300.}
    module.argparse=SimpleNamespace(ArgumentParser=CloseoutParser,REMAINDER=argparse.REMAINDER)
    return module


if __name__=='__main__':budget_module().main()
