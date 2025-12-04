#!/usr/bin/env python3
"""
Benchmark harness to compare RL vs baseline solvers on multiple CNF instances.
Runs each instance with timeout, logs results to CSV.
"""
import argparse
import os
import time
import signal
import csv
from pathlib import Path
from typing import Optional, Dict, Any

from run_solver import parse_dimacs_file
from cdcl_rl import CDCLSolverRL
from cdcl_baseline import CDCLSolverBaseline


class TimeoutException(Exception):
    pass


def timeout_handler(signum, frame):
    raise TimeoutException()


def run_instance(cnf_path: str, mode: str, heuristic: str, epoch: int, restart: int, timeout_sec: int) -> Dict[str, Any]:
    """
    Run a single instance with timeout.
    Returns dict with: instance, mode, heuristic, status (SAT/UNSAT/TIMEOUT), time, conflicts, decisions, propagations
    """
    instance_name = os.path.basename(cnf_path)
    result = {
        'instance': instance_name,
        'mode': mode,
        'heuristic': heuristic,
        'status': 'TIMEOUT',
        'time': timeout_sec,
        'conflicts': 0,
        'decisions': 0,
        'propagations': 0,
        'restarts': 0,
    }

    try:
        num_vars, clauses = parse_dimacs_file(cnf_path)
        
        if mode == 'rl':
            solver = CDCLSolverRL(num_vars, clauses)
            solver.epoch_size = epoch
            solver.restart_interval = restart
        else:
            solver = CDCLSolverBaseline(num_vars, clauses, heuristic=heuristic)
            solver.restart_interval = restart
            solver.epoch_size = epoch

        # Set timeout
        signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(timeout_sec)

        t0 = time.time()
        sat = solver.solve()
        elapsed = time.time() - t0

        signal.alarm(0)  # Cancel alarm

        result['status'] = 'SAT' if sat else 'UNSAT'
        result['time'] = elapsed
        result['conflicts'] = solver.conflicts
        result['decisions'] = solver.decisions
        result['propagations'] = solver.propagations
        result['restarts'] = solver.restarts

    except TimeoutException:
        result['status'] = 'TIMEOUT'
        result['time'] = timeout_sec
    except Exception as e:
        result['status'] = f'ERROR: {str(e)}'
        result['time'] = timeout_sec
    finally:
        signal.alarm(0)

    return result


def main():
    parser = argparse.ArgumentParser(description="Benchmark RL vs baseline on multiple CNF instances")
    parser.add_argument('--cnf-dir', type=str, required=True, help='Directory containing .cnf files')
    parser.add_argument('--output', type=str, default='benchmark_results.csv', help='Output CSV file')
    parser.add_argument('--timeout', type=int, default=300, help='Timeout per instance (seconds)')
    parser.add_argument('--epoch', type=int, default=50, help='Conflicts per epoch')
    parser.add_argument('--restart', type=int, default=200, help='Conflicts per restart')
    parser.add_argument('--baseline-heuristic', type=str, default='vsids', choices=['vsids', 'jw', 'dlis', 'random'], help='Heuristic for baseline')
    parser.add_argument('--modes', nargs='+', default=['rl', 'baseline'], choices=['rl', 'baseline'], help='Modes to run')
    args = parser.parse_args()

    cnf_dir = Path(args.cnf_dir)
    if not cnf_dir.exists():
        print(f"Error: Directory {cnf_dir} does not exist")
        return

    cnf_files = sorted(cnf_dir.glob('*.cnf'))
    if not cnf_files:
        print(f"No .cnf files found in {cnf_dir}")
        return

    print(f"Found {len(cnf_files)} CNF files")
    print(f"Timeout: {args.timeout}s, Epoch: {args.epoch}, Restart: {args.restart}")
    print(f"Modes: {args.modes}, Baseline heuristic: {args.baseline_heuristic}")
    print(f"Output: {args.output}\n")

    results = []
    total_runs = len(cnf_files) * len(args.modes)
    current_run = 0

    for cnf_path in cnf_files:
        for mode in args.modes:
            current_run += 1
            print(f"[{current_run}/{total_runs}] Running {cnf_path.name} ({mode})... ", end='', flush=True)
            
            result = run_instance(
                str(cnf_path),
                mode,
                args.baseline_heuristic,
                args.epoch,
                args.restart,
                args.timeout
            )
            
            results.append(result)
            print(f"{result['status']} in {result['time']:.2f}s (conflicts={result['conflicts']})")

    # Write results to CSV
    fieldnames = ['instance', 'mode', 'heuristic', 'status', 'time', 'conflicts', 'decisions', 'propagations', 'restarts']
    with open(args.output, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)

    print(f"\nResults written to {args.output}")
    
    # Quick summary
    print("\n=== Summary ===")
    for mode in args.modes:
        mode_results = [r for r in results if r['mode'] == mode]
        solved = sum(1 for r in mode_results if r['status'] in ['SAT', 'UNSAT'])
        total = len(mode_results)
        avg_time = sum(r['time'] for r in mode_results if r['status'] in ['SAT', 'UNSAT']) / max(1, solved)
        print(f"{mode}: {solved}/{total} solved, avg time: {avg_time:.2f}s")


if __name__ == '__main__':
    main()
