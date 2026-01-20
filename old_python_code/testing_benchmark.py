#!/usr/bin/env python3
"""
Simple testing benchmark - runs RL vs Baseline on all test CNFs with 1 min timeout.
Prints results to terminal and logs to timestamped file.
"""
import sys
import time
import signal
import os
from pathlib import Path
from datetime import datetime
from contextlib import contextmanager
import io

# Add project directories to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / 'rl-cdcl'))
sys.path.insert(0, str(project_root / 'baseline-cdcl'))
sys.path.insert(0, str(project_root / 'core_files'))
sys.path.insert(0, str(project_root / 'heuristics'))
sys.path.insert(0, str(project_root / 'bandit'))
sys.path.insert(0, str(project_root / 'utils'))

from run_solver import parse_dimacs_file
from cdcl_rl import CDCLSolverRL
from cdcl_baseline import CDCLSolverBaseline


class TimeoutException(Exception):
    pass


@contextmanager
def suppress_output():
    """Context manager to suppress stdout and stderr"""
    save_stdout = sys.stdout
    save_stderr = sys.stderr
    sys.stdout = io.StringIO()
    sys.stderr = io.StringIO()
    try:
        yield
    finally:
        sys.stdout = save_stdout
        sys.stderr = save_stderr


def timeout_handler(signum, frame):
    raise TimeoutException()


def run_solver(cnf_path, mode, timeout_sec=60):
    """Run a solver with timeout. Returns (status, time, conflicts)"""
    try:
        num_vars, clauses = parse_dimacs_file(cnf_path)
        
        if mode == 'rl':
            solver = CDCLSolverRL(num_vars, clauses)
        else:
            solver = CDCLSolverBaseline(num_vars, clauses, heuristic='vsids')
        
        # Set timeout
        signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(timeout_sec)
        
        t0 = time.time()
        with suppress_output():
            sat = solver.solve()
        elapsed = time.time() - t0
        
        signal.alarm(0)  # Cancel alarm
        
        status = 'SAT' if sat else 'UNSAT'
        return status, elapsed, solver.conflicts
        
    except TimeoutException:
        signal.alarm(0)
        return 'TIMEOUT', timeout_sec, 0
    except Exception as e:
        signal.alarm(0)
        return f'ERROR', 0, 0
    finally:
        signal.alarm(0)


def main():
    timeout = 60  # 1 minute
    test_dir = Path(__file__).parent / 'test_cnfs'
    log_dir = Path(__file__).parent / 'bechmark_results_logs'
    
    # Create log directory if it doesn't exist
    log_dir.mkdir(exist_ok=True)
    
    # Get all CNF files
    cnf_files = sorted(test_dir.glob('*.cnf'))
    
    if not cnf_files:
        print("No CNF files found!")
        return
    
    # Create timestamped log file
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    log_file = log_dir / f'test_results_{timestamp}.log'
    
    print(f"\n{'='*70}")
    print(f"Testing {len(cnf_files)} instances with {timeout}s timeout")
    print(f"{'='*70}\n")
    
    rl_wins = 0
    bl_wins = 0
    results = []
    
    for i, cnf_path in enumerate(cnf_files, 1):
        print(f"[{i}/{len(cnf_files)}] {cnf_path.name:<20} ", end='', flush=True)
        
        # Run RL
        rl_status, rl_time, rl_conf = run_solver(cnf_path, 'rl', timeout)
        
        # Run Baseline
        bl_status, bl_time, bl_conf = run_solver(cnf_path, 'baseline', timeout)
        
        # Determine winner
        if rl_status in ['SAT', 'UNSAT'] and bl_status in ['SAT', 'UNSAT']:
            if rl_time < bl_time:
                winner = 'RL'
                rl_wins += 1
            else:
                winner = 'BL'
                bl_wins += 1
        elif rl_status in ['SAT', 'UNSAT']:
            winner = 'RL (only solved)'
            rl_wins += 1
        elif bl_status in ['SAT', 'UNSAT']:
            winner = 'BL (only solved)'
            bl_wins += 1
        else:
            winner = 'NONE (both failed)'
        
        # Print result
        print(f"RL: {rl_status:8} ({rl_time:6.2f}s) | BL: {bl_status:8} ({bl_time:6.2f}s) | → {winner}")
        
        results.append({
            'instance': cnf_path.name,
            'rl_status': rl_status,
            'rl_time': rl_time,
            'bl_status': bl_status,
            'bl_time': bl_time,
            'winner': winner
        })
    
    # Print summary
    print(f"\n{'='*70}")
    print(f"SUMMARY")
    print(f"{'='*70}")
    print(f"RL Wins:       {rl_wins}/{len(cnf_files)}")
    print(f"Baseline Wins: {bl_wins}/{len(cnf_files)}")
    print(f"{'='*70}\n")
    
    # Write log file
    with open(log_file, 'w') as f:
        f.write(f"Test Results - {timestamp}\n")
        f.write(f"Timeout: {timeout}s\n")
        f.write(f"Instances tested: {len(cnf_files)}\n\n")
        f.write(f"RL Wins: {rl_wins}/{len(cnf_files)}\n")
        f.write(f"Baseline Wins: {bl_wins}/{len(cnf_files)}\n\n")
        f.write(f"Winner: {'RL' if rl_wins > bl_wins else 'BASELINE' if bl_wins > rl_wins else 'TIE'}\n\n")
        f.write("Detailed Results:\n")
        f.write("-" * 70 + "\n")
        for r in results:
            f.write(f"{r['instance']:<20} | RL: {r['rl_status']:8} ({r['rl_time']:6.2f}s) | BL: {r['bl_status']:8} ({r['bl_time']:6.2f}s)\n")
    
    print(f"Log saved to: {log_file}")


if __name__ == '__main__':
    main()
