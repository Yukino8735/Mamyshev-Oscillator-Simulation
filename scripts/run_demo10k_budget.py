#!/usr/bin/env python3
"""This batch's caps around the existing owned-process monitor; no new monitor."""
import argparse
import importlib.util
from pathlib import Path
from types import SimpleNamespace

class DemoParser(argparse.ArgumentParser):
    def add_argument(self,*args,**kwargs):
        if args==('--batch',):kwargs.update(choices=['demo_10k_release_001'],default='demo_10k_release_001')
        return super().add_argument(*args,**kwargs)

def main():
    path=Path(__file__).with_name('run_v4_budget.py')
    spec=importlib.util.spec_from_file_location('demo10k_existing_budget',path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    module.CAPS={'engineering':600.,'ml':900.,'matlab':180.}
    module.argparse=SimpleNamespace(ArgumentParser=DemoParser,REMAINDER=argparse.REMAINDER)
    module.main()

if __name__=='__main__':main()
