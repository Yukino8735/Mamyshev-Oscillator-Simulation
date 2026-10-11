#!/usr/bin/env python3
"""V4 category accounting around the EXISTING owned-process monitor, no solver."""
import argparse
import datetime as dt
import fcntl
import importlib.util
import json
import os
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / 'reports/local/accuracy_v4_001'
CAPS = {'engineering': 300., 'ml': 900.}


def write(path, data):
    temp = path.with_suffix('.tmp')
    temp.write_text(json.dumps(data, indent=2, allow_nan=False) + '\n')
    temp.replace(path)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('category', choices=CAPS)
    parser.add_argument('label')
    parser.add_argument('--timeout-s', type=float, required=True)
    parser.add_argument('--batch', choices=['accuracy_v4_001', 'accuracy_v4_1_001', 'accuracy_v4_2_001'], default='accuracy_v4_001')
    parser.add_argument('command', nargs=argparse.REMAINDER)
    args = parser.parse_args()
    evidence = ROOT / 'reports/local' / args.batch
    if not evidence.is_dir():
        parser.error('Batch must have an existing exclusive start snapshot; do not silently create another budget')
    if not args.label.replace('_', '').isalnum() or not 0 < args.timeout_s <= CAPS[args.category]:
        parser.error('Invalid label or category timeout')
    command = args.command
    if command and command[0] == '--':
        command = command[1:]
    if not command:
        parser.error('Provide Python arguments after --')
    if command[0] != '-m':
        command[0] = str((ROOT / command[0]).resolve())
    folder = evidence / 'budget' / args.category / args.label
    folder.parent.mkdir(parents=True, exist_ok=True)
    with (evidence / 'serial_budget.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        ledger_path = evidence / 'budget_ledger.json'
        ledger = json.loads(ledger_path.read_text()) if ledger_path.exists() else {'caps_s': CAPS, 'attempts': []}
        if any(a['status'] == 'running' for a in ledger['attempts']):
            raise RuntimeError('Unknown running reservation: inspect before any continuation')
        used = sum(a['charged_s'] for a in ledger['attempts'] if a['category'] == args.category)
        remaining = CAPS[args.category] - used
        if remaining <= 0:
            raise RuntimeError('Category budget exhausted')
        timeout = min(args.timeout_s, remaining)
        folder.mkdir(exist_ok=False)
        entry = {'category': args.category, 'label': args.label, 'status': 'running',
                 'reserved_cap_s': timeout, 'charged_s': timeout,
                 'start_utc': dt.datetime.now(dt.timezone.utc).isoformat(),
                 'command': [sys.executable, *command], 'full_gmmnlse_calls': 0}
        ledger['attempts'].append(entry)
        write(ledger_path, ledger)
        spec = importlib.util.spec_from_file_location('v4_existing_process_monitor', ROOT / 'tests/run_matlab_short.py')
        monitor = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(monitor)
        env = os.environ.copy()
        env.update({k: '2' for k in ['OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS',
                                    'NUMEXPR_NUM_THREADS', 'VECLIB_MAXIMUM_THREADS']})
        env['PYTHONPATH'] = str(ROOT / 'src') + os.pathsep + str(ROOT / 'mamyshev_accuracy_v4/reference')
        env['MPLBACKEND'] = 'Agg'
        env['MPLCONFIGDIR'] = str(evidence / 'matplotlib_cache')
        env['PYTHONDONTWRITEBYTECODE'] = '1'
        started = time.monotonic()
        record = None
        error = None
        try:
            record = monitor.run_isolated([sys.executable, *command], folder, env, timeout,
                                          {'kind': 'v4_' + args.category, 'full_cavity_runs': 0},
                                          shutdown_reserve_s=min(7, timeout / 4))
        except BaseException as exception:
            error = repr(exception)
            path = folder / 'runner_record.json'
            if path.exists():
                record = json.loads(path.read_text())
        finally:
            measured = time.monotonic() - started
            entry.update(status='completed' if record and record['status'] == 'completed' and not error else 'failed',
                         charged_s=measured, runner_elapsed_s=record.get('elapsed_s') if record else None,
                         error=error, end_utc=dt.datetime.now(dt.timezone.utc).isoformat())
            write(ledger_path, ledger)
        print(json.dumps(entry, indent=2))
        if entry['status'] != 'completed':
            sys.exit(1)


if __name__ == '__main__':
    main()
